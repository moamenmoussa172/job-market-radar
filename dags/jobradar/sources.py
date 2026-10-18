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
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import requests

from jobradar.filters import is_tech_role

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


def _get_text(url: str, params: dict | None = None) -> str:
    resp = requests.get(url, params=params, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return resp.text


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
        if is_tech_role(j.get("title"))
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


def _arbeitnow_page(page: int, retries: int = 3) -> dict:
    """One page; on HTTP 429 (rate limit) wait as the server asks, then try again."""
    for attempt in range(retries + 1):
        try:
            return _get_json(ARBEITNOW_URL, params={"page": page})
        except requests.HTTPError as exc:
            resp = exc.response
            if resp is None or resp.status_code != 429 or attempt == retries:
                raise
            try:
                wait = float(resp.headers.get("Retry-After", ""))
            except ValueError:
                wait = 0
            time.sleep(min(max(wait, 15 * (attempt + 1)), 120))
    raise RuntimeError("unreachable")


def extract_arbeitnow(max_pages: int = 30, pause_seconds: float = 2.0) -> ExtractResult:
    keep: list[dict] = []
    warnings: list[str] = []
    seen = 0
    for page in range(1, max_pages + 1):
        try:
            payload = _arbeitnow_page(page)
        except requests.RequestException as exc:
            if page == 1:
                raise                      # nothing at all: a real failure
            warnings.append(f"arbeitnow stopped at page {page} ({exc}); kept pages 1-{page - 1}")
            break
        data = payload.get("data", [])
        seen += len(data)
        keep.extend(j for j in data if is_tech_role(j.get("title")))
        if not data or not (payload.get("links") or {}).get("next"):
            break
        time.sleep(pause_seconds)
    log.info("arbeitnow: %s jobs scanned, %s data-related", seen, len(keep))
    return ExtractResult("arbeitnow", keep, warnings)


def arbeitnow_id(record: dict) -> str:
    return str(record["slug"])


# --------------------------------------------------------------------------- #
# Company career boards (ATS public APIs): Greenhouse, Lever, Ashby.
# One call per company. The company list lives in company_boards.csv
# (columns: ats, token) - edit it freely. Boards that fail are reported as
# warnings in raw.ingestion_log so the list can be pruned.
# --------------------------------------------------------------------------- #
BOARDS_FILE = Path(__file__).with_name("company_boards.csv")
GREENHOUSE_URLS = ["https://boards-api.greenhouse.io/v1/boards/{token}/jobs",       # US data centre
                   "https://boards-api.eu.greenhouse.io/v1/boards/{token}/jobs"]    # EU (e.g. Tamara, Ziina)
BREEZY_URL = "https://{token}.breezy.hr/json"                                      # public positions feed
TEAMTAILOR_URL = "https://{token}.teamtailor.com/jobs.rss"                          # public RSS (per_page <= 200)
LEVER_URLS = ["https://api.lever.co/v0/postings/{token}", "https://api.eu.lever.co/v0/postings/{token}"]
ASHBY_URL = "https://api.ashbyhq.com/posting-api/job-board/{token}"
SMARTRECRUITERS_URL = "https://api.smartrecruiters.com/v1/companies/{token}/postings"
WORKABLE_URL = "https://www.workable.com/api/accounts/{token}"
RECRUITEE_URL = "https://{token}.recruitee.com/api/offers/"           # public Careers Site API
PERSONIO_URLS = ["https://{token}.jobs.personio.de/xml",                # public XML job feed
                 "https://{token}.jobs.personio.com/xml"]

# Platforms whose board names can be guessed from a company name (used by probing)
PROBE_ATS = ("greenhouse", "lever", "ashby", "smartrecruiters", "workable", "recruitee", "personio",
             "breezy", "teamtailor")
# + enterprise platforms (big corporates, banks, telcos, oil & gas): their board ids can't be guessed,
# they come from company_boards.csv or from job links that point to them (harvest).
BOARD_ATS = PROBE_ATS + ("workday", "successfactors")
# SmartRecruiters company identifiers are case-sensitive (e.g. "BoschGroup"); so are Workday site names.
CASE_SENSITIVE_ATS = ("smartrecruiters", "workday", "lever")   # Lever: jobs.lever.co/Bosta, /Yassir

# Workday board id = "<tenant>.<wdN>/<site>", from https://<tenant>.<wdN>.myworkdayjobs.com/[en-US/]<site>
_WORKDAY_RE = re.compile(
    r"^(?:https?://)?([a-z0-9-]+)\.(wd[0-9]+)(?:\.myworkdayjobs\.com)?/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_-]+)",
    re.IGNORECASE)
_WORKDAY_NOT_SITES = {"wday", "job", "jobs", "details", "login", "en-us"}


def normalize_board_token(ats: str, token: str) -> str:
    token = token.strip()
    if ats == "workday":
        m = _WORKDAY_RE.match(token)
        if not m or m.group(3).lower() in _WORKDAY_NOT_SITES:
            return ""
        return f"{m.group(1).lower()}.{m.group(2).lower()}/{m.group(3)}"
    if ats == "successfactors":  # career site host, e.g. jobs.sap.com
        return re.sub(r"^https?://", "", token.lower()).split("/")[0]
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


def load_board_companies(path: Path = BOARDS_FILE) -> dict[tuple[str, str], str]:
    """(ats, token) -> company display name, for rows that give one."""
    return {k: v["company"] for k, v in load_board_details(path).items() if v.get("company")}


def load_board_details(path: Path = BOARDS_FILE) -> dict[tuple[str, str], dict]:
    """(ats, token) -> {"company", "country"} from the optional CSV columns (used for display names, and
    as the location of jobs whose feed only gives a city)."""
    out = {}
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(line for line in fh if not line.lstrip().startswith("#")):
            ats = (row.get("ats") or "").strip().lower()
            token = normalize_board_token(ats, row.get("token") or "")
            details = {k: (row.get(k) or "").strip() for k in ("company", "country")}
            if ats in BOARD_ATS and token and any(details.values()):
                out[(ats, token)] = details
    return out


def load_board_tokens(ats: str, path: Path = BOARDS_FILE) -> list[str]:
    return [t for a, t in load_board_rows(path) if a == ats]


def _fetch_greenhouse(token: str) -> list[dict]:
    # A Greenhouse board lives in the US or the EU data centre; try both (like Lever).
    last_exc: Exception | None = None
    for url in GREENHOUSE_URLS:
        try:
            payload = _get_json(url.format(token=token), params={"content": "true"})
        except requests.HTTPError as exc:
            last_exc = exc
            continue
        return [j for j in payload.get("jobs", []) if is_tech_role(j.get("title"))]
    raise last_exc or requests.HTTPError(f"greenhouse board '{token}' not found")


def _fetch_breezy(token: str) -> list[dict]:
    """Breezy HR careers site feed: a JSON list of open positions (no descriptions)."""
    positions = _get_json(BREEZY_URL.format(token=token))
    if not isinstance(positions, list):
        raise ValueError(f"breezy '{token}' did not return a positions list")
    return [p for p in positions if isinstance(p, dict) and is_tech_role(p.get("name"))]


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_teamtailor_rss(xml_text: str) -> list[dict]:
    """Teamtailor RSS -> dicts. Besides title/link/description/pubDate/guid, items carry namespaced
    fields (locations, department, remote status) whose exact tags vary: they are kept by local name."""
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if _local(root.tag) != "rss" or channel is None:
        raise ValueError(f"not an RSS feed (root <{root.tag}>)")
    jobs = []
    for item in channel.findall("item"):
        job: dict = {"locations": []}
        for child in item:
            name, text = _local(child.tag), (child.text or "").strip()
            if name in ("locations", "location"):
                # <tt:locations><tt:location><tt:city>Riyadh</tt:city><tt:country>Saudi Arabia</tt:country>...
                for loc in (list(child) if name == "locations" and len(child) else [child]):
                    place = [(el.text or "").strip() for el in loc.iter() if _local(el.tag) in ("city", "country")]
                    job["locations"].append(", ".join(dict.fromkeys(p for p in place if p)) or (loc.text or "").strip())
            elif text and name not in job:
                job[name] = text
        job["locations"] = [loc for loc in job["locations"] if loc]
        jobs.append(job)
    return jobs


def _fetch_teamtailor(token: str) -> list[dict]:
    text = _get_text(TEAMTAILOR_URL.format(token=token), params={"per_page": 200})
    try:
        jobs = parse_teamtailor_rss(text)
    except ET.ParseError as exc:
        raise ValueError(f"teamtailor '{token}' did not return an RSS feed") from exc
    return [j for j in jobs if is_tech_role(j.get("title"))]


def _fetch_lever(token: str) -> list[dict]:
    # Lever has a global and an EU instance; a company exists on only one. Some site names are
    # capitalised (jobs.lever.co/Bosta): the name is tried as written, in lower case, and Capitalised.
    last_exc: Exception | None = None
    for name in dict.fromkeys([token, token.lower(), token[:1].upper() + token[1:].lower()]):
        for url in LEVER_URLS:
            try:
                postings = _get_json(url.format(token=name), params={"mode": "json"})
            except requests.HTTPError as exc:
                last_exc = exc
                continue
            if isinstance(postings, list):
                return [j for j in postings if is_tech_role(j.get("text"))]
    raise last_exc or requests.HTTPError(f"lever board '{token}' not found")


def _fetch_ashby(token: str) -> list[dict]:
    payload = _get_json(ASHBY_URL.format(token=token), params={"includeCompensation": "true"})
    return [
        j for j in payload.get("jobs", [])
        if j.get("isListed", True) and is_tech_role(j.get("title"))
    ]


SMARTRECRUITERS_MAX_DETAILS = int(os.environ.get("SMARTRECRUITERS_MAX_DETAILS", "150"))


def _fetch_smartrecruiters(token: str, max_pages: int = 20) -> list[dict]:
    """List postings (titles only), then fetch full details for data roles only."""
    url = SMARTRECRUITERS_URL.format(token=token)
    data_items: list[dict] = []
    for page in range(max_pages):
        payload = _get_json(url, params={"limit": 100, "offset": page * 100})
        content = payload.get("content") or []
        data_items.extend(p for p in content if is_tech_role(p.get("name")))
        if len(content) < 100 or (page + 1) * 100 >= (payload.get("totalFound") or 0):
            break
    # One details call per matching posting; big employers list hundreds of tech roles,
    # so details are fetched for the newest SMARTRECRUITERS_MAX_DETAILS only (the rest
    # are kept as summaries: title, location, dates - but no description/skills).
    data_items.sort(key=lambda p: p.get("releasedDate") or "", reverse=True)
    summaries = data_items[SMARTRECRUITERS_MAX_DETAILS:]
    data_items = data_items[:SMARTRECRUITERS_MAX_DETAILS]
    detailed = list(summaries)
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
    return [{**j, "account_name": payload.get("name")} for j in jobs if is_tech_role(j.get("title"))]


def _fetch_recruitee(token: str) -> list[dict]:
    payload = _get_json(RECRUITEE_URL.format(token=token))
    offers = payload.get("offers") if isinstance(payload, dict) else None
    if offers is None:
        raise ValueError(f"recruitee '{token}' returned no offers list")
    return [o for o in offers if is_tech_role(o.get("title"))]


def parse_personio_xml(xml_text: str) -> list[dict]:
    """<workzag-jobs><position>...</position></workzag-jobs> -> list of dicts."""
    root = ET.fromstring(xml_text)
    if root.tag != "workzag-jobs":
        raise ValueError(f"not a Personio feed (root <{root.tag}>)")
    jobs = []
    for pos in root.findall("position"):
        job: dict = {}
        for child in pos:
            if child.tag == "additionalOffices":
                job["additionalOffices"] = [o.text for o in child.findall("office") if o.text]
            elif child.tag == "jobDescriptions":
                job["jobDescriptions"] = [
                    {"name": (d.findtext("name") or "").strip(), "value": (d.findtext("value") or "").strip()}
                    for d in child.findall("jobDescription")
                ]
            else:
                job[child.tag] = (child.text or "").strip()
        jobs.append(job)
    return jobs


def _fetch_personio(token: str) -> list[dict]:
    last_exc: Exception | None = None
    for url in PERSONIO_URLS:
        try:
            jobs = parse_personio_xml(_get_text(url.format(token=token)))
        except (requests.HTTPError, ET.ParseError) as exc:
            last_exc = exc
            continue
        return [{**j, "job_url": f"https://{token}.jobs.personio.de/job/{j.get('id')}"}
                for j in jobs if is_tech_role(j.get("name"))]
    if isinstance(last_exc, ET.ParseError):
        raise ValueError(f"personio '{token}' did not return a job feed")
    raise last_exc or requests.HTTPError(f"personio '{token}' not found")


# --------------------------------------------------------------------------- #
# Workday (myworkdayjobs.com) - used by most large corporates in the Gulf and by
# multinationals with offices in Egypt and the Gulf. Undocumented but public JSON
# API behind every careers site:
#   POST /wday/cxs/<tenant>/<site>/jobs  {"appliedFacets", "limit" (max 20!), "offset", "searchText"}
#   GET  /wday/cxs/<tenant>/<site><externalPath>  (Accept: application/json) -> jobPostingInfo
# Big employers list thousands of jobs worldwide, so only jobs in the countries we cover are
# requested (Workday's country filter), MENA first, and details are fetched for tech titles only.
# --------------------------------------------------------------------------- #
WORKDAY_PAGE = 20  # larger pages silently return nothing
WORKDAY_MAX_PAGES = int(os.environ.get("WORKDAY_MAX_PAGES", "15"))       # per country group
WORKDAY_MAX_DETAILS = int(os.environ.get("WORKDAY_MAX_DETAILS", "80"))   # per board
WORKDAY_HEADERS = {"Accept": "application/json", "Accept-Language": "en-US", "Content-Type": "application/json"}
MENA_COUNTRY_NAMES = ("Egypt", "United Arab Emirates", "Saudi Arabia", "Qatar", "Kuwait", "Bahrain", "Oman",
                      "Jordan", "Morocco", "Lebanon", "Tunisia")
EUROPE_COUNTRY_NAMES = ("Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia", "Czech Republic",
                        "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary", "Ireland",
                        "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta", "Netherlands", "Norway", "Poland",
                        "Portugal", "Romania", "Serbia", "Spain", "Sweden", "Switzerland", "United Kingdom")
# "mena" or "mena,europe" (default); "all" = no country filter (page cap still applies)
WORKDAY_REGIONS = [r.strip().lower() for r in os.environ.get("WORKDAY_REGIONS", "mena,europe").split(",") if r.strip()]


def workday_urls(token: str) -> tuple[str, str, str]:
    """token 'tenant.wd3/Site' -> (careers base, list API url, detail API prefix)."""
    host_part, site = token.split("/", 1)
    tenant = host_part.split(".")[0]
    base = f"https://{host_part}.myworkdayjobs.com"
    api = f"{base}/wday/cxs/{tenant}/{site}"
    return f"{base}/en-US/{site}", f"{api}/jobs", api


def _workday_post(url: str, body: dict) -> dict:
    resp = requests.post(url, json=body, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT, **WORKDAY_HEADERS})
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict) or "jobPostings" not in data:
        raise ValueError("not a Workday jobs API response")
    return data


def workday_country_facet(facets: list, names: tuple[str, ...]) -> tuple[str | None, list[str]]:
    """Find the country filter in Workday's facet tree -> (facet parameter, ids of the wanted countries).
    Facets nest (e.g. Locations > Country > values); the parameter name varies per site."""
    wanted = {n.lower() for n in names}
    best: tuple[str | None, list[str]] = (None, [])

    def walk(nodes: list) -> None:
        nonlocal best
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            values = node.get("values") or []
            leaves = [v for v in values if isinstance(v, dict) and v.get("id") and "values" not in v]
            ids = [v["id"] for v in leaves if (v.get("descriptor") or "").strip().lower() in wanted]
            param = node.get("facetParameter")
            if ids and param:
                is_country = "country" in param.lower() or "country" in (node.get("descriptor") or "").lower()
                if is_country or not best[0]:
                    if is_country or len(ids) > len(best[1]):
                        best = (param, ids)
            walk([v for v in values if isinstance(v, dict) and "values" in v])

    walk(facets)
    return best


_WORKDAY_CITIES = {
    "mena": ("cairo", "alexandria", "giza", "new cairo", "dubai", "abu dhabi", "sharjah", "riyadh", "jeddah",
             "dammam", "dhahran", "khobar", "doha", "kuwait", "manama", "muscat", "amman", "casablanca", "rabat",
             "beirut", "tunis", "uae", "ksa"),
    "europe": ("london", "manchester", "edinburgh", "berlin", "munich", "hamburg", "frankfurt", "stuttgart",
               "paris", "amsterdam", "eindhoven", "dublin", "cork", "madrid", "barcelona", "warsaw", "krakow",
               "gdansk", "wroclaw", "lisbon", "porto", "milan", "rome", "stockholm", "copenhagen", "prague", "brno",
               "vienna", "zurich", "geneva", "brussels", "budapest", "bucharest", "sofia", "athens", "helsinki",
               "oslo", "tallinn", "riga", "vilnius", "belgrade", "zagreb", "luxembourg", "valletta"),
}


def workday_has_country_facet(facets: list) -> bool:
    def walk(nodes: list) -> bool:
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            label = f"{node.get('facetParameter', '')} {node.get('descriptor', '')}".lower()
            if "country" in label and node.get("values"):
                return True
            if walk([v for v in node.get("values") or [] if isinstance(v, dict) and "values" in v]):
                return True
        return False
    return walk(facets)


def workday_location_matcher(regions: list[str]) -> re.Pattern:
    words: list[str] = []
    for region in regions:
        names = MENA_COUNTRY_NAMES if region == "mena" else EUROPE_COUNTRY_NAMES if region == "europe" else ()
        words += [n.lower() for n in names] + list(_WORKDAY_CITIES.get(region, ()))
    return re.compile(r"(?<![a-z])(" + "|".join(re.escape(w) for w in sorted(set(words), key=len, reverse=True))
                      + r")(?![a-z])", re.IGNORECASE)


def workday_posted_date(posted_on: str | None, today: dt.date | None = None) -> str | None:
    """'Posted Today' / 'Posted Yesterday' / 'Posted 3 Days Ago' / 'Posted 30+ Days Ago' -> ISO date."""
    today = today or dt.date.today()
    text = (posted_on or "").lower()
    if "today" in text:
        return today.isoformat()
    if "yesterday" in text:
        return (today - dt.timedelta(days=1)).isoformat()
    m = re.search(r"(\d+)\+?\s*days?", text)
    return (today - dt.timedelta(days=int(m.group(1)))).isoformat() if m else None


def _fetch_workday(token: str) -> list[dict]:
    careers, list_url, api = workday_urls(token)
    first = _workday_post(list_url, {"appliedFacets": {}, "limit": WORKDAY_PAGE, "offset": 0, "searchText": ""})
    groups: list[tuple[str, ...] | None] = []
    for region in WORKDAY_REGIONS:
        groups.append(None if region == "all" else
                      MENA_COUNTRY_NAMES if region == "mena" else EUROPE_COUNTRY_NAMES if region == "europe" else ())
    summaries: dict[str, dict] = {}
    has_country_filter = workday_has_country_facet(first.get("facets") or [])
    if not has_country_filter and None not in groups:
        # This site can't filter by country: read the newest jobs and keep those whose location
        # text names one of our countries or a big city there ("Gdansk, Poland", "Dubai - UAE").
        wanted = workday_location_matcher(WORKDAY_REGIONS)
        for page in range(WORKDAY_MAX_PAGES * 2):
            data = first if page == 0 else _workday_post(
                list_url, {"appliedFacets": {}, "limit": WORKDAY_PAGE, "offset": page * WORKDAY_PAGE, "searchText": ""})
            postings = data.get("jobPostings") or []
            for jp in postings:
                if (jp.get("externalPath") and is_tech_role(jp.get("title"))
                        and wanted.search(jp.get("locationsText") or "")):
                    summaries.setdefault(jp["externalPath"], jp)
            if len(postings) < WORKDAY_PAGE or (page + 1) * WORKDAY_PAGE >= (data.get("total") or 0):
                break
        groups = []  # done
    for names in groups:
        if names == ():
            continue
        facets: dict = {}
        if names is not None:
            param, ids = workday_country_facet(first.get("facets") or [], names)
            if not param:
                continue  # the site filters by country, and has no jobs in these countries
            facets = {param: ids}
        for page in range(WORKDAY_MAX_PAGES):
            data = first if (not facets and page == 0) else _workday_post(
                list_url, {"appliedFacets": facets, "limit": WORKDAY_PAGE, "offset": page * WORKDAY_PAGE,
                           "searchText": ""})
            postings = data.get("jobPostings") or []
            for jp in postings:
                if jp.get("externalPath") and is_tech_role(jp.get("title")):
                    summaries.setdefault(jp["externalPath"], jp)
            if len(postings) < WORKDAY_PAGE or (page + 1) * WORKDAY_PAGE >= (data.get("total") or 0):
                break
    jobs = []
    today = dt.date.today()
    for i, (path, jp) in enumerate(summaries.items()):
        job = {"title": jp.get("title"), "externalPath": path, "locationsText": jp.get("locationsText"),
               "postedOn": jp.get("postedOn"), "posted_date": workday_posted_date(jp.get("postedOn"), today),
               "bulletFields": jp.get("bulletFields"), "job_url": f"{careers}{path}"}
        if i < WORKDAY_MAX_DETAILS:
            try:
                info = (_get_json(api + path, headers=WORKDAY_HEADERS) or {}).get("jobPostingInfo") or {}
            except (requests.HTTPError, ValueError):
                info = {}
            if info:
                job.update({k: info.get(k) for k in ("jobDescription", "location", "additionalLocations",
                                                      "timeType", "startDate", "jobReqId", "remoteType")})
                job["country"] = (info.get("country") or {}).get("descriptor")
                job["company"] = (info.get("hiringOrganization") or {}).get("name") if isinstance(
                    info.get("hiringOrganization"), dict) else None
                if info.get("externalUrl"):
                    job["job_url"] = info["externalUrl"]
        jobs.append(job)
    return jobs


# --------------------------------------------------------------------------- #
# SAP SuccessFactors career sites (jobs.<company>.com, "Recruiting Marketing").
# They publish an RSS feed of open jobs: <host>/services/rss/job/?locale=en_US&keywords=
# Board id = the career site host. Sites that switched the feed off are marked dead.
# --------------------------------------------------------------------------- #
SUCCESSFACTORS_RSS = "https://{host}/services/rss/job/"
SUCCESSFACTORS_ROWS = int(os.environ.get("SUCCESSFACTORS_ROWS", "5000"))   # no paging; the default is only 20
SUCCESSFACTORS_MAX_SECONDS = int(os.environ.get("SUCCESSFACTORS_MAX_SECONDS", "240"))  # per board: big feeds are slow


def split_title_location(title: str) -> tuple[str, str | None]:
    """'Data Engineer (Riyadh, SA, 12345)' -> ('Data Engineer', 'Riyadh, SA, 12345').
    The location is the balanced (...) group that ends the title; either part may hold parentheses."""
    title = title.strip()
    if not title.endswith(")"):
        return title, None
    depth = 0
    for i in range(len(title) - 1, -1, -1):
        depth += {")": 1, "(": -1}.get(title[i], 0)
        if depth == 0:
            return (title[:i].strip() or title), title[i + 1:-1].strip()
    return title, None


def _sf_item(item: ET.Element) -> dict:
    title, location = split_title_location(item.findtext("title") or "")
    return {
        "title": title,
        "location": location,
        "link": (item.findtext("link") or "").strip(),
        "guid": (item.findtext("guid") or item.findtext("link") or "").strip(),
        "description": item.findtext("description") or "",
        "pubDate": (item.findtext("pubDate") or "").strip(),
    }


def parse_successfactors_stream(chunks, deadline: float | None = None) -> list[dict]:
    """Parse the RSS feed while it downloads. Big employers' feeds are many megabytes: if the
    connection drops or the time is up, the jobs read so far are kept instead of losing them all."""
    parser = ET.XMLPullParser(events=("start", "end"))
    jobs: list[dict] = []
    head, seen_root = b"", False
    try:
        for chunk in chunks:
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            if len(head) < 64:
                head += chunk[:64]
                if head.lstrip().startswith(b"<xml>"):  # malformed query: <xml>Error: ...</xml>
                    raise ValueError(f"successfactors feed error: {head.decode('utf-8', 'replace').strip()[:120]}")
            parser.feed(chunk)
            for event, el in parser.read_events():
                if event == "start" and not seen_root:
                    seen_root = True
                    if el.tag != "rss":
                        raise ValueError(f"not an RSS feed (root <{el.tag}>)")
                if event == "end" and el.tag == "item":
                    jobs.append(_sf_item(el))
                    el.clear()
            if deadline and time.monotonic() > deadline:
                log.warning("successfactors feed: time limit reached, keeping %s jobs read so far", len(jobs))
                break
    except (requests.RequestException, ET.ParseError) as exc:
        if not jobs:
            raise ValueError(f"successfactors feed could not be read: {exc}") from exc
        log.warning("successfactors feed cut off (%s), keeping %s jobs read so far", exc, len(jobs))
    return jobs


def parse_successfactors_rss(xml_text: str) -> list[dict]:
    if xml_text.lstrip().startswith("<xml>"):
        raise ValueError(f"successfactors feed error: {xml_text.strip()[:120]}")
    root = ET.fromstring(xml_text)
    if root.tag != "rss" or root.find("channel") is None:
        raise ValueError(f"not an RSS feed (root <{root.tag}>)")
    return parse_successfactors_stream([xml_text])


def _successfactors_chunks(host: str, params: dict):
    # the feed only answers when RSS is asked for (406 for JSON or application/xml)
    resp = requests.get(SUCCESSFACTORS_RSS.format(host=host), params=params, timeout=(15, 60), stream=True,
                        headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml"})
    resp.raise_for_status()
    return resp.iter_content(chunk_size=64 * 1024)


def _fetch_successfactors(token: str) -> list[dict]:
    last_exc: Exception | None = None
    for params in ({"rows": SUCCESSFACTORS_ROWS}, {}):   # all jobs; else the default first 20
        try:
            deadline = time.monotonic() + SUCCESSFACTORS_MAX_SECONDS
            jobs = parse_successfactors_stream(_successfactors_chunks(token, params), deadline)
            return [j for j in jobs if is_tech_role(j.get("title"))]
        except ValueError as exc:
            last_exc = exc
    raise last_exc or ValueError(f"successfactors '{token}' failed")


ATS_FETCHERS: dict[str, Callable[[str], list[dict]]] = {
    "greenhouse": _fetch_greenhouse,
    "lever": _fetch_lever,
    "ashby": _fetch_ashby,
    "smartrecruiters": _fetch_smartrecruiters,
    "workable": _fetch_workable,
    "recruitee": _fetch_recruitee,
    "personio": _fetch_personio,
    "workday": _fetch_workday,
    "successfactors": _fetch_successfactors,
    "breezy": _fetch_breezy,
    "teamtailor": _fetch_teamtailor,
}


def extract_company_boards(ats: str, tokens: list[str] | None = None,
                           pause_seconds: float = 0.5, meta: dict[str, dict] | None = None) -> ExtractResult:
    """meta: token -> {"company": .., "country": ..} from the company list (attached to records,
    used when a feed has no company name or country, e.g. Personio and Recruitee)."""
    tokens = tokens if tokens is not None else load_board_tokens(ats)
    meta = meta or {}
    fetch = ATS_FETCHERS[ats]
    keep: list[dict] = []
    warnings: list[str] = []
    status: dict[str, int | None] = {}
    for token in tokens:
        try:
            jobs = fetch(token)
        except (requests.RequestException, ValueError, ET.ParseError) as exc:  # any network/feed problem
            warnings.append(f"{ats} board '{token}' failed: {exc}")
            status[token] = None
            continue
        status[token] = len(jobs)
        extra = {"board_token": token}
        if meta.get(token):
            extra.update({f"board_{k}": v for k, v in meta[token].items() if v})
        keep.extend({**job, **extra} for job in jobs)
        time.sleep(pause_seconds)
    ok_boards = sum(1 for v in status.values() if v is not None)
    # Every board failing means the network (or the platform) is down - but only with several boards:
    # one or two broken boards must not stop the daily run (they are reported as warnings).
    if len(tokens) >= 3 and ok_boards == 0:
        raise RuntimeError(f"All {ats} boards failed - check network or board tokens")
    log.info("%s: %s/%s boards ok, %s data-related jobs", ats, ok_boards, len(tokens), len(keep))
    return ExtractResult(ats, keep, warnings, status)


def extract_greenhouse(tokens: list[str] | None = None, pause_seconds: float = 0.5,
                  meta: dict | None = None) -> ExtractResult:
    return extract_company_boards("greenhouse", tokens, pause_seconds, meta)


def extract_lever(tokens: list[str] | None = None, pause_seconds: float = 0.5,
                  meta: dict | None = None) -> ExtractResult:
    return extract_company_boards("lever", tokens, pause_seconds, meta)


def extract_ashby(tokens: list[str] | None = None, pause_seconds: float = 0.5,
                  meta: dict | None = None) -> ExtractResult:
    return extract_company_boards("ashby", tokens, pause_seconds, meta)


def extract_smartrecruiters(tokens: list[str] | None = None, pause_seconds: float = 0.5,
                  meta: dict | None = None) -> ExtractResult:
    return extract_company_boards("smartrecruiters", tokens, pause_seconds, meta)


def extract_workable(tokens: list[str] | None = None, pause_seconds: float = 0.5,
                  meta: dict | None = None) -> ExtractResult:
    return extract_company_boards("workable", tokens, pause_seconds, meta)


def extract_recruitee(tokens: list[str] | None = None, pause_seconds: float = 0.5,
                      meta: dict | None = None) -> ExtractResult:
    return extract_company_boards("recruitee", tokens, pause_seconds, meta)


def extract_personio(tokens: list[str] | None = None, pause_seconds: float = 0.5,
                     meta: dict | None = None) -> ExtractResult:
    return extract_company_boards("personio", tokens, pause_seconds, meta)


def extract_breezy(tokens: list[str] | None = None, pause_seconds: float = 0.5,
                   meta: dict[str, dict] | None = None) -> ExtractResult:
    return extract_company_boards("breezy", tokens, pause_seconds, meta)


def extract_teamtailor(tokens: list[str] | None = None, pause_seconds: float = 0.5,
                       meta: dict[str, dict] | None = None) -> ExtractResult:
    return extract_company_boards("teamtailor", tokens, pause_seconds, meta)


def breezy_id(record: dict) -> str:
    return f"{record.get('board_token', '')}:{record.get('id') or record.get('friendly_id') or record['url']}"


def teamtailor_id(record: dict) -> str:
    return f"{record.get('board_token', '')}:{record.get('guid') or record['link']}"


def extract_workday(tokens: list[str] | None = None, pause_seconds: float = 1.0,
                    meta: dict[str, dict] | None = None) -> ExtractResult:
    return extract_company_boards("workday", tokens, pause_seconds, meta)


def extract_successfactors(tokens: list[str] | None = None, pause_seconds: float = 1.0,
                           meta: dict[str, dict] | None = None) -> ExtractResult:
    return extract_company_boards("successfactors", tokens, pause_seconds, meta)


def workday_id(record: dict) -> str:
    return f"{record.get('board_token', '')}:{record.get('jobReqId') or record['externalPath']}"


def successfactors_id(record: dict) -> str:
    return f"{record.get('board_token', '')}:{record.get('guid') or record['link']}"


def recruitee_id(record: dict) -> str:
    return f"{record['board_token']}:{record.get('id') or record.get('slug')}"


def personio_id(record: dict) -> str:
    return f"{record['board_token']}:{record['id']}"


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
JOBICY_INDUSTRIES = ["data-science", "engineering", "design-multimedia"]
# Keyword searches catch roles listed under other industries.
JOBICY_TAGS = ["data engineer", "data analyst", "analytics", "machine learning",
               "qa", "tester", "devops", "ux", "ios", "android", "flutter", "react native"]


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
            if is_tech_role(j.get("jobTitle")):  # e.g. design-multimedia also has graphic/video roles
                keep[str(j["id"])] = j
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
            if is_tech_role(j.get("jobTitle")):  # keyword hits can be any role
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
    # data & AI
    "data engineer", "data analyst", "analytics engineer", "business intelligence",
    "data scientist", "machine learning engineer", "bi developer", "data platform", "analytics", "etl",
    # software, QA, design, devops, security
    "software engineer", "frontend", "backend", "full stack", "mobile developer",
    "ios developer", "android developer", "flutter developer", "react native",
    "qa engineer", "test automation", "ux designer", "product designer", "ui designer",
    "devops", "site reliability", "cloud engineer", "security engineer",
    # specialist roles (update 35)
    "solutions architect", "sales engineer", "soc analyst", "penetration tester", "embedded software",
    "firmware engineer", "fpga engineer", "verification engineer", "llm engineer", "computer vision",
    "nlp engineer", "integration engineer", "developer advocate", "data architect",
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
                if is_tech_role(j.get("title")):
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
# Europe is covered by Adzuna, so the key-based searches focus on the Middle East,
# where few companies use the public job-board platforms.
SEARCH_COUNTRIES = [  # (ISO code, name used in free-text queries)
    ("eg", "Egypt"), ("ae", "United Arab Emirates"), ("sa", "Saudi Arabia"), ("qa", "Qatar"),
    ("kw", "Kuwait"), ("bh", "Bahrain"), ("om", "Oman"), ("jo", "Jordan"),
]
# Countries first, so each day's slice spreads over several countries.
SEARCH_ROLES = ["software engineer", "data engineer", "data analyst", "developer", "devops engineer",
                "qa engineer", "cyber security", "network engineer", "sap consultant", "product manager",
                "ux designer", "machine learning engineer", "mobile developer", "flutter developer",
                "solutions architect", "presales engineer", "soc analyst", "embedded software engineer",
                "ai engineer", "it manager"]
ADZUNA_ROLES = ["data engineer", "data analyst", "software engineer", "frontend developer",
                "backend developer", "qa engineer", "ux designer", "devops engineer",
                "mobile developer", "data scientist", "cyber security", "sap consultant",
                "solutions architect", "embedded software engineer", "fpga engineer", "penetration tester",
                "pre-sales engineer", "computer vision engineer", "llm engineer", "integration engineer"]


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
                                params={"query": f"{role} jobs in {name}", "country": code, "language": "en"})
        except requests.HTTPError as exc:
            warnings.append(f"jsearch '{role}' in {code} failed: {exc}")
            if exc.response is not None and exc.response.status_code in (401, 403, 429):
                break  # bad key or quota used up: don't burn more requests today
            continue
        data = payload.get("data") if isinstance(payload, dict) else payload
        if isinstance(data, dict):  # some versions nest the list
            data = data.get("jobs") or data.get("data") or []
        for job in data or []:
            if is_tech_role(job.get("job_title")) and job.get("job_id"):
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
    roles = ["software developer", "data", "it", "network engineer", "qa tester", "ux designer", "mobile developer"]
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
            if is_tech_role(job.get("title")):
                job_key = str(job.get("id") or job.get("link"))
                keep[job_key] = {**job, "search_query": role, "search_location": location}
        time.sleep(pause_seconds)
    log.info("jooble: %s searches, %s data-related jobs", len(pairs), len(keep))
    return ExtractResult("jooble", list(keep.values()), warnings)


def jooble_id(record: dict) -> str:
    return str(record.get("id") or record.get("link"))


# Adzuna: job search API for the UK and most of the EU (Egypt / Gulf not covered).
# Needs ADZUNA_APP_ID + ADZUNA_APP_KEY. Free plan limits are per day/week/month,
# so a fixed daily budget walks through (role, country) pairs. Attribution
# ("Jobs by Adzuna") is required wherever the data is shown.
ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
ADZUNA_PER_DAY = int(os.environ.get("ADZUNA_REQUESTS_PER_DAY", "80"))  # free plan: ~2,500 a month
ADZUNA_COUNTRIES = ["gb", "de", "nl", "fr", "es", "it", "pl", "at", "be", "ch"]


def adzuna_pairs() -> list[tuple[str, str]]:
    return [(role, c) for role in ADZUNA_ROLES for c in ADZUNA_COUNTRIES]


def extract_adzuna(pairs: list | None = None, pause_seconds: float = 2.5) -> ExtractResult:
    app_id = os.environ.get("ADZUNA_APP_ID", "").strip()
    app_key = os.environ.get("ADZUNA_APP_KEY", "").strip()
    if not app_id or not app_key:
        return ExtractResult("adzuna", [], ["ADZUNA_APP_ID / ADZUNA_APP_KEY not set - source skipped"])
    pairs = pairs if pairs is not None else daily_slice(adzuna_pairs(), ADZUNA_PER_DAY)
    keep: dict[str, dict] = {}
    warnings: list[str] = []
    for role, country in pairs:
        try:
            payload = _get_json(ADZUNA_URL.format(country=country), params={
                "app_id": app_id, "app_key": app_key, "what": role,
                "results_per_page": 50, "max_days_old": 30, "content-type": "application/json"})
        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "?"
            warnings.append(f"adzuna '{role}' in {country} failed: HTTP {code}")
            if code in (401, 403, 429):
                break  # bad key or quota used up
            continue
        for job in payload.get("results") or []:
            if is_tech_role(job.get("title")) and job.get("id"):
                keep[str(job["id"])] = {**job, "search_query": role, "search_country": country}
        time.sleep(pause_seconds)  # free plan allows ~25 requests a minute
    log.info("adzuna: %s searches, %s tech jobs", len(pairs), len(keep))
    return ExtractResult("adzuna", list(keep.values()), warnings)


def adzuna_id(record: dict) -> str:
    return str(record["id"])


# Bundesagentur für Arbeit (Germany's federal employment agency): official public job
# search API with a published key. Search results have title, employer and place but no
# description, so these jobs have no skills. Rotating source (see dbt).
BA_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
BA_KEY = "jobboerse-jobsuche"  # public key published with the API, not a secret
BA_QUERIES = ["Softwareentwickler", "Software Engineer", "Data Engineer", "Data Scientist", "Data Analyst",
              "DevOps", "Cloud Engineer", "Frontend Developer", "Backend Developer", "Fullstack",
              "IT-Security", "SAP Berater", "Mobile Developer", "iOS Developer", "Android Developer", "Flutter",
              "QA Engineer", "UX Designer", "Embedded Software", "FPGA", "Solution Architect",
              "Presales", "SOC Analyst", "Penetration Tester",
              "Machine Learning", "Systemadministrator", "Netzwerkadministrator"]
BA_PAGES = int(os.environ.get("BA_PAGES_PER_QUERY", "2"))


def extract_bundesagentur(queries: list | None = None, pages: int | None = None,
                          pause_seconds: float = 1.0) -> ExtractResult:
    keep: dict[str, dict] = {}
    warnings: list[str] = []
    for query in queries if queries is not None else BA_QUERIES:
        for page in range(1, (pages or BA_PAGES) + 1):
            try:
                payload = _get_json(BA_URL, headers={"X-API-Key": BA_KEY}, params={
                    "was": query, "angebotsart": 1, "veroeffentlichtseit": 30, "page": page, "size": 100})
            except requests.HTTPError as exc:
                code = exc.response.status_code if exc.response is not None else "?"
                warnings.append(f"bundesagentur '{query}' page {page} failed: HTTP {code}")
                break
            items = payload.get("stellenangebote") or []
            for job in items:
                title = job.get("titel") or job.get("beruf")
                if job.get("refnr") and is_tech_role(title):
                    keep[job["refnr"]] = {**job, "search_query": query}
            if len(items) < 100:
                break
            time.sleep(pause_seconds)
    log.info("bundesagentur: %s tech jobs", len(keep))
    return ExtractResult("bundesagentur", list(keep.values()), warnings)


def bundesagentur_id(record: dict) -> str:
    return str(record["refnr"])


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
    "recruitee": SourceSpec(extract_recruitee, recruitee_id, required=False, board_ats="recruitee"),
    "personio": SourceSpec(extract_personio, personio_id, required=False, board_ats="personio"),
    "workday": SourceSpec(extract_workday, workday_id, required=False, board_ats="workday"),
    "breezy": SourceSpec(extract_breezy, breezy_id, required=False, board_ats="breezy"),
    "teamtailor": SourceSpec(extract_teamtailor, teamtailor_id, required=False, board_ats="teamtailor"),
    "successfactors": SourceSpec(extract_successfactors, successfactors_id, required=False,
                                 board_ats="successfactors"),
    # key-based aggregators: optional (missing key / quota reached only warns)
    "jsearch": SourceSpec(extract_jsearch, jsearch_id, required=False),
    "jooble": SourceSpec(extract_jooble, jooble_id, required=False),
    "adzuna": SourceSpec(extract_adzuna, adzuna_id, required=False),
    "bundesagentur": SourceSpec(extract_bundesagentur, bundesagentur_id, required=False),
}
