"""Public website: export the warehouse to small JSON files and publish them,
together with the static site in /site, to a GitHub Pages branch.

* export_site_data(conn) -> {"data/jobs.json": bytes, "data/meta.json": bytes}
  Only active jobs from sources whose terms allow showing their listings on another
  site are listed (see PUBLIC_LIST_EXCLUDED); every job keeps a link to its source.
* publish(files, repo, branch, token) pushes everything as ONE commit through the
  GitHub Git Data API (no git binary, no SSH). The branch is replaced each day by a
  commit without parents, so its history doesn't grow with daily data.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import logging
import os
import re
from pathlib import Path

import requests

log = logging.getLogger(__name__)

# Remotive and Himalayas ask not to re-post their listings on other job sites.
# Their jobs still count in the warehouse/dashboard, but are not listed publicly.
PUBLIC_LIST_EXCLUDED = ("remotive", "himalayas")
MAX_PUBLIC_JOBS = int(os.environ.get("SITE_MAX_JOBS", "15000"))
STALE_POSTING_DAYS = 45  # posted more than this long before we first saw it = long-open listing
SITE_DIR = Path(os.environ.get("SITE_DIR") or Path(__file__).resolve().parents[2] / "site")
GITHUB_API = "https://api.github.com"
SOURCE_CREDITS = {
    "adzuna": "Jobs by Adzuna", "jooble": "via Jooble", "jsearch": "via Google for Jobs (JSearch)",
    "jobicy": "via Jobicy", "arbeitnow": "via Arbeitnow", "bundesagentur": "via Bundesagentur für Arbeit",
}

JOBS_SQL = """
with jobs as (
    select f.*
    from marts.fct_job_postings f
    where f.is_active
      and f.job_url is not null
      and f.primary_source <> all(%(excluded)s)
    order by coalesce(f.posted_at::date, f.first_seen_date) desc, f.job_id
    limit %(limit)s
),
geo as (
    select r.job_id,
           array_remove(array_agg(distinct r.country), null)                               as countries,
           array_remove(array_agg(distinct case when r.country is null then r.region end), null) as regions
    from marts.bridge_job_regions r join jobs using (job_id)
    group by 1
),
sk as (
    select b.job_id, array_agg(distinct b.skill order by b.skill) as skills
    from marts.bridge_job_skills b join jobs using (job_id)
    group by 1
)
select j.job_id, j.job_title, j.company_name, j.track, j.role_family, j.seniority, j.work_mode,
       j.industry, left(coalesce(j.remote_eligibility_text, j.location_text), 90) as loc,
       coalesce(g.countries, '{}'), coalesce(g.regions, '{}'), j.remote_scope = 'Worldwide' as worldwide,
       case when j.has_comparable_salary then round(j.salary_annual_min_usd / 1000.0) end as sal_min_k,
       case when j.has_comparable_salary then round(j.salary_annual_max_usd / 1000.0) end as sal_max_k,
       -- long-open listings ("evergreen" roles posted years ago) show when we first saw them
       case when j.posted_at::date < j.first_seen_date - %(stale_days)s then j.first_seen_date
            else coalesce(j.posted_at::date, j.first_seen_date) end as posted,
       j.posted_at::date < j.first_seen_date - %(stale_days)s as long_open,
       j.job_url, coalesce(s.skills, '{}'),
       j.offers_visa_or_relocation, j.nationals_only, j.arabic_required, j.primary_source
from jobs j
left join geo g using (job_id)
left join sk s using (job_id)
order by posted desc, j.job_id
"""


def pg_regex_to_js(pattern: str) -> str:
    """Postgres ARE word boundaries -> JavaScript: \\m = start of a word, \\M = end of a word."""
    return pattern.replace("\\m", "(?<!\\w)(?=\\w)").replace("\\M", "(?<=\\w)(?!\\w)")


def _rows(conn, sql: str, params: dict | None = None) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
        return cur.fetchall()


def export_site_data(conn, generated_at: dt.datetime | None = None) -> dict[str, bytes]:
    generated_at = generated_at or dt.datetime.now(dt.timezone.utc)
    rows = _rows(conn, JOBS_SQL, {"excluded": list(PUBLIC_LIST_EXCLUDED), "limit": MAX_PUBLIC_JOBS,
                                  "stale_days": STALE_POSTING_DAYS})

    skills = sorted({s for r in rows for s in r[17]}, key=str.lower)
    skill_idx = {s: i for i, s in enumerate(skills)}
    jobs = []
    for (job_id, title, company, track, role, seniority, work_mode, industry, loc, countries, regions,
         worldwide, sal_min, sal_max, posted, long_open, url, job_skills, visa, nationals, arabic, source) in rows:
        flags = (1 if visa else 0) | (2 if nationals else 0) | (4 if arabic else 0) | (8 if long_open else 0)
        job = {"id": job_id[:12], "t": title, "c": company, "tr": track, "r": role, "s": seniority,
               "w": work_mode, "i": industry, "l": loc, "co": list(countries), "rg": list(regions),
               "p": posted.isoformat(), "u": url, "k": [skill_idx[s] for s in job_skills]}
        if worldwide:
            job["ww"] = 1
        if sal_min is not None:
            job["$"] = [int(sal_min), int(sal_max if sal_max is not None else sal_min)]
        if flags:
            job["f"] = flags
        if source in SOURCE_CREDITS:
            job["by"] = SOURCE_CREDITS[source]
        jobs.append(job)

    countries = _rows(conn, """
        select country, min(region) from seeds.geo_patterns
        where country is not null and region is not null group by 1 order by 1""")
    tracks = _rows(conn, """
        select track, array_agg(role_family order by role_family) from seeds.role_tracks
        where track <> 'Not tech' group by track order by min(track_order), track""")
    total_active = _rows(conn, "select count(*) from marts.fct_job_postings where is_active")[0][0]
    patterns = dict(_rows(conn, "select skill, pattern from seeds.skills"))

    def distinct(key: str, order: list[str] | None = None) -> list[str]:
        values = {j[key] for j in jobs if j.get(key)}
        if order:
            return [v for v in order if v in values] + sorted(values - set(order))
        return sorted(values)

    meta = {
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "total_active_jobs": total_active,
        "listed_jobs": len(jobs),
        "skills": skills,
        "countries": [{"name": c, "region": r} for c, r in countries],
        "tracks": [{"name": t, "roles": list(roles)} for t, roles in tracks],
        "seniorities": distinct("s", ["Intern / Student", "Junior", "Mid", "Senior", "Lead / Principal",
                                      "Head / Director", "Not stated"]),
        "work_modes": distinct("w", ["Remote", "Hybrid", "Onsite"]),
        "industries": distinct("i"),
        "credits": sorted(set(SOURCE_CREDITS.values())),
        # same rules the pipeline uses to find skills in job descriptions, for reading a CV in the browser
        # (case-insensitive JavaScript regexes, aligned with "skills")
        "skill_patterns": [pg_regex_to_js(patterns.get(s, "")) for s in skills],
    }
    dump = lambda obj: json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")  # noqa: E731
    log.info("site export: %s of %s active jobs listed, %s skills", len(jobs), total_active, len(skills))
    return {"data/jobs.json": dump(jobs), "data/meta.json": dump(meta),
            "data/trends.json": dump(export_trends(conn, generated_at))}


TREND_WEEKS = 12
MIN_SCOPE_JOBS = 20      # a place needs this many new jobs over the period to get its own trend
TOP_SKILL_MOVES = 12


def export_trends(conn, generated_at: dt.datetime | None = None) -> dict:
    """Hiring trend, skill momentum and time-to-close, from the trend marts.
    weekly[scope][track] = new jobs per week aligned with "weeks" (the last one may be partial)."""
    generated_at = generated_at or dt.datetime.now(dt.timezone.utc)
    this_week = generated_at.date() - dt.timedelta(days=generated_at.weekday())
    weeks = [this_week - dt.timedelta(weeks=i) for i in range(TREND_WEEKS - 1, -1, -1)]
    pos = {w: i for i, w in enumerate(weeks)}
    weekly: dict[str, dict[str, list[int]]] = {}
    for week, scope, track, n in _rows(conn, """
            select week_start, scope, track, new_jobs from marts.mart_weekly_new_jobs
            where week_start >= %(first)s""", {"first": weeks[0]}):
        if week in pos and track:
            weekly.setdefault(scope, {}).setdefault(track, [0] * TREND_WEEKS)[pos[week]] += int(n)
    weekly = {sc: tr for sc, tr in weekly.items()
              if sc == "All" or sum(sum(v) for v in tr.values()) >= MIN_SCOPE_JOBS}

    skills: dict[str, dict[str, list]] = {}
    window_days = None
    for scope, skill, window, before, now, change, jobs_now in _rows(conn, """
            select scope, skill, window_days, share_before_pct, share_now_pct, change_pts, jobs_now
            from marts.mart_skill_trends"""):
        window_days = int(window)
        skills.setdefault(scope, []).append([skill, float(before), float(now), float(change), int(jobs_now)])
    skill_moves = {}
    for scope, rows in skills.items():
        rows.sort(key=lambda r: r[3], reverse=True)
        skill_moves[scope] = {"rising": [r for r in rows if r[3] > 0][:TOP_SKILL_MOVES],
                              "falling": [r for r in reversed(rows) if r[3] < 0][:TOP_SKILL_MOVES],
                              "top": sorted(rows, key=lambda r: r[2], reverse=True)[:TOP_SKILL_MOVES]}
    days_open = [[role, track, int(med), int(p25), int(p75), int(n)] for role, track, med, p25, p75, n in _rows(conn, """
            select role_family, track, median_days_open, p25_days_open, p75_days_open, closed_jobs
            from marts.mart_time_to_close order by closed_jobs desc limit 25""")]
    history_days = _rows(conn, "select coalesce(max(first_seen_date) - min(first_seen_date), 0) "
                               "from marts.fct_job_postings")[0][0]
    return {"generated_at": generated_at.isoformat(timespec="seconds"), "history_days": int(history_days),
            "weeks": [w.isoformat() for w in weeks], "weekly": weekly,
            "window_days": window_days, "skills": skill_moves, "days_open": days_open}


def analytics_snippet(code: str | None) -> str:
    """GoatCounter tag (anonymous, cookie-free visit counts) for the site code from goatcounter.com."""
    code = (code or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,49}", code):
        return ""
    return (f'<script data-goatcounter="https://{code}.goatcounter.com/count" '
            f'async src="https://gc.zgo.at/count.js"></script>')


def site_files(site_dir: Path = SITE_DIR, analytics_code: str | None = None) -> dict[str, bytes]:
    """The static website (HTML/CSS/JS) that goes next to the data files.
    With a GoatCounter code (env GOATCOUNTER_CODE) the counting tag is added to every page."""
    if analytics_code is None:
        analytics_code = os.environ.get("GOATCOUNTER_CODE", "")
    files = {}
    for path in sorted(site_dir.rglob("*")):
        if path.is_file() and not path.name.startswith(".") and "data" not in path.relative_to(site_dir).parts:
            files[path.relative_to(site_dir).as_posix()] = path.read_bytes()
    tag = analytics_snippet(analytics_code)
    if tag:
        for name in [n for n in files if n.endswith(".html")]:
            html = files[name].decode("utf-8")
            files[name] = html.replace("</body>", f"  {tag}\n</body>", 1).encode("utf-8")
    files[".nojekyll"] = b""  # serve files as-is (no Jekyll processing)
    return files


# --------------------------------------------------------------------------- #
# Publishing (GitHub Git Data API)
# --------------------------------------------------------------------------- #
def _gh(method: str, path: str, token: str, body: dict | None = None, ok=(200, 201)) -> dict | None:
    resp = requests.request(
        method, f"{GITHUB_API}{path}", json=body, timeout=120,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "job-market-radar"},
    )
    if resp.status_code == 404 and method == "GET":
        return None
    if resp.status_code not in ok:
        raise RuntimeError(f"GitHub {method} {path} -> HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json() if resp.content else {}


def publish(files: dict[str, bytes], repo: str, branch: str, token: str,
            message: str = "Daily site update") -> str:
    """Replace the branch content with `files` in a single commit. Returns the commit sha."""
    tree = []
    for path, content in sorted(files.items()):
        blob = _gh("POST", f"/repos/{repo}/git/blobs", token,
                   {"content": base64.b64encode(content).decode("ascii"), "encoding": "base64"})
        tree.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    new_tree = _gh("POST", f"/repos/{repo}/git/trees", token, {"tree": tree})
    commit = _gh("POST", f"/repos/{repo}/git/commits", token,
                 {"message": message, "tree": new_tree["sha"], "parents": []})
    ref = f"heads/{branch}"
    if _gh("GET", f"/repos/{repo}/git/ref/{ref}", token) is None:
        _gh("POST", f"/repos/{repo}/git/refs", token, {"ref": f"refs/{ref}", "sha": commit["sha"]})
    else:
        _gh("PATCH", f"/repos/{repo}/git/refs/{ref}", token, {"sha": commit["sha"], "force": True})
    log.info("published %s files to %s@%s (%s)", len(files), repo, branch, commit["sha"][:7])
    return commit["sha"]


def publish_from_env(conn) -> str | None:
    """Export + publish using SITE_GITHUB_TOKEN / SITE_REPO / SITE_BRANCH. None if not configured."""
    token = os.environ.get("SITE_GITHUB_TOKEN", "").strip()
    repo = os.environ.get("SITE_REPO", "").strip()
    branch = os.environ.get("SITE_BRANCH", "gh-pages").strip() or "gh-pages"
    if not token or not repo:
        log.warning("SITE_GITHUB_TOKEN / SITE_REPO not set - website not published")
        return None
    files = {**site_files(), **export_site_data(conn)}
    return publish(files, repo, branch, token,
                   message=f"Site update {dt.date.today().isoformat()}")
