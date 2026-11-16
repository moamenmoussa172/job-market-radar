"""Referral offers: people who work at a company and are happy to refer job seekers there.

How it works (no server, no accounts):
* A referrer fills in a Google Form. Answers land in the owner's Google Sheet (private).
* The owner ticks "Approved" for real offers. A second tab, "Published", shows only approved rows and only
  the columns that are meant to be public (QUERY formula, see REFERRALS.md); only that tab is published as CSV.
* Every run reads that CSV (REFERRALS_CSV_URL) and writes data/referrals.json for the site. The site links each
  offer to the referrer's own LinkedIn profile; the job seeker writes to them there. Radarak never sees seekers.

Nothing here ever fails the run: no URL, a bad sheet or a network error just means no referrals today.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import logging
import os
import re

import requests

log = logging.getLogger(__name__)

MAX_AGE_DAYS = 90            # offers expire; the referrer can fill in the form again to renew
MAX_OFFERS = 2000
LINKEDIN = re.compile(r"^https?://([a-z]{2,3}\.)?(www\.)?linkedin\.com/in/[A-Za-z0-9\-_%]{2,100}/?(\?.*)?$")
LEVELS = {                   # answers in the form -> seniority values used on the site
    "intern & junior": ["Intern / Student", "Junior"],
    "intern and junior": ["Intern / Student", "Junior"],
    "mid": ["Mid"],
    "mid-level": ["Mid"],
    "senior": ["Senior"],
    "lead and above": ["Lead / Principal", "Head / Director"],
    "lead & above": ["Lead / Principal", "Head / Director"],
}
# words that suggest someone is selling referrals or fishing for data: those offers are dropped
BLOCK = re.compile(r"\b(fee|fees|pay me|paid referral|price|usd|egp|sar|aed|whats ?app|telegram|wa\.me|t\.me|"
                   r"password|national id|passport|bank account|credit card)\b|\$\d", re.I)
COMPANY_SUFFIX = re.compile(r"[,.]?\s+(inc|llc|ltd|limited|gmbh|s\.?a\.?e?|plc|co|corp|corporation|group|holding|"
                            r"egypt|ksa|uae|mena|middle east)\.?$", re.I)


def company_key(name: str) -> str:
    """'Valeo Egypt LLC' and 'valeo' -> 'valeo', so offers match the company names on jobs."""
    k = re.sub(r"\s+", " ", (name or "").strip().lower())
    for _ in range(3):
        k = COMPANY_SUFFIX.sub("", k).strip()
    return k


def _clean(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    text = re.sub(r"https?://\S+", "", text).strip()          # no links in free text
    return text[:limit]


def _date(value: str) -> dt.date | None:
    value = (value or "").strip()
    for fmt in ("%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _split(value: str) -> list[str]:
    return [p.strip() for p in re.split(r"[,;\n]", value or "") if p.strip()]


def parse(csv_text: str, tracks: list[str], today: dt.date | None = None) -> list[dict]:
    """Rows of the published tab -> clean offers for the site (newest first, one per person and company)."""
    today = today or dt.date.today()
    known_tracks = {t.lower(): t for t in tracks}
    rows = list(csv.reader(io.StringIO(csv_text)))
    if len(rows) < 2:
        return []
    out, seen = [], set()
    for r in rows[1:]:
        r = (r + [""] * 10)[:10]
        when, name, company, title, linkedin, areas, levels, place, job, note = r
        day = _date(when)
        linkedin = linkedin.strip()
        if not LINKEDIN.match(linkedin) or not company.strip() or not name.strip():
            continue
        if day and (today - day).days > MAX_AGE_DAYS:
            continue
        if BLOCK.search(note):                    # the note is the only free text shown to seekers
            log.warning("referral from %s dropped: looks like a paid or data-fishing offer", company)
            continue
        job = job.strip()
        if job and not re.match(r"^https://[^\s]+$", job):
            job = ""
        lv = []
        for part in _split(levels):
            lv += LEVELS.get(part.lower(), [])
        tr = [known_tracks[a.lower()] for a in _split(areas) if a.lower() in known_tracks]
        key = (company_key(company), linkedin.lower().rstrip("/").split("?")[0])
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "id": hashlib.sha1("|".join(key).encode()).hexdigest()[:10],
            "n": _clean(name, 60), "c": _clean(company, 80), "ck": key[0], "t": _clean(title, 80),
            "li": linkedin.split("?")[0], "tr": tr, "lv": sorted(set(lv)), "loc": _clean(place, 60),
            "job": job[:400], "note": _clean(note, 220), "d": day.isoformat() if day else "",
        })
    out.sort(key=lambda o: o["d"], reverse=True)
    return out[:MAX_OFFERS]


def fetch(url: str, session=requests) -> str:
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def offers_from_env(tracks: list[str], today: dt.date | None = None, session=requests) -> list[dict]:
    """The approved offers, or [] when REFERRALS_CSV_URL is not set or anything goes wrong."""
    url = os.environ.get("REFERRALS_CSV_URL", "").strip()
    if not url:
        return []
    try:
        offers = parse(fetch(url, session), tracks, today)
        log.info("referrals: %s approved offers", len(offers))
        return offers
    except Exception as exc:  # noqa: BLE001 - referrals never break publishing
        log.warning("referrals not read: %s", exc)
        return []
