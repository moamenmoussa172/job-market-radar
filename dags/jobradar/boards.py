"""Self-expanding registry of company career boards (Greenhouse, Lever, Ashby,
SmartRecruiters, Workable).

Lifecycle of a board in raw.company_boards:

    seeded from company_boards.csv ─┐
    harvested from apply links ─────┴─► candidate ──validate──► active ──3 failures in a row──► dead
                                                    └──404────► dead

* harvest: other sources (Himalayas, JSearch, Jooble, ...) often link to
  boards.greenhouse.io/<token>, jobs.lever.co/<token> or jobs.ashbyhq.com/<token>.
  Those tokens are collected from the last days of raw snapshots.
* validate: each candidate gets one request; a working board becomes active.
  A capped number per day keeps the run short and polite to the APIs.
* extract: the daily extract uses all active boards (falls back to the CSV seed
  list if the registry is empty), and records success/failure per board.
"""
from __future__ import annotations

import logging
import re

import requests

from jobradar import sources

log = logging.getLogger(__name__)

MAX_VALIDATIONS_PER_RUN = 60   # discovered boards checked per run
MAX_SEED_VALIDATIONS = 300
DEAD_AFTER_FAILURES = 3
HARVEST_DAYS = 7

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
"""

# Python and Postgres (ARE) share this regex syntax; one capture group = token.
TOKEN_PATTERNS = {
    "greenhouse": r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([A-Za-z0-9_-]+)",
    "lever": r"jobs(?:\.eu)?\.lever\.co/([A-Za-z0-9_.-]+)",
    "ashby": r"jobs\.ashbyhq\.com/([A-Za-z0-9_.-]+)",
    "smartrecruiters": r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9_-]+)",
    "workable": r"apply\.workable\.com/(?!j/)([A-Za-z0-9_-]+)",  # /j/<code> is a job, not an account
}
_NOT_TOKENS = {"embed", "api", "v1", "jobs", "job", "j", "boards", "careers", "search", "apply", "oneclick-ui", ""}


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


def seed(conn, rows: list[tuple[str, str]]) -> int:
    """Add CSV rows that aren't in the registry yet, as candidates (validated before use)."""
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO raw.company_boards (ats, token, origin) VALUES (%s, %s, 'seed') "
            "ON CONFLICT (ats, token) DO NOTHING",
            rows,
        )
        added = cur.rowcount
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
             where status = 'candidate' and origin <> 'seed' order by first_seen_at, token limit %s)
            """,
            (MAX_SEED_VALIDATIONS, limit),
        )
        todo = cur.fetchall()
    counts = {"active": 0, "dead": 0, "retry": 0}
    for ats, token in todo:
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
