"""Extractors for each job source.

Every extractor returns a list of *untouched* source records (dicts) for
data-related jobs, plus a stable `source_job_id` for each one.
Parsing (skills, seniority, remote scope, salary) is NOT done here; it
belongs to the silver layer so we can re-run it over history.
"""
from __future__ import annotations

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
    return ExtractResult("remotive", keep)


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
# Greenhouse public job boards - one call per company board token.
# Board list lives in greenhouse_boards.txt (edit freely).
# --------------------------------------------------------------------------- #
GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
BOARDS_FILE = Path(__file__).with_name("greenhouse_boards.txt")


def load_board_tokens(path: Path = BOARDS_FILE) -> list[str]:
    tokens = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            tokens.append(line.lower())
    return sorted(set(tokens))


def extract_greenhouse(tokens: list[str] | None = None, pause_seconds: float = 0.5) -> ExtractResult:
    tokens = tokens if tokens is not None else load_board_tokens()
    keep: list[dict] = []
    warnings: list[str] = []
    ok_boards = 0
    for token in tokens:
        try:
            payload = _get_json(GREENHOUSE_URL.format(token=token), params={"content": "true"})
        except requests.HTTPError as exc:
            warnings.append(f"greenhouse board '{token}' failed: {exc}")
            continue
        ok_boards += 1
        for job in payload.get("jobs", []):
            if is_data_role(job.get("title")):
                keep.append({**job, "board_token": token})
        time.sleep(pause_seconds)
    if tokens and ok_boards == 0:
        raise RuntimeError("All Greenhouse boards failed - check network or board tokens")
    log.info("greenhouse: %s/%s boards ok, %s data-related jobs", ok_boards, len(tokens), len(keep))
    return ExtractResult("greenhouse", keep, warnings)


def greenhouse_id(record: dict) -> str:
    return f"{record['board_token']}:{record['id']}"


# --------------------------------------------------------------------------- #
SOURCES: dict[str, tuple[Callable[[], ExtractResult], Callable[[dict], str]]] = {
    "remotive": (extract_remotive, remotive_id),
    "arbeitnow": (extract_arbeitnow, arbeitnow_id),
    "greenhouse": (extract_greenhouse, greenhouse_id),
}
