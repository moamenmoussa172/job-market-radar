"""Ways to hear about new jobs without coming back to the site: Telegram channels and RSS feeds.

* telegram_links(): the public Telegram channels from TELEGRAM_CHANNELS (entries whose chat is
  "@name"; numeric chat ids are private and are never shown). Put in meta.json for the app and used
  on the search pages: "Get new Egypt jobs on Telegram".
* rss_files(): one RSS feed per country / track page (feeds/egypt.xml, feeds/egypt/data-and-analytics.xml,
  feeds/remote.xml) with its 40 newest jobs. Feed readers, Telegram RSS bots and Slack/Discord can
  follow them.
"""
from __future__ import annotations

import datetime as dt
import email.utils
import os

from jobradar.seo_pages import REMOTE, _e, place_name

FEED_ITEMS = 40
FEED_DIR = "feeds"

TXT = {
    "en": {"tg": "New {p} jobs every morning on Telegram", "tg_any": "New jobs every morning on Telegram",
           "join": "Join on Telegram", "rss": "RSS feed", "remote": "remote",
           "h": "Get new jobs without checking back"},
    "ar": {"tg": "وظايف {p} الجديدة كل صبح على تيليجرام", "tg_any": "الوظايف الجديدة كل صبح على تيليجرام",
           "join": "اشترك على تيليجرام", "rss": "RSS", "remote": "الريموت",
           "h": "خلّي الوظايف الجديدة توصلك"},
}


def telegram_links(spec: str | None = None) -> list[dict]:
    """[{"u": "https://t.me/radarak_egypt", "pl": ["Egypt"]}, ...] for the public channels."""
    from jobradar.telegram import parse_channels
    if spec is None:     # from .env: only when the bot can post, so the site never links to an empty channel
        spec = os.environ.get("TELEGRAM_CHANNELS", "") if os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() else ""
    out = []
    for ch in parse_channels(spec):
        name = ch.chat.lstrip("@")
        if ch.chat.startswith("@") and name.replace("_", "").isalnum():
            out.append({"u": f"https://t.me/{name}", "pl": ch.places})
    return out


def channel_for(place: str | None, meta: dict) -> dict | None:
    for ch in meta.get("telegram") or []:
        if place and place in ch["pl"]:
            return ch
    return None


def feed_path(place: str, x_slug: str | None = None) -> str:
    from jobradar.seo_pages import slug
    base = "remote" if place == REMOTE else slug(place)
    return f"{FEED_DIR}/{base}/{x_slug}.xml" if x_slug else f"{FEED_DIR}/{base}.xml"


def alerts_block(place: str | None, meta: dict, rel: str, lang: str, x_slug: str | None = None) -> str:
    """The "Get new jobs" row on a page: Telegram button for the place's channel, its RSS feed, email."""
    t = TXT[lang]
    ch = channel_for(place, meta)
    feeds = meta.get("feeds") or {}
    feed = feeds.get(f"{place}|{x_slug}" if x_slug else place or "")
    if not ch and not feed:
        return ""
    label = (t["remote"] if place == REMOTE else place_name(place, lang)) if place else ""
    bits = []
    if ch:
        bits.append(f'<a class="primary tg" href="{_e(ch["u"])}" target="_blank" rel="noopener">{_e(t["join"])}</a>')
    if feed:
        bits.append(f'<a class="rss" href="{_e(rel + feed)}" type="application/rss+xml">{_e(t["rss"])}</a>')
    text = t["tg"].format(p=label) if ch and label else t["tg_any"] if ch else t["h"]
    return f'<div class="alerts" data-alerts><p>📣 {_e(text)}</p>{"".join(bits)}</div>'


def _rfc822(day: str) -> str:
    try:
        d = dt.date.fromisoformat(day)
    except (TypeError, ValueError):
        return ""
    return email.utils.format_datetime(dt.datetime(d.year, d.month, d.day, 6, 0, tzinfo=dt.timezone.utc))


def rss_feed(title: str, link: str, self_url: str, jobs: list[dict], base: str, skills: list[str],
             today: dt.date) -> bytes:
    items = []
    for j in sorted(jobs, key=lambda j: (j.get("fs") or j.get("p") or "", j["id"]), reverse=True)[:FEED_ITEMS]:
        url = base + j["pg"] if j.get("pg") else base + "#job=" + j["id"]
        where = "Remote" if j.get("w") == REMOTE else (j.get("l") or ", ".join(j.get("co") or []))
        bits = [j.get("c") or "", where, j.get("s") if j.get("s") not in (None, "Not stated") else ""]
        if j.get("$"):
            lo, hi = j["$"]
            bits.append(f"${lo}k" if lo == hi else f"${lo}k–${hi}k")
        sk = ", ".join(skills[i] for i in (j.get("k") or [])[:6] if i < len(skills))
        desc = " · ".join(b for b in bits if b) + (f". Skills: {sk}" if sk else "")
        if j.get("by"):
            desc += f" ({j['by']})"
        items.append(f"<item><title>{_e(j.get('t'))} — {_e(j.get('c') or '')}</title><link>{_e(url)}</link>"
                     f'<guid isPermaLink="false">radarak-{_e(j["id"])}</guid><pubDate>{_rfc822(j.get("fs") or j.get("p"))}</pubDate>'
                     f"<description>{_e(desc)}</description></item>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
            f"<title>{_e(title)}</title><link>{_e(link)}</link>"
            f"<description>{_e(title)}, from Radarak (radarak.online). Updated every morning.</description>"
            f'<atom:link href="{_e(self_url)}" rel="self" type="application/rss+xml"/>'
            f"<lastBuildDate>{_rfc822(today.isoformat())}</lastBuildDate>"
            + "".join(items) + "</channel></rss>\n").encode()


def rss_files(pages: list, base: str, today: dt.date, skills: list[str]) -> tuple[dict[str, bytes], dict[str, str]]:
    """Feeds for the country and track pages. Returns (files, {"Egypt": path, "Egypt|data-and-analytics": path})."""
    from jobradar.seo_pages import _unique
    files, index = {}, {}
    for p in pages:
        if p.kind not in ("country", "track"):
            continue
        x = p.x_slug if p.kind == "track" else None
        path = feed_path(p.place, x)
        where = "remote" if p.place == REMOTE else f"in {p.place}"
        title = (f"{p.label} jobs {where}" if p.kind == "track" else
                 "Remote tech jobs" if p.place == REMOTE else f"Tech jobs in {p.place}")
        files[path] = rss_feed(title, base + p.url_path("en"), base + path, _unique(p.jobs), base, skills, today)
        index[f"{p.place}|{x}" if x else p.place] = path
    return files, index
