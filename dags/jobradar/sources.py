"""Extractors for each job source.

Every extractor returns a list of *untouched* source records (dicts) for
data-related jobs, plus a stable `source_job_id` for each one.
Parsing (skills, seniority, remote scope, salary) is NOT done here; it
belongs to the silver layer so we can re-run it over history.
"""
from __future__ import annotations

import csv
import datetime as dt
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import requests

from jobradar.filters import is_data_role

log = logging.getLogger(__name__)

USER_AGENT = "job-market-radar/0.1 (personal data engineering project)"
TIMEOUT = 60


@dataclass
class ExtractResult:
    source: str
    records: list[dict]
    warnings: list[str] = field(default_factory=list)
    # company-board sources only: token -> data jobs found (None = board request failed)
    board_status: dict[str, int | None] = field(default_factory=dict)


def _get_json(url: str, params: dict | None = None, headers: dict | None = None) -> dict | list:
    resp = requests.get(url, params=params, timeout=TIMEOUT,
                        headers={"User-Agent": USER_AGENT, **(headers or {})})
    resp.raise_for_status()
    return resp.json()


def _post_json(url: str, body: dict) -> dict | list:
    resp = requests.post(url, json=body, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return resp.json()


# --------------------------------------------------------------------------- #
# Remotive - remote jobs. Terms: max ~4 calls/day, link back to Remotive,
# credit Remotive as the source, no re-posting to other job boards.
# --------------------------------------------------------------------------- #
REMOTIVE_URL = "https://remotive.com/api/remote-jobs"


def extract_remotive() -> ExtractResult:
    payload = _get_json(REMOTIVE_URL)  # one call per run returns all jobs
    jobs = payload.get("jobs", [])
    keep = [
        j for j in jobs
        if is_data_role(j.get("title")) or "data" in (j.get("category") or "").lower()
    ]
    log.info("remotive: %s jobs total, %s data-related", len(jobs), len(keep))
    warnings = []
    if len(jobs) < 100:
        warnings.append(f"remotive public API returned only {len(jobs)} jobs (sample feed)")
    return ExtractResult("remotive", keep, warnings)


def remotive_id(record: dict) -> str:
    return str(record["id"])


# --------------------------------------------------------------------------- #
# Arbeitnow - Europe (DE + more) with remote and visa_sponsorship flags.
# Newest first, paginated; a daily pull of the first pages covers new jobs.
# --------------------------------------------------------------------------- #
ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"


def extract_arbeitnow(max_pages: int = 10, pause_seconds: float = 1.0) -> ExtractResult:
    keep: list[dict] = []
    seen = 0
    for page in range(1, max_pages + 1):
        payload = _get_json(ARBEITNOW_URL, params={"page": page})
        data = payload.get("data", [])
        seen += len(data)
        keep.extend(j for j in data if is_data_role(j.get("title")))
        if not data or not (payload.get("links") or {}).get("next"):
            break
        time.sleep(pause_seconds)
    log.info("arbeitnow: %s jobs scanned, %s data-related", seen, len(keep))
    return ExtractResult("arbeitnow", keep)


def arbeitnow_id(record: dict) -> str:
    return str(record["slug"])


# --------------------------------------------------------------------------- #
# Company career boards (ATS public APIs): Greenhouse, Lever, Ashby.
# One call per company. The company list lives in company_boards.csv
# (columns: ats, token) - edit it freely. Boards that fail are reported as
# warnings in raw.ingestion_log so the list can be pruned.
# --------------------------------------------------------------------------- #
BOARDS_FILE = Path(__file__).with_name("company_boards.csv")
GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
LEVER_URLS = ["https://api.lever.co/v0/postings/{token}", "https://api.eu.lever.co/v0/postings/{token}"]
ASHBY_URL = "https://api.ashbyhq.com/posting-api/job-board/{token}"
SMARTRECRUITERS_URL = "https://api.smartrecruiters.com/v1/companies/{token}/postings"
WORKABLE_URL = "https://www.workable.com/api/accounts/{token}"

BOARD_ATS = ("greenhouse", "lever", "ashby", "smartrecruiters", "workable")
# SmartRecruiters company identifiers are case-sensitive (e.g. "BoschGroup").
CASE_SENSITIVE_ATS = ("smartrecruiters",)


def normalize_board_token(ats: str, token: str) -> str:
    token = token.strip()
    return token if ats in CASE_SENSITIVE_ATS else token.lower()


def load_board_rows(path: Path = BOARDS_FILE) -> list[tuple[str, str]]:
    """All (ats, token) seed rows from company_boards.csv."""
    rows = set()
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(line for line in fh if not line.lstrip().startswith("#")):
            ats = (row.get("ats") or "").strip().lower()
            token = normalize_board_token(ats, row.get("token") or "")
            if ats in BOARD_ATS and token:
                rows.add((ats, token))
    return sorted(rows)


def load_board_tokens(ats: str, path: Path = BOARDS_FILE) -> list[str]:
    return [t for a, t in load_board_rows(path) if a == ats]


def _fetch_greenhouse(token: str) -> list[dict]:
    payload = _get_json(GREENHOUSE_URL.format(token=token), params={"content": "true"})
    return [j for j in payload.get("jobs", []) if is_data_role(j.get("title"))]


def _fetch_lever(token: str) -> list[dict]:
    # Lever has a global and an EU instance; a company exists on only one.
    last_exc: Exception | None = None
    for url in LEVER_URLS:
        try:
            postings = _get_json(url.format(token=token), params={"mode": "json"})
        except requests.HTTPError as exc:
            last_exc = exc
            continue
        if isinstance(postings, list):
            return [j for j in postings if is_data_role(j.get("text"))]
    raise last_exc or requests.HTTPError(f"lever board '{token}' not found")


def _fetch_ashby(token: str) -> list[dict]:
    payload = _get_json(ASHBY_URL.format(token=token), params={"includeCompensation": "true"})
    return [
        j for j in payload.get("jobs", [])
        if j.get("isListed", True) and is_data_role(j.get("title"))
    ]


def _fetch_smartrecruiters(token: str, max_pages: int = 10) -> list[dict]:
    """List postings (titles only), then fetch full details for data roles only."""
    url = SMARTRECRUITERS_URL.format(token=token)
    data_items: list[dict] = []
    for page in range(max_pages):
        payload = _get_json(url, params={"limit": 100, "offset": page * 100})
        content = payload.get("content") or []
        data_items.extend(p for p in content if is_data_role(p.get("name")))
        if len(content) < 100 or (page + 1) * 100 >= (payload.get("totalFound") or 0):
            break
    detailed = []
    for item in data_items:
        try:
            detailed.append(_get_json(f"{url}/{item['id']}"))
        except requests.HTTPError:
            detailed.append(item)  # keep the summary if details fail
    return detailed


def _fetch_workable(token: str) -> list[dict]:
    payload = _get_json(WORKABLE_URL.format(token=token), params={"details": "true"})
    jobs = payload.get("jobs") if isinstance(payload, dict) else None
    if jobs is None:
        raise ValueError(f"workable account '{token}' returned no jobs list")
    return [{**j, "account_name": payload.get("name")} for j in jobs if is_data_role(j.get("title"))]


ATS_FETCHERS: dict[str, Callable[[str], list[dict]]] = {
    "greenhouse": _fetch_greenhouse,
    "lever": _fetch_lever,
    "ashby": _fetch_ashby,
    "smartrecruiters": _fetch_smartrecruiters,
    "workable": _fetch_workable,
}


def extract_company_boards(ats: str, tokens: list[str] | None = None,
                           pause_seconds: float = 0.5) -> ExtractResult:
    tokens = tokens if tokens is not None else load_board_tokens(ats)
    fetch = ATS_FETCHERS[ats]
    keep: list[dict] = []
    warnings: list[str] = []
    status: dict[str, int | None] = {}
    for token in tokens:
        try:
            jobs = fetch(token)
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout, ValueError) as exc:
            warnings.append(f"{ats} board '{token}' failed: {exc}")
            status[token] = None
            continue
        status[token] = len(jobs)
        keep.extend({**job, "board_token": token} for job in jobs)
        time.sleep(pause_seconds)
    ok_boards = sum(1 for v in status.values() if v is not None)
    if tokens and ok_boards == 0:
        raise RuntimeError(f"All {ats} boards failed - check network or board tokens")
    log.info("%s: %s/%s boards ok, %s data-related jobs", ats, ok_boards, len(tokens), len(keep))
    return ExtractResult(ats, keep, warnings, status)


def extract_greenhouse(tokens: list[str] | None = None, pause_seconds: float = 0.5) -> ExtractResult:
    return extract_company_boards("greenhouse", tokens, pause_seconds)


def extract_lever(tokens: list[str] | None = None, pause_seconds: float = 0.5) -> ExtractResult:
    return extract_company_boards("lever", tokens, pause_seconds)


def extract_ashby(tokens: list[str] | None = None, pause_seconds: float = 0.5) -> ExtractResult:
    return extract_company_boards("ashby", tokens, pause_seconds)


def extract_smartrecruiters(tokens: list[str] | None = None, pause_seconds: float = 0.5) -> ExtractResult:
    return extract_company_boards("smartrecruiters", tokens, pause_seconds)


def extract_workable(tokens: list[str] | None = None, pause_seconds: float = 0.5) -> ExtractResult:
    return extract_company_boards("workable", tokens, pause_seconds)


def smartrecruiters_id(record: dict) -> str:
    return f"{record['board_token']}:{record['id']}"


def workable_id(record: dict) -> str:
    return f"{record['board_token']}:{record.get('shortcode') or record.get('code') or record.get('url')}"


def greenhouse_id(record: dict) -> str:
    return f"{record['board_token']}:{record['id']}"


def lever_id(record: dict) -> str:
    return f"{record['board_token']}:{record['id']}"


def ashby_id(record: dict) -> str:
    # Ashby's public API has no stable id field; the job URL is unique per job.
    return f"{record['board_token']}:{record.get('id') or record.get('jobUrl')}"


# --------------------------------------------------------------------------- #
# Jobicy - remote jobs with jobGeo (eligibility), jobLevel and salary fields.
# Terms: poll at most hourly (we do daily), keep the Jobicy url + attribution.
# --------------------------------------------------------------------------- #
JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"
JOBICY_INDUSTRIES = ["data-science"]
# Keyword searches catch data roles listed under other industries (e.g. engineering).
JOBICY_TAGS = ["data engineer", "data analyst", "analytics", "business intelligence", "machine learning"]


def extract_jobicy(industries: list[str] | None = None, pause_seconds: float = 2.0,
                   tags: list[str] | None = None) -> ExtractResult:
    industries = industries if industries is not None else JOBICY_INDUSTRIES
    tags = tags if tags is not None else JOBICY_TAGS
    keep: dict[str, dict] = {}
    warnings: list[str] = []
    seen = 0
    for industry in industries:
        payload = _get_json(JOBICY_URL, params={"count": 200, "industry": industry})
        jobs = payload.get("jobs") or []
        seen += len(jobs)
        for j in jobs:
            keep[str(j["id"])] = j  # industry feed is already data-focused; keep all
        time.sleep(pause_seconds)
    for tag in tags:
        try:
            payload = _get_json(JOBICY_URL, params={"count": 200, "tag": tag})
        except requests.HTTPError as exc:
            warnings.append(f"jobicy tag '{tag}' failed: {exc}")
            continue
        jobs = payload.get("jobs") or []
        seen += len(jobs)
        for j in jobs:
            if is_data_role(j.get("jobTitle")):  # keyword hits can be any role
                keep.setdefault(str(j["id"]), j)
        time.sleep(pause_seconds)
    log.info("jobicy: %s results scanned, %s distinct data jobs", seen, len(keep))
    return ExtractResult("jobicy", list(keep.values()), warnings)


def jobicy_id(record: dict) -> str:
    return str(record["id"])


# --------------------------------------------------------------------------- #
# Himalayas - remote jobs with locationRestrictions + timezoneRestriction.
# Search API: 20 jobs/page, rate limited (HTTP 429). Terms: link back to the
# Himalayas job URL and credit Himalayas; no re-posting to other job boards.
# --------------------------------------------------------------------------- #
HIMALAYAS_SEARCH_URL = "https://himalayas.app/jobs/api/search"
HIMALAYAS_QUERIES = [
    "data engineer", "data analyst", "analytics engineer", "business intelligence",
    "data scientist", "machine learning engineer", "bi developer", "data platform",
    "analytics", "etl",
]


def _himalayas_page(query: str, page: int) -> list[dict]:
    for attempt in range(2):
        try:
            payload = _get_json(HIMALAYAS_SEARCH_URL, params={"q": query, "page": page})
            return payload.get("jobs") or payload.get("data") or []
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 429 and attempt == 0:
                time.sleep(30)
                continue
            raise
    return []


def himalayas_id(record: dict) -> str:
    return str(record.get("guid") or record.get("applicationLink"))


def extract_himalayas(queries: list[str] | None = None, max_pages: int = 5,
                      pause_seconds: float = 2.0) -> ExtractResult:
    queries = queries if queries is not None else HIMALAYAS_QUERIES
    keep: dict[str, dict] = {}
    warnings: list[str] = []
    for query in queries:
        for page in range(1, max_pages + 1):
            try:
                jobs = _himalayas_page(query, page)
            except requests.HTTPError as exc:
                warnings.append(f"himalayas q='{query}' page={page} failed: {exc}")
                break
            for j in jobs:
                if is_data_role(j.get("title")):
                    keep[himalayas_id(j)] = {**j, "search_query": query}
            if len(jobs) < 20:
                break
            time.sleep(pause_seconds)
    log.info("himalayas: %s data-related jobs from %s queries", len(keep), len(queries))
    return ExtractResult("himalayas", list(keep.values()), warnings)


# --------------------------------------------------------------------------- #
# Licensed aggregators with API keys (keys live in .env, never in code).
# Both have small quotas, so each day runs only the next slice of a fixed
# list of (role, country) searches; every pair is covered every few days.
# Jobs from these sources stay "active" for ACTIVE_WINDOW_DAYS (see dbt).
# --------------------------------------------------------------------------- #
SEARCH_COUNTRIES = [  # (ISO code, name used in free-text queries)
    ("eg", "Egypt"), ("ae", "United Arab Emirates"), ("sa", "Saudi Arabia"), ("qa", "Qatar"),
    ("de", "Germany"), ("es", "Spain"), ("gb", "United Kingdom"),
]
SEARCH_ROLES = ["data engineer", "data analyst", "business intelligence", "analytics engineer"]


def daily_slice(pairs: list, per_day: int, day: dt.date | None = None) -> list:
    """The `per_day` items for `day`, walking the list so all items rotate through."""
    if not pairs or per_day <= 0:
        return []
    day = day or dt.date.today()
    start = (day.toordinal() * per_day) % len(pairs)
    return [pairs[(start + i) % len(pairs)] for i in range(min(per_day, len(pairs)))]


# JSearch (OpenWeb Ninja): Google for Jobs data - postings originally published on
# LinkedIn, Indeed, Glassdoor, Bayt, company sites, ... Free plan: 200 requests/month.
JSEARCH_URL = "https://api.openwebninja.com/jsearch/search-v2"
JSEARCH_PER_DAY = int(os.environ.get("JSEARCH_REQUESTS_PER_DAY", "6"))


def jsearch_pairs() -> list[tuple[str, str, str]]:
    return [(role, code, name) for role in SEARCH_ROLES for code, name in SEARCH_COUNTRIES]


def extract_jsearch(pairs: list | None = None, pause_seconds: float = 1.0) -> ExtractResult:
    key = os.environ.get("JSEARCH_API_KEY", "").strip()
    if not key:
        return ExtractResult("jsearch", [], ["JSEARCH_API_KEY not set - source skipped"])
    pairs = pairs if pairs is not None else daily_slice(jsearch_pairs(), JSEARCH_PER_DAY)
    keep: dict[str, dict] = {}
    warnings: list[str] = []
    for role, code, name in pairs:
        try:
            payload = _get_json(JSEARCH_URL, headers={"x-api-key": key},
                                params={"query": f"{role} jobs in {name}", "country": code})
        except requests.HTTPError as exc:
            warnings.append(f"jsearch '{role}' in {code} failed: {exc}")
            if exc.response is not None and exc.response.status_code in (401, 403, 429):
                break  # bad key or quota used up: don't burn more requests today
            continue
        data = payload.get("data") if isinstance(payload, dict) else payload
        if isinstance(data, dict):  # some versions nest the list
            data = data.get("jobs") or data.get("data") or []
        for job in data or []:
            if is_data_role(job.get("job_title")) and job.get("job_id"):
                keep[str(job["job_id"])] = {**job, "search_query": role, "search_country": code}
        time.sleep(pause_seconds)
    log.info("jsearch: %s searches, %s data-related jobs", len(pairs), len(keep))
    return ExtractResult("jsearch", list(keep.values()), warnings)


def jsearch_id(record: dict) -> str:
    return str(record["job_id"])


# Jooble: aggregator, 60+ countries. Descriptions are short snippets.
# Key quota is small (500 requests by default), so only a few searches per day.
JOOBLE_URL = "https://jooble.org/api/{key}"
JOOBLE_PER_DAY = int(os.environ.get("JOOBLE_REQUESTS_PER_DAY", "3"))


def jooble_pairs() -> list[tuple[str, str]]:
    roles = ["data engineer", "data analyst"]
    return [(role, name) for role in roles for _, name in SEARCH_COUNTRIES]


def extract_jooble(pairs: list | None = None, pause_seconds: float = 1.0) -> ExtractResult:
    key = os.environ.get("JOOBLE_API_KEY", "").strip()
    if not key:
        return ExtractResult("jooble", [], ["JOOBLE_API_KEY not set - source skipped"])
    pairs = pairs if pairs is not None else daily_slice(jooble_pairs(), JOOBLE_PER_DAY)
    keep: dict[str, dict] = {}
    warnings: list[str] = []
    for role, location in pairs:
        try:
            payload = _post_json(JOOBLE_URL.format(key=key),
                                 {"keywords": role, "location": location, "page": "1"})
        except requests.HTTPError as exc:
            warnings.append(f"jooble '{role}' in {location} failed: HTTP "
                            f"{exc.response.status_code if exc.response is not None else '?'}")
            if exc.response is not None and exc.response.status_code in (401, 403, 429):
                break
            continue
        for job in payload.get("jobs") or []:
            if is_data_role(job.get("title")):
                job_key = str(job.get("id") or job.get("link"))
                keep[job_key] = {**job, "search_query": role, "search_location": location}
        time.sleep(pause_seconds)
    log.info("jooble: %s searches, %s data-related jobs", len(pairs), len(keep))
    return ExtractResult("jooble", list(keep.values()), warnings)


def jooble_id(record: dict) -> str:
    return str(record.get("id") or record.get("link"))


# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SourceSpec:
    extract: Callable[..., ExtractResult]
    job_id: Callable[[dict], str]
    required: bool = True  # if True, the run fails when this source loads 0 jobs
    board_ats: str | None = None  # company-board source: board list comes from the registry


SOURCES: dict[str, SourceSpec] = {
    "remotive": SourceSpec(extract_remotive, remotive_id, required=False),  # small sample feed
    "jobicy": SourceSpec(extract_jobicy, jobicy_id),
    "himalayas": SourceSpec(extract_himalayas, himalayas_id),
    "arbeitnow": SourceSpec(extract_arbeitnow, arbeitnow_id),
    "greenhouse": SourceSpec(extract_greenhouse, greenhouse_id, board_ats="greenhouse"),
    "lever": SourceSpec(extract_lever, lever_id, board_ats="lever"),
    "ashby": SourceSpec(extract_ashby, ashby_id, board_ats="ashby"),
    "smartrecruiters": SourceSpec(extract_smartrecruiters, smartrecruiters_id, required=False,
                                  board_ats="smartrecruiters"),
    "workable": SourceSpec(extract_workable, workable_id, required=False, board_ats="workable"),
    # key-based aggregators: optional (missing key / quota reached only warns)
    "jsearch": SourceSpec(extract_jsearch, jsearch_id, required=False),
    "jooble": SourceSpec(extract_jooble, jooble_id, required=False),
}
