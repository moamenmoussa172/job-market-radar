"""Daily Telegram posts: the new tech jobs of the day, per channel (e.g. Egypt, the Gulf, Remote).

Configuration (.env):
    TELEGRAM_BOT_TOKEN   token from @BotFather; the bot must be an admin of each channel
    TELEGRAM_CHANNELS    one channel per entry, ";"-separated:  <chat>=<places>
                         chat   = @public_channel_name or a numeric chat id (-100...)
                         places = "|"-separated countries, or Remote (jobs open worldwide)
                         e.g.  @radarak_egypt=Egypt;@radarak_gulf=Saudi Arabia|United Arab Emirates|Qatar;@radarak_remote=Remote
    TELEGRAM_MAX_JOBS    most jobs per channel per day (default 40)

A job counts for a country when it is an office/hybrid job there, or a remote job open to that
country or its region (not "anywhere in the world" - that is the Remote channel). Each job is
posted to a channel once (raw.telegram_posts). Only jobs first seen in the last 2 days are posted,
so a new channel starts with today's jobs instead of the whole backlog. Listings from sources that
ask not to be re-posted (Remotive, Himalayas) are never posted, as on the website.
"""
from __future__ import annotations

import datetime as dt
import html
import logging
import os
import re
import time
from dataclasses import dataclass
from urllib.parse import quote

import requests

from jobradar.site_export import PUBLIC_LIST_EXCLUDED, SOURCE_CREDITS

log = logging.getLogger(__name__)

API = "https://api.telegram.org/bot{token}/{method}"
MAX_MESSAGE = 4000          # Telegram's limit is 4096 characters
NEW_DAYS = 2
TRACK_EMOJI = {
    "Data & Analytics": "🟣", "AI & Machine Learning": "🧠", "Software Engineering": "🔵", "Mobile Development": "📱",
    "QA & Testing": "🧪", "UI/UX Design": "🎨", "DevOps & Cloud": "☁️", "Security": "🔐", "ERP & CRM": "🧾",
    "Networks & Telecom": "📡", "Product & Delivery": "🧭", "IT & Support": "🛠", "Embedded & Chip Design": "🔌", "Clients & Projects": "🤝",
}
FLAGS = {
    "Egypt": "🇪🇬", "Saudi Arabia": "🇸🇦", "United Arab Emirates": "🇦🇪", "Qatar": "🇶🇦", "Kuwait": "🇰🇼",
    "Bahrain": "🇧🇭", "Oman": "🇴🇲", "Jordan": "🇯🇴", "Palestine": "🇵🇸", "Morocco": "🇲🇦", "Germany": "🇩🇪", "United Kingdom": "🇬🇧",
    "Netherlands": "🇳🇱", "France": "🇫🇷", "Spain": "🇪🇸", "Ireland": "🇮🇪", "Poland": "🇵🇱", "Remote": "🌍",
    "Algeria": "🇩🇿",
    "Iraq": "🇮🇶",
    "Libya": "🇱🇾",
    "Sudan": "🇸🇩",
    "Syria": "🇸🇾",
    "Yemen": "🇾🇪",
    "Mauritania": "🇲🇷",
    "Lebanon": "🇱🇧",
    "Tunisia": "🇹🇳",
    "Turkey": "🇹🇷",
    "Nigeria": "🇳🇬",
    "Kenya": "🇰🇪",
    "Ethiopia": "🇪🇹",
    "Bangladesh": "🇧🇩",
    "Pakistan": "🇵🇰",
    "India": "🇮🇳",
    "Kazakhstan": "🇰🇿",
    "Georgia": "🇬🇪",
    "Armenia": "🇦🇲",
    "Azerbaijan": "🇦🇿",
    "Albania": "🇦🇱",
    "Slovakia": "🇸🇰",
    "United States": "🇺🇸",
    "Canada": "🇨🇦",
}
AR_PLACES = {
    "Egypt": "مصر", "Saudi Arabia": "السعودية", "United Arab Emirates": "الإمارات", "Qatar": "قطر",
    "Kuwait": "الكويت", "Bahrain": "البحرين", "Oman": "عُمان", "Jordan": "الأردن", "Palestine": "فلسطين", "Morocco": "المغرب",
    "Germany": "ألمانيا", "United Kingdom": "بريطانيا", "Netherlands": "هولندا", "France": "فرنسا",
    "Spain": "إسبانيا", "Ireland": "أيرلندا", "Poland": "بولندا", "Remote": "ريموت",
    "Algeria": "الجزائر",
    "Iraq": "العراق",
    "Libya": "ليبيا",
    "Sudan": "السودان",
    "Syria": "سوريا",
    "Yemen": "اليمن",
    "Mauritania": "موريتانيا",
    "Lebanon": "لبنان",
    "Tunisia": "تونس",
}
AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

DDL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE IF NOT EXISTS raw.telegram_posts (
    chat       text        NOT NULL,
    job_id     text        NOT NULL,
    posted_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (chat, job_id)
);
"""

JOBS_SQL = """
with eligible as (
    select f.*
    from marts.fct_job_postings f
    where f.is_active
      and f.job_url is not null
      and coalesce(f.track, '') <> 'Not tech'
      and not f.nationals_only
      and f.primary_source <> all(%(excluded)s)
      and f.first_seen_date >= current_date - %(new_days)s
      and not exists (select 1 from raw.telegram_posts t where t.chat = %(chat)s and t.job_id = f.job_id)
      and (
            (%(remote)s and f.work_mode = 'Remote' and f.remote_scope = 'Worldwide')
         or (not %(remote)s and exists (
                select 1 from marts.bridge_job_regions r
                where r.job_id = f.job_id
                  and (   (r.country = any(%(countries)s) and f.work_mode <> 'Remote')
                       or (f.work_mode = 'Remote' and r.country = any(%(countries)s))
                       or (f.work_mode = 'Remote' and r.country is null and r.region <> 'Worldwide'
                           and r.region in (select g.region from seeds.geo_patterns g
                                            where g.country = any(%(countries)s))))))
      )
),
-- the same title at the same company in several cities is one post
one_per_title as (
    select distinct on (lower(job_title), lower(coalesce(company_name, ''))) *
    from eligible
    order by lower(job_title), lower(coalesce(company_name, '')), first_seen_date desc, job_id
)
select job_id, job_title, company_name, track, work_mode, location_text, job_url,
       case when has_comparable_salary then round(salary_annual_min_usd / 1000.0) end,
       case when has_comparable_salary then round(salary_annual_max_usd / 1000.0) end,
       offers_visa_or_relocation, arabic_required, seniority, primary_source
from one_per_title
order by first_seen_date desc,
         (has_comparable_salary)::int desc,
         job_id
limit %(limit)s
"""


@dataclass
class Channel:
    chat: str
    places: list[str]

    @property
    def remote(self) -> bool:
        return self.places == ["Remote"]

    @property
    def label(self) -> str:
        if len(self.places) > 3:
            return ", ".join(self.places[:3]) + " +"
        return ", ".join(self.places)

    @property
    def label_ar(self) -> str:
        return "، ".join(AR_PLACES.get(p, p) for p in self.places[:3]) + (" +" if len(self.places) > 3 else "")

    @property
    def flags(self) -> str:
        return "".join(FLAGS.get(p, "") for p in self.places[:4]) or "📍"


def parse_channels(spec: str | None) -> list[Channel]:
    channels = []
    for entry in (spec or "").split(";"):
        if "=" not in entry:
            continue
        chat, places = entry.split("=", 1)
        places_list = [p.strip() for p in places.split("|") if p.strip()]
        if chat.strip() and places_list:
            channels.append(Channel(chat.strip(), places_list))
    return channels


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()


def select_jobs(conn, channel: Channel, limit: int) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(JOBS_SQL, {"excluded": list(PUBLIC_LIST_EXCLUDED), "new_days": NEW_DAYS, "chat": channel.chat,
                               "remote": channel.remote, "countries": channel.places, "limit": limit})
        return cur.fetchall()


def site_url() -> str:
    explicit = os.environ.get("SITE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/") + "/"
    domain = os.environ.get("SITE_DOMAIN", "").strip().lower()
    if domain:
        return "https://" + re.sub(r"^https?://", "", domain).split("/")[0] + "/"
    repo = os.environ.get("SITE_REPO", "").strip()
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner.lower()}.github.io/{name}/"
    return ""


def _job_line(job: tuple) -> str:
    (_, title, company, _track, work_mode, location, url, sal_min, sal_max, visa, arabic, _sen, source) = job
    e = html.escape
    where = "Remote" if work_mode == "Remote" else (location or "")
    where = where if len(where) <= 40 else where[:39] + "…"
    bits = [f'• <a href="{e(url, quote=True)}">{e(title)}</a>']
    meta = [e(company or ""), e(where), "" if work_mode in ("Remote", "Onsite", None) else e(work_mode)]
    line = bits[0] + " — " + " · ".join(m for m in meta if m)
    if sal_min is not None:
        line += f" · 💰 ${int(sal_min)}k" + (f"–{int(sal_max)}k" if sal_max and sal_max != sal_min else "")
    if visa:
        line += " · 🛂 visa"
    if arabic:
        line += " · 🗣 Arabic"
    if source in SOURCE_CREDITS:
        line += f" <i>({e(SOURCE_CREDITS[source])})</i>"
    return line


def format_messages(channel: Channel, jobs: list[tuple], url: str, today: dt.date | None = None) -> list[str]:
    """One digest, split into Telegram-sized messages. Jobs grouped by track."""
    if not jobs:
        return []
    today = today or dt.date.today()
    n = len(jobs)
    head = (f"{channel.flags} <b>{n} new tech job{'s' if n != 1 else ''} · {html.escape(channel.label)}</b>"
            f" · {today.day} {today:%b}\n"
            f"{channel.flags} <b>{str(n).translate(AR_DIGITS)} وظيفة تك جديدة · {html.escape(channel.label_ar)}</b>")
    blocks: list[str] = []
    by_track: dict[str, list[tuple]] = {}
    for job in jobs:
        by_track.setdefault(job[3] or "Other", []).append(job)
    for track in sorted(by_track, key=lambda t: (-len(by_track[t]), t)):
        lines = [f"\n\n{TRACK_EMOJI.get(track, '•')} <b>{html.escape(track)}</b> ({len(by_track[track])})"]
        lines += [_job_line(j) for j in by_track[track]]
        blocks.append("\n".join(lines))
    place_hash = "" if channel.remote or len(channel.places) != 1 else f"#country={quote(channel.places[0])}"
    foot = ("\n\n🔎 " + (f'<a href="{html.escape(url + place_hash, quote=True)}">More jobs, filters and your CV match on Radarak</a>'
                         if url else "Radarak") + " · مجاني بالعربي والإنجليزي")
    messages, current = [], head
    for block in blocks:
        if len(current) + len(block) + len(foot) > MAX_MESSAGE:
            messages.append(current)
            current = ""
        while len(block) > MAX_MESSAGE:  # one very long track: cut between lines
            cut = block.rfind("\n", 0, MAX_MESSAGE)
            messages.append(block[:cut])
            block = block[cut:]
        current += block
    messages.append(current + foot)
    return [m.strip() for m in messages if m.strip()]


def send_message(token: str, chat: str, text: str, retries: int = 3) -> None:
    for _ in range(retries):
        resp = requests.post(API.format(token=token, method="sendMessage"), timeout=30, json={
            "chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True})
        if resp.status_code == 429:  # flood control: Telegram says how long to wait
            time.sleep(int((resp.json().get("parameters") or {}).get("retry_after", 5)) + 1)
            continue
        if resp.status_code != 200:
            raise RuntimeError(f"Telegram {chat}: HTTP {resp.status_code} {resp.text[:200]}")
        return
    raise RuntimeError(f"Telegram {chat}: still rate-limited")


def record_posted(conn, chat: str, job_ids: list[str]) -> None:
    with conn.cursor() as cur:
        cur.executemany("insert into raw.telegram_posts (chat, job_id) values (%s, %s) on conflict do nothing",
                        [(chat, j) for j in job_ids])
    conn.commit()


def todays_insight(conn) -> dict | None:
    """The site's insight of the day (same data as the website), or None if it can't be computed."""
    try:
        import json
        from jobradar import insights, site_export
        data = site_export.export_site_data(conn)
        items = insights.all_insights(site_export.all_jobs(data), json.loads(data["data/meta.json"]))["items"]
        return items[0] if items else None
    except Exception as exc:  # noqa: BLE001 - the job posts go out anyway
        conn.rollback()
        log.warning("telegram: no insight today (%s)", exc)
        return None


def post_insight(conn, token: str, chat: str, insight: dict, url: str, today: dt.date | None = None) -> bool:
    """Send the insight of the day to a channel, once per day (kept in raw.telegram_posts as insight:<date>)."""
    from jobradar.insights import telegram_text
    key = f"insight:{(today or dt.date.today()).isoformat()}"
    with conn.cursor() as cur:
        cur.execute("select 1 from raw.telegram_posts where chat = %s and job_id = %s", (chat, key))
        if cur.fetchone():
            return False
    send_message(token, chat, telegram_text(insight, url))
    record_posted(conn, chat, [key])
    time.sleep(1.5)
    return True


def post_from_env(conn) -> dict[str, int]:
    """Post today's new jobs to every configured channel. -> {chat: jobs posted}. Never raises for one channel."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    channels = parse_channels(os.environ.get("TELEGRAM_CHANNELS"))
    if not token or not channels:
        log.info("TELEGRAM_BOT_TOKEN / TELEGRAM_CHANNELS not set - nothing posted to Telegram")
        return {}
    limit = int(os.environ.get("TELEGRAM_MAX_JOBS", "40"))
    ensure_schema(conn)
    url, result = site_url(), {}
    insight = todays_insight(conn)
    for channel in channels:
        try:
            if insight:
                post_insight(conn, token, channel.chat, insight, url)
            jobs = select_jobs(conn, channel, limit)
            for text in format_messages(channel, jobs, url):
                send_message(token, channel.chat, text)
                time.sleep(1.5)
            record_posted(conn, channel.chat, [j[0] for j in jobs])
            result[channel.chat] = len(jobs)
            log.info("telegram %s: %s new jobs posted", channel.chat, len(jobs))
        except Exception as exc:  # noqa: BLE001 - one channel failing must not stop the others
            conn.rollback()
            log.warning("telegram %s: not posted (%s)", channel.chat, exc)
            result[channel.chat] = -1
    return result
