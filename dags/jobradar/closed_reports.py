"""Jobs that visitors reported as closed ("This job was removed / has expired").

The site has no server, so a report is an anonymous GoatCounter event named "closed/<job id>" (the same
counter that counts visits; nothing about the visitor is sent). Every run reads those events back with
GoatCounter's API (GOATCOUNTER_API_TOKEN, a token with "Read statistics" only) and keeps them in
raw.closed_reports; the site leaves those jobs out from then on.

Without the token nothing happens: the reporter still stops seeing the job in their own browser.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import re

import requests

log = logging.getLogger(__name__)

LOOKBACK_DAYS = 60
JOB_ID = re.compile(r"^/?(?:report-)?closed/([0-9a-f]{12})(?:/.*)?$")   # also the older "report-closed/<id>/<company>"

DDL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE IF NOT EXISTS raw.closed_reports (
    job_id       text        PRIMARY KEY,        -- the 12-character id used on the site
    reports      integer     NOT NULL,
    first_seen   timestamptz NOT NULL DEFAULT now(),
    last_seen    timestamptz NOT NULL DEFAULT now()
);
"""


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()


def fetch_reports(code: str, token: str, today: dt.date | None = None, session=requests) -> dict[str, int]:
    """{job id: number of reports} from GoatCounter's hits API (paths "closed/<id>")."""
    today = today or dt.date.today()
    url = f"https://{code}.goatcounter.com/api/v0/stats/hits"
    params = {"start": (today - dt.timedelta(days=LOOKBACK_DAYS)).isoformat(), "end": (today + dt.timedelta(days=1)).isoformat(),
              "filter": "closed/", "limit": 100}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    out: dict[str, int] = {}
    seen_ids: list[int] = []
    for _ in range(50):                                   # 50 pages x 100 paths is plenty
        q = dict(params)
        if seen_ids:
            q["exclude_paths"] = ",".join(str(i) for i in seen_ids)
        resp = session.get(url, params=q, headers=headers, timeout=30)
        resp.raise_for_status()
        body = resp.json() or {}
        hits = body.get("hits") or []
        for h in hits:
            m = JOB_ID.match(str(h.get("path") or ""))
            if m:
                out[m.group(1)] = out.get(m.group(1), 0) + int(h.get("count") or 0)
            if h.get("path_id") is not None:
                seen_ids.append(h["path_id"])
        if not body.get("more") or not hits:
            break
    return out


def save(conn, reports: dict[str, int]) -> None:
    with conn.cursor() as cur:
        for job_id, n in reports.items():
            cur.execute("""insert into raw.closed_reports (job_id, reports) values (%s, %s)
                           on conflict (job_id) do update set reports = greatest(raw.closed_reports.reports, excluded.reports),
                                                              last_seen = now()""", (job_id, max(n, 1)))
    conn.commit()


def sync(conn, today: dt.date | None = None) -> dict:
    """Read new reports into the warehouse. Never raises."""
    code, token = os.environ.get("GOATCOUNTER_CODE", "").strip(), os.environ.get("GOATCOUNTER_API_TOKEN", "").strip()
    if not code or not token:
        return {"skipped": "GOATCOUNTER_CODE / GOATCOUNTER_API_TOKEN not set"}
    try:
        ensure_schema(conn)
        reports = fetch_reports(code, token, today)
        save(conn, reports)
        log.info("closed reports: %s jobs", len(reports))
        return {"reported_jobs": len(reports)}
    except Exception as exc:  # noqa: BLE001 - a report sync never breaks publishing
        log.warning("closed reports sync failed: %s", exc)
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
        return {"error": str(exc)[:200]}


def closed_ids(conn) -> set[str]:
    """The 12-character ids of jobs visitors reported as closed."""
    if conn is None:
        return set()
    try:
        with conn.cursor() as cur:
            cur.execute("select job_id from raw.closed_reports")
            return {r[0] for r in cur.fetchall()}
    except Exception:  # noqa: BLE001 - table not there yet
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
        return set()
