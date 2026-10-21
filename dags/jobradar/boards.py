"""Self-expanding registry of company career boards (Greenhouse, Lever, Ashby,
SmartRecruiters, Workable, Recruitee, Personio, Breezy, Teamtailor, Workday, SuccessFactors).

Lifecycle of a board in raw.company_boards:

    seeded from company_boards.csv ─┐
    harvested from apply links ─────┴─► candidate ──validate──► active ──3 failures in a row──► dead
                                                    └──404────► dead

* harvest: other sources (Himalayas, JSearch, Jooble, ...) often link to
  boards.greenhouse.io/<token>, jobs.lever.co/<token> or jobs.ashbyhq.com/<token>.
  Those tokens are collected from the last days of raw snapshots.
* validate: each candidate gets one request; a working board becomes active.
  A capped number per day keeps the run short and polite to the APIs.
* probe: dbt/seeds/companies.csv lists companies (name, country, industry) without
  knowing which hiring platform they use. Each company's likely board names are tried
  on every platform; a board is kept only if its tech jobs mention the company's
  country (so a different company with the same name is not picked up). Once one
  platform matches, the company's other guesses are skipped.
* extract: the daily extract uses all active boards (falls back to the CSV seed
  list if the registry is empty), and records success/failure per board.
"""
from __future__ import annotations

import csv
import json
import logging
import os
import re
import time
from pathlib import Path

import requests

from jobradar import sources

log = logging.getLogger(__name__)

MAX_VALIDATIONS_PER_RUN = 60   # discovered boards checked per run
MAX_SEED_VALIDATIONS = 300
DEAD_AFTER_FAILURES = 3
HARVEST_DAYS = 7
MAX_PROBES_PER_RUN = int(os.environ.get("BOARD_PROBES_PER_RUN", "800"))
PROBE_RECHECK_DAYS = 30
PROBE_PAUSE_SECONDS = 0.3   # a company with no tech jobs today is tried again a month later
COMPANIES_FILE = Path(os.environ.get("DBT_PROJECT_DIR") or Path(__file__).resolve().parents[2] / "dbt") \
    / "seeds" / "companies.csv"

DDL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE IF NOT EXISTS raw.company_boards (
    ats                   text        NOT NULL,
    token                 text        NOT NULL,
    status                text        NOT NULL DEFAULT 'candidate',  -- candidate | active | dead
    origin                text        NOT NULL,                      -- seed | discovered
    discovered_from       text,                                      -- source that linked to it
    first_seen_at         timestamptz NOT NULL DEFAULT now(),
    last_checked_at       timestamptz,
    last_ok_at            timestamptz,
    consecutive_failures  integer     NOT NULL DEFAULT 0,
    data_jobs_last_run    integer,
    PRIMARY KEY (ats, token)
);
ALTER TABLE raw.company_boards ADD COLUMN IF NOT EXISTS company_name text;
ALTER TABLE raw.company_boards ADD COLUMN IF NOT EXISTS country text;
ALTER TABLE raw.company_boards ADD COLUMN IF NOT EXISTS industry text;
ALTER TABLE raw.company_boards ADD COLUMN IF NOT EXISTS note text;
"""

# Python and Postgres (ARE) share this regex syntax; one capture group = token.
TOKEN_PATTERNS = {
    "greenhouse": r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([A-Za-z0-9_-]+)",
    "lever": r"jobs(?:\.eu)?\.lever\.co/([A-Za-z0-9_.-]+)",
    "ashby": r"jobs\.ashbyhq\.com/([A-Za-z0-9_.-]+)",
    "smartrecruiters": r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9_-]+)",
    "workable": r"apply\.workable\.com/(?!j/)([A-Za-z0-9_-]+)",  # /j/<code> is a job, not an account
    "recruitee": r"([A-Za-z0-9-]+)\.recruitee\.com",
    "personio": r"([A-Za-z0-9-]+)\.jobs\.personio\.(?:de|com)",
    # whole "<tenant>.<wdN>.myworkdayjobs.com/[en-US/]<site>"; normalised to "<tenant>.<wdN>/<site>"
    "workday": r"([a-z0-9-]+\.wd[0-9]+\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?[A-Za-z0-9_-]+)",
    "breezy": r"([A-Za-z0-9-]+)\.breezy\.hr",
    "teamtailor": r"([A-Za-z0-9-]+)\.teamtailor\.com",
}
_NOT_TOKENS = {"embed", "api", "v1", "jobs", "job", "j", "boards", "careers", "search", "apply", "oneclick-ui",
               "www", "app", "help", "support", "docs", "blog", "career", "marketplace", "status", ""}


def normalize_token(raw: str, ats: str = "greenhouse") -> str | None:
    token = sources.normalize_board_token(ats, raw.strip().strip(".-_"))
    if token.lower() in _NOT_TOKENS or len(token) < 2 or len(token) > 80:
        return None
    return token


def tokens_in_text(text: str) -> set[tuple[str, str]]:
    """(ats, token) pairs mentioned in a piece of text (used by tests and as a reference)."""
    found = set()
    for ats, pattern in TOKEN_PATTERNS.items():
        for raw in re.findall(pattern, text or ""):
            token = normalize_token(raw, ats)
            if token:
                found.add((ats, token))
    return found


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()


def seed(conn, rows: list[tuple[str, str]], companies: dict[tuple[str, str], str | dict] | None = None) -> int:
    """Add CSV rows that aren't in the registry yet, as candidates (validated before use).
    companies: display names (or {"company", "country"}) from the CSV, attached where still empty."""
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO raw.company_boards (ats, token, origin) VALUES (%s, %s, 'seed') "
            "ON CONFLICT (ats, token) DO NOTHING",
            rows,
        )
        added = cur.rowcount
        # A listed board that failed before is checked again every few days: the company may have
        # opened jobs again, or the reader learned a new way to reach it (e.g. Greenhouse's EU servers).
        cur.executemany(
            "UPDATE raw.company_boards SET status = 'candidate', consecutive_failures = 0, origin = 'seed' "
            "WHERE ats = %s AND token = %s AND status = 'dead' "
            "AND coalesce(last_checked_at, 'epoch'::timestamptz) < now() - interval '3 days'",
            rows,
        )
        if companies:
            details = {k: (v if isinstance(v, dict) else {"company": v}) for k, v in companies.items()}
            cur.executemany(
                "UPDATE raw.company_boards SET company_name = coalesce(company_name, nullif(%s, '')), "
                "country = coalesce(country, nullif(%s, '')) WHERE ats = %s AND token = %s",
                [(d.get("company") or "", d.get("country") or "", ats, token) for (ats, token), d in details.items()],
            )
    conn.commit()
    return max(added, 0)


def harvest(conn, days: int = HARVEST_DAYS) -> int:
    """Find board tokens in recent raw payloads of all sources; insert new ones as candidates."""
    found: dict[tuple[str, str], str] = {}
    with conn.cursor() as cur:
        for ats, pattern in TOKEN_PATTERNS.items():
            cur.execute(
                """
                select distinct m[1], s.source
                from raw.job_posting_snapshots s,
                     regexp_matches(s.payload::text, %s, 'g') as m
                where s.snapshot_date >= current_date - %s
                """,
                (pattern, days),
            )
            for raw_token, source in cur.fetchall():
                token = normalize_token(raw_token, ats)
                if token:
                    found.setdefault((ats, token), source)
        if not found:
            return 0
        cur.executemany(
            "INSERT INTO raw.company_boards (ats, token, origin, discovered_from) "
            "VALUES (%s, %s, 'discovered', %s) ON CONFLICT (ats, token) DO NOTHING",
            [(ats, token, src) for (ats, token), src in found.items()],
        )
        added = max(cur.rowcount, 0)
    conn.commit()
    log.info("harvest: %s board links seen, %s new candidates", len(found), added)
    return added


def validate_board(ats: str, token: str) -> tuple[str, int | None]:
    """-> ('active', data_jobs) | ('dead', None) on 404 | ('retry', None) on other errors."""
    try:
        if ats == "workday":  # one list request is enough to know the board exists (a full fetch is ~100)
            _, list_url, _ = sources.workday_urls(token)
            data = sources._workday_post(list_url, {"appliedFacets": {}, "limit": sources.WORKDAY_PAGE,
                                                    "offset": 0, "searchText": ""})
            return "active", int(data.get("total") or 0)
        jobs = sources.ATS_FETCHERS[ats](token)
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else None
        # Lever's fetcher raises without a response when both instances 404
        return ("dead", None) if code in (404, None) else ("retry", None)
    except ValueError:  # answered, but not a job board (e.g. Workable account without a jobs list)
        return "dead", None
    except (requests.ConnectionError, requests.Timeout):
        return "retry", None
    return "active", len(jobs)


def validate_candidates(conn, limit: int = MAX_VALIDATIONS_PER_RUN) -> dict[str, int]:
    with conn.cursor() as cur:
        # seeds are always validated (the CSV is short); discovered boards are capped per run
        cur.execute(
            """
            (select ats, token from raw.company_boards
             where status = 'candidate' and origin = 'seed' order by token limit %s)
            union all
            (select ats, token from raw.company_boards
             where status = 'candidate' and origin not in ('seed', 'probe')
             order by first_seen_at, token limit %s)
            """,
            (MAX_SEED_VALIDATIONS, limit),
        )
        todo = cur.fetchall()
    counts = {"active": 0, "dead": 0, "retry": 0}
    for ats, token in todo:
        with sources.no_connect_retries():  # a failed check is simply retried next run
            result, data_jobs = validate_board(ats, token)
        counts[result] += 1
        with conn.cursor() as cur:
            if result == "retry":
                cur.execute(
                    "update raw.company_boards set last_checked_at = now() where ats = %s and token = %s",
                    (ats, token),
                )
            else:
                cur.execute(
                    """
                    update raw.company_boards
                    set status = %s, last_checked_at = now(),
                        last_ok_at = case when %s = 'active' then now() else last_ok_at end,
                        data_jobs_last_run = %s
                    where ats = %s and token = %s
                    """,
                    (result, result, data_jobs, ats, token),
                )
        conn.commit()
    log.info("validate: %s checked -> %s", len(todo), counts)
    return counts


# --------------------------------------------------------------------------- #
# Probing: find which hiring platform each listed company uses
# --------------------------------------------------------------------------- #
# Words that show a board belongs to a company in that country (searched in its jobs).
COUNTRY_KEYWORDS = {
    "Egypt": ["egypt", "cairo", "giza", "alexandria", "mansoura", "6th of october", "new capital"],
    "United Arab Emirates": ["united arab emirates", "uae", "dubai", "abu dhabi", "sharjah", "ajman"],
    "Saudi Arabia": ["saudi", "ksa", "riyadh", "jeddah", "dammam", "khobar", "neom"],
    "Qatar": ["qatar", "doha"],
    "Kuwait": ["kuwait"],
    "Bahrain": ["bahrain", "manama"],
    "Oman": ["oman", "muscat"],
    "Jordan": ["jordan", "amman"],
    "Palestine": ["palestine", "ramallah", "gaza", "nablus", "bethlehem", "hebron"],
    "Morocco": ["morocco", "casablanca", "rabat", "marrakech", "tangier"],
    "Tunisia": ["tunisia", "tunis", "sfax", "sousse"],
    "Algeria": ["algeria", "algiers", "oran"],
    "Lebanon": ["lebanon", "beirut"],
    "Iraq": ["iraq", "baghdad", "erbil", "basra"],
    "Pakistan": ["pakistan", "karachi", "lahore", "islamabad", "rawalpindi", "faisalabad"],
    "Bangladesh": ["bangladesh", "dhaka", "chittagong", "chattogram", "sylhet"],
    "Kazakhstan": ["kazakhstan", "almaty", "astana"],
    "Uzbekistan": ["uzbekistan", "tashkent"],
    "Georgia": ["tbilisi", "batumi", "sakartvelo"],
    "Armenia": ["armenia", "yerevan"],
    "Azerbaijan": ["azerbaijan", "baku"],
    "Serbia": ["serbia", "belgrade", "novi sad"],
    "Kosovo": ["kosovo", "pristina", "prishtina", "prishtinë"],
    "Bosnia and Herzegovina": ["bosnia", "sarajevo", "tuzla", "banja luka", "mostar"],
    "Croatia": ["croatia", "zagreb", "rijeka", "osijek"],
    "Slovakia": ["slovakia", "bratislava", "košice", "kosice", "žilina", "zilina"],
    "Slovenia": ["slovenia", "ljubljana", "maribor"],
    "Nigeria": ["nigeria", "lagos", "abuja", "port harcourt", "ibadan"],
    "Kenya": ["kenya", "nairobi", "mombasa"],
    "Ethiopia": ["ethiopia", "addis ababa"],
    "Rwanda": ["rwanda", "kigali"],
    "Ghana": ["ghana", "accra", "kumasi"],
    "South Africa": ["south africa", "cape town", "johannesburg", "durban", "pretoria"],
    "Sri Lanka": ["sri lanka", "colombo"],
    "Nepal": ["nepal", "kathmandu", "lalitpur"],
    "Iceland": ["iceland", "reykjavik", "reykjavík"],
    # remote-first employers: accept the board if its tech jobs are remote
    "Remote": ["remote", "anywhere", "worldwide", "work from home", "distributed"],
    "Netherlands": ["netherlands", "amsterdam", "rotterdam", "utrecht", "eindhoven", "the hague"],
    "Germany": ["germany", "deutschland", "berlin", "munich", "münchen", "hamburg", "frankfurt", "cologne"],
    "United Kingdom": ["united kingdom", "london", "manchester", "edinburgh", "uk"],
    "Spain": ["spain", "españa", "madrid", "barcelona", "valencia"],
    "France": ["france", "paris", "lyon"],
    "Sweden": ["sweden", "stockholm"],
    "Finland": ["finland", "helsinki"],
    "Estonia": ["estonia", "tallinn"],
    "Lithuania": ["lithuania", "vilnius", "kaunas"],
    "Denmark": ["denmark", "copenhagen", "aarhus"],
    "Czechia": ["czech", "czechia", "prague", "brno"],
}
_MENA = ["mena", "middle east", "gcc"]
MENA_COUNTRIES = ("Egypt", "United Arab Emirates", "Saudi Arabia", "Qatar", "Kuwait", "Bahrain", "Oman", "Jordan", "Palestine",
                  "Morocco", "Tunisia", "Algeria", "Lebanon", "Iraq")


def load_companies(path: Path = COMPANIES_FILE) -> list[dict]:
    if not path.exists():
        log.warning("company list %s not found - probing skipped", path)
        return []
    with path.open(encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if (r.get("company") or "").strip()]


def slug_candidates(company: str, slugs: str = "") -> list[str]:
    """Likely board names: explicit ones from the CSV, else 'mnthalan' and 'mnt-halan'."""
    explicit = [x.strip() for x in (slugs or "").split(";") if x.strip()]
    if explicit:
        return explicit
    words = re.sub(r"[^A-Za-z0-9]+", " ", company).split()
    out = ["".join(words).lower(), "-".join(words).lower()]
    return list(dict.fromkeys(t for t in out if t))


def probe_tokens(company: str, slugs: str = "") -> list[tuple[str, str]]:
    pairs = []
    for slug in slug_candidates(company, slugs):
        for ats in sources.PROBE_ATS:
            if ats == "smartrecruiters" and slug.islower():
                # SmartRecruiters ids are case-sensitive and usually CamelCase ("DeliveryHero")
                words = re.sub(r"[^A-Za-z0-9]+", " ", company).split()
                token = "".join(w[:1].upper() + w[1:] for w in words) if slug == "".join(words).lower() else slug
            else:
                token = slug.lower() if ats == "lever" else slug   # the Lever reader also tries "Bosta"
            token = normalize_token(token, ats)
            if token:
                pairs.append((ats, token))
    return list(dict.fromkeys(pairs))


def seed_probes(conn, companies: list[dict]) -> int:
    """Insert every (platform, guessed board name) as a probe candidate with company metadata.
    Boards already in the registry (CSV seeds, discovered) just get the metadata attached."""
    rows = []
    for c in companies:
        if (c.get("country") or "").strip() == "Global":
            continue  # already in the board list; listed only for their industry
        for ats, token in probe_tokens(c["company"], c.get("slugs", "")):
            rows.append((ats, token, c["company"].strip(), (c.get("country") or "").strip() or None,
                         (c.get("industry") or "").strip() or None))
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            """
            insert into raw.company_boards (ats, token, origin, company_name, country, industry)
            values (%s, %s, 'probe', %s, %s, %s)
            on conflict (ats, token) do update set
                company_name = coalesce(raw.company_boards.company_name, excluded.company_name),
                country      = coalesce(raw.company_boards.country, excluded.country),
                industry     = coalesce(raw.company_boards.industry, excluded.industry)
            """,
            rows,
        )
    conn.commit()
    return len(rows)


def matches_country(jobs: list[dict], country: str | None) -> bool:
    if not country or country not in COUNTRY_KEYWORDS:
        return True  # nothing to check against
    text = json.dumps(jobs, ensure_ascii=False).lower()
    words = COUNTRY_KEYWORDS[country] + (_MENA if country in MENA_COUNTRIES else [])
    return any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", text) for w in words)


def probe_board(ats: str, token: str, country: str | None) -> tuple[str, str | None]:
    """-> (status, note). active = board exists and its tech jobs are in the company's country."""
    try:
        jobs = sources.ATS_FETCHERS[ats](token)
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else None
        return ("dead", "not found") if code in (404, 410, None) else ("retry", f"HTTP {code}")
    except ValueError:
        return "dead", "not a job board"
    except (requests.ConnectionError, requests.Timeout):
        return "retry", "network"
    if not jobs:
        return "candidate", "no tech jobs to verify yet"
    if matches_country(jobs, country):
        return "active", None
    return "dead", f"jobs not in {country} (probably a different company)"


def validate_probes(conn, limit: int = MAX_PROBES_PER_RUN) -> dict[str, int]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select b.ats, b.token, b.country, b.company_name
            from raw.company_boards b
            where b.status = 'candidate' and b.origin = 'probe'
              and (b.last_checked_at is null or b.last_checked_at < now() - %s * interval '1 day')
              and not exists (select 1 from raw.company_boards a
                              where a.company_name = b.company_name and a.status = 'active')
            order by b.last_checked_at nulls first, b.company_name, b.ats
            limit %s
            """,
            (PROBE_RECHECK_DAYS, limit),
        )
        todo = cur.fetchall()
    counts = {"active": 0, "dead": 0, "candidate": 0, "retry": 0, "skipped": 0}
    found: set[str] = set()
    for ats, token, country, company in todo:
        if company in found:
            counts["skipped"] += 1
            continue
        with sources.no_connect_retries():
            status, note = probe_board(ats, token, country)
        counts[status] += 1
        time.sleep(PROBE_PAUSE_SECONDS)
        with conn.cursor() as cur:
            cur.execute(
                """
                update raw.company_boards
                set status = %s, note = %s,
                    -- network errors are retried next run; everything else waits for the recheck
                    last_checked_at = case when %s = 'retry' then null else now() end,
                    last_ok_at = case when %s = 'active' then now() else last_ok_at end
                where ats = %s and token = %s
                """,
                ("candidate" if status == "retry" else status, note, status, status, ats, token),
            )
        conn.commit()
        if status == "active":
            found.add(company)
            log.info("probe: %s uses %s (%s)", company, ats, token)
    log.info("probe: %s checked -> %s", len(todo), counts)
    return counts


def board_meta(conn, ats: str) -> dict[str, dict]:
    """token -> {"company", "country"} for active boards that came from the company list."""
    with conn.cursor() as cur:
        cur.execute(
            "select token, company_name, country from raw.company_boards "
            "where ats = %s and status = 'active' and company_name is not null",
            (ats,),
        )
        return {t: {"company": c, "country": k} for t, c, k in cur.fetchall()}


def active_tokens(conn, ats: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            "select token from raw.company_boards where ats = %s and status = 'active' order by token",
            (ats,),
        )
        return [r[0] for r in cur.fetchall()]


def record_extraction(conn, ats: str, board_status: dict[str, int | None]) -> None:
    """Update per-board health after the daily extract; 3 failures in a row -> dead."""
    with conn.cursor() as cur:
        for token, data_jobs in board_status.items():
            if data_jobs is None:
                cur.execute(
                    """
                    update raw.company_boards
                    set consecutive_failures = consecutive_failures + 1, last_checked_at = now(),
                        status = case when consecutive_failures + 1 >= %s then 'dead' else status end
                    where ats = %s and token = %s
                    """,
                    (DEAD_AFTER_FAILURES, ats, token),
                )
            else:
                cur.execute(
                    """
                    update raw.company_boards
                    set consecutive_failures = 0, last_checked_at = now(), last_ok_at = now(),
                        data_jobs_last_run = %s
                    where ats = %s and token = %s
                    """,
                    (data_jobs, ats, token),
                )
    conn.commit()
