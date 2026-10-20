"""Radarak Weekly: one email on Sundays with the week's new jobs, sent through Buttondown.

Free Buttondown covers the first 100 subscribers; everyone gets the same email (per-person filters
need Buttondown's paid tagging). Configure in .env:
  BUTTONDOWN_API_KEY   - Buttondown -> Settings -> API
  BUTTONDOWN_USERNAME  - your newsletter's username (shows the subscribe box on the site)
  BUTTONDOWN_STATUS    - draft (default: you review and press Send) or about_to_send (sends by itself)
  NEWSLETTER_WEEKDAY   - 0=Monday ... 6=Sunday (default 6)
One email per week at most: sent weeks are recorded in raw.newsletter_log.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
from collections import Counter
from urllib.parse import quote

import requests

log = logging.getLogger(__name__)

BUTTONDOWN_API = "https://api.buttondown.com/v1/emails"
PLACES = ["Egypt", "Saudi Arabia", "United Arab Emirates", "Remote", "Qatar", "Kuwait", "Jordan", "Bahrain",
          "Oman", "Morocco", "Palestine", "Germany", "United Kingdom", "Netherlands"]
PLACES_SHOWN = 6
PICKS = 5

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw.newsletter_log (
    week_start date PRIMARY KEY,
    sent_at timestamptz NOT NULL DEFAULT now(),
    email_id text,
    status text
)"""


def _slug(text: str) -> str:
    from jobradar.seo_pages import slug
    return slug(text)


def _unique(jobs: list[dict]) -> list[dict]:
    from jobradar.seo_pages import _unique as u
    return u(jobs)


def new_this_week(jobs: list[dict], today: dt.date) -> list[dict]:
    since = (today - dt.timedelta(days=7)).isoformat()
    return _unique([j for j in jobs if (j.get("fs") or j.get("p") or "") > since])


def _in(j: dict, place: str) -> bool:
    return j.get("w") == "Remote" if place == "Remote" else place in (j.get("co") or [])


def build_digest(jobs: list[dict], meta: dict, base: str, today: dt.date) -> tuple[str, str]:
    """(subject, markdown body) for this week."""
    base = base.rstrip("/") + "/"
    new = new_this_week(jobs, today)
    start = today - dt.timedelta(days=6)
    span = f"{start.day} {start:%b}–{today.day} {today:%b}" if start.month != today.month else f"{start.day}–{today.day} {today:%b}"
    subject = f"Radarak Weekly: {len(new):,} new tech jobs ({span})"
    skills = meta.get("skills", [])
    top_sk = [skills[i] for i, _ in Counter(k for j in new for k in j.get("k", [])).most_common(6) if i < len(skills)]
    lines = [
        f"**{len(new):,} new tech jobs this week.** Here's where they are and what they ask for.",
        "",
        f"_{len(new):,} وظيفة تك جديدة الأسبوع ده. دي أماكنها والمهارات المطلوبة فيها._",
        "",
    ]
    if top_sk:
        lines += [f"**Most asked skills this week:** {', '.join(top_sk)}", ""]
    counts = {p: [j for j in new if _in(j, p)] for p in PLACES}
    shown = sorted((p for p in PLACES if counts[p]), key=lambda p: (p not in ("Egypt", "Remote"), -len(counts[p])))[:PLACES_SHOWN]
    for p in shown:
        pj = counts[p]
        page = base + "jobs/" + ("remote" if p == "Remote" else _slug(p)) + "/"
        title = "Remote" if p == "Remote" else p
        lines += ["---", "", f"### {title}: {len(pj):,} new jobs", ""]
        tracks = Counter(j.get("tr") for j in pj if j.get("tr")).most_common(4)
        if tracks:
            lines += [" · ".join(f"{tr} **{n}**" for tr, n in tracks), ""]
        picks = sorted(pj, key=lambda j: (not j.get("$"), not ((j.get("f") or 0) & 1), j.get("p", "")), reverse=False)[:PICKS]
        for j in picks:
            extra = []
            if j.get("$"):
                lo, hi = j["$"]
                extra.append(f"${lo}k" if lo == hi else f"${lo}k–${hi}k")
            if (j.get("f") or 0) & 1:
                extra.append("visa / relocation")
            if p != "Remote" and j.get("w") == "Remote":
                extra.append("remote")
            tail = f" · {', '.join(extra)}" if extra else ""
            lines.append(f"- [{j.get('t')}]({base}#job={quote(j['id'])}), {j.get('c') or ''}{tail}")
        lines += ["", f"[See all {title} jobs →]({page})", ""]
    juniors = [j for j in new if j.get("s") in ("Intern / Student", "Junior")]
    lines += ["---", ""]
    if juniors:
        lines += [f"🎓 **{len(juniors):,} new intern and junior jobs** this week: [Juniors corner →]({base}juniors/)", ""]
    lines += [f"🎯 Upload your CV on [radarak.online]({base}) to see which of these you match, and what to learn next.", "",
              "Free, no sign-up. Reply to this email to tell me what you'd like to see here."]
    return subject, "\n".join(lines)


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(SCHEMA)
    conn.commit()


def already_sent(conn, week_start: dt.date) -> bool:
    with conn.cursor() as cur:
        cur.execute("select 1 from raw.newsletter_log where week_start = %s", (week_start,))
        return cur.fetchone() is not None


def record(conn, week_start: dt.date, email_id: str | None, status: str) -> None:
    with conn.cursor() as cur:
        cur.execute("insert into raw.newsletter_log (week_start, email_id, status) values (%s, %s, %s) "
                    "on conflict (week_start) do nothing", (week_start, email_id, status))
    conn.commit()


def create_email(api_key: str, subject: str, body: str, status: str) -> dict:
    resp = requests.post(BUTTONDOWN_API, timeout=60, json={"subject": subject, "body": body, "status": status},
                         headers={"Authorization": f"Token {api_key}", "Content-Type": "application/json"})
    if resp.status_code >= 300:
        raise RuntimeError(f"Buttondown HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def send_from_env(conn, jobs: list[dict], meta: dict, base: str, today: dt.date | None = None) -> dict:
    """Create this week's email if it's newsletter day, configured, and not done yet. Returns what happened."""
    today = today or dt.date.today()
    key = os.environ.get("BUTTONDOWN_API_KEY", "").strip()
    if not key:
        return {"skipped": "BUTTONDOWN_API_KEY not set"}
    weekday = int(os.environ.get("NEWSLETTER_WEEKDAY", "6") or 6)
    if today.weekday() != weekday:
        return {"skipped": f"not newsletter day (weekday {today.weekday()} != {weekday})"}
    status = os.environ.get("BUTTONDOWN_STATUS", "draft").strip() or "draft"
    week_start = today - dt.timedelta(days=today.weekday())
    ensure_schema(conn)
    if already_sent(conn, week_start):
        return {"skipped": "already created this week"}
    subject, body = build_digest(jobs, meta, base, today)
    email = create_email(key, subject, body, status)
    record(conn, week_start, str(email.get("id") or ""), status)
    log.info("newsletter %s: %s", status, subject)
    return {"subject": subject, "status": status, "id": email.get("id")}
