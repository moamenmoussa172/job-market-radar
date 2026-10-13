"""Extractors for each job source.

Every extractor returns a list of *untouched* source records (dicts) for
data-related jobs, plus a stable `source_job_id` for each one.
Parsing (skills, seniority, remote scope, salary) is NOT done here; it
belongs to the silver layer so we can re-run it over history.
"""
from __future__ import annotations

import csv
import logging
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


def _get_json(url: str, params: dict | None = None) -> dict | list:
    resp = requests.get(url, params=params, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
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


def load_board_tokens(ats: str, path: Path = BOARDS_FILE) -> list[str]:
    tokens = set()
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(line for line in fh if not line.lstrip().startswith("#")):
            if (row.get("ats") or "").strip().lower() == ats and (row.get("token") or "").strip():
                tokens.add(row["token"].strip().lower())
    return sorted(tokens)


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


ATS_FETCHERS: dict[str, Callable[[str], list[dict]]] = {
    "greenhouse": _fetch_greenhouse,
    "lever": _fetch_lever,
    "ashby": _fetch_ashby,
}


def extract_company_boards(ats: str, tokens: list[str] | None = None,
                           pause_seconds: float = 0.5) -> ExtractResult:
    tokens = tokens if tokens is not None else load_board_tokens(ats)
    fetch = ATS_FETCHERS[ats]
    keep: list[dict] = []
    warnings: list[str] = []
    ok_boards = 0
    for token in tokens:
        try:
            jobs = fetch(token)
        except requests.HTTPError as exc:
            warnings.append(f"{ats} board '{token}' failed: {exc}")
            continue
        ok_boards += 1
        keep.extend({**job, "board_token": token} for job in jobs)
        time.sleep(pause_seconds)
    if tokens and ok_boards == 0:
        raise RuntimeError(f"All {ats} boards failed - check network or board tokens")
    log.info("%s: %s/%s boards ok, %s data-related jobs", ats, ok_boards, len(tokens), len(keep))
    return ExtractResult(ats, keep, warnings)


def extract_greenhouse(tokens: list[str] | None = None, pause_seconds: float = 0.5) -> ExtractResult:
    return extract_company_boards("greenhouse", tokens, pause_seconds)


def extract_lever(tokens: list[str] | None = None, pause_seconds: float = 0.5) -> ExtractResult:
    return extract_company_boards("lever", tokens, pause_seconds)


def extract_ashby(tokens: list[str] | None = None, pause_seconds: float = 0.5) -> ExtractResult:
    return extract_company_boards("ashby", tokens, pause_seconds)


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


def extract_jobicy(industries: list[str] | None = None, pause_seconds: float = 2.0) -> ExtractResult:
    industries = industries if industries is not None else JOBICY_INDUSTRIES
    keep: dict[str, dict] = {}
    seen = 0
    for industry in industries:
        payload = _get_json(JOBICY_URL, params={"count": 200, "industry": industry})
        jobs = payload.get("jobs") or []
        seen += len(jobs)
        for j in jobs:
            keep[str(j["id"])] = j  # industry feed is already data-focused; keep all
        time.sleep(pause_seconds)
    log.info("jobicy: %s jobs from %s industry feed(s)", seen, len(industries))
    return ExtractResult("jobicy", list(keep.values()))


def jobicy_id(record: dict) -> str:
    return str(record["id"])


# --------------------------------------------------------------------------- #
# Himalayas - remote jobs with locationRestrictions + timezoneRestriction.
# Search API: 20 jobs/page, rate limited (HTTP 429). Terms: link back to the
# Himalayas job URL and credit Himalayas; no re-posting to other job boards.
# --------------------------------------------------------------------------- #
HIMALAYAS_SEARCH_URL = "https://himalayas.app/jobs/api/search"
HIMALAYAS_QUERIES = ["data engineer", "data analyst", "analytics engineer", "business intelligence"]


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
@dataclass(frozen=True)
class SourceSpec:
    extract: Callable[[], ExtractResult]
    job_id: Callable[[dict], str]
    required: bool = True  # if True, the run fails when this source loads 0 jobs


SOURCES: dict[str, SourceSpec] = {
    "remotive": SourceSpec(extract_remotive, remotive_id, required=False),  # small sample feed
    "jobicy": SourceSpec(extract_jobicy, jobicy_id),
    "himalayas": SourceSpec(extract_himalayas, himalayas_id),
    "arbeitnow": SourceSpec(extract_arbeitnow, arbeitnow_id),
    "greenhouse": SourceSpec(extract_greenhouse, greenhouse_id),
    "lever": SourceSpec(extract_lever, lever_id),
    "ashby": SourceSpec(extract_ashby, ashby_id),
}
