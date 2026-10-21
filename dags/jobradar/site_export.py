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
import time
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
       j.offers_visa_or_relocation, j.nationals_only, j.arabic_required, j.primary_source,
       j.first_seen_date
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
         worldwide, sal_min, sal_max, posted, long_open, url, job_skills, visa, nationals, arabic, source,
         first_seen) in rows:
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
        # the day Radarak first saw the job, for "new since your last visit" (only when it differs from "p")
        if first_seen and first_seen.isoformat() != job["p"]:
            job["fs"] = first_seen.isoformat()
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


GITHUB_PAGES_URL = "https://moamenmoussa172.github.io/job-market-radar/"
_DOMAIN_RE = re.compile(r"(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}")


def clean_domain(value: str | None) -> str:
    """'https://www.Radarak.com/' -> 'www.radarak.com'; anything that isn't a plain host name -> ''."""
    d = (value or "").strip().lower()
    d = re.sub(r"^https?://", "", d).split("/")[0]
    return d if _DOMAIN_RE.fullmatch(d) else ""


def add_analytics(files: dict[str, bytes], analytics_code: str | None = None) -> dict[str, bytes]:
    """Add the GoatCounter tag to every HTML page in `files` (in place)."""
    if analytics_code is None:
        analytics_code = os.environ.get("GOATCOUNTER_CODE", "")
    tag = analytics_snippet(analytics_code)
    if tag:
        for name in [n for n in files if n.endswith(".html")]:
            html = files[name].decode("utf-8")
            files[name] = html.replace("</body>", f"  {tag}\n</body>", 1).encode("utf-8")
    return files


def newsletter_name(value: str | None = None) -> str:
    name = (os.environ.get("BUTTONDOWN_USERNAME", "") if value is None else value).strip().lower()
    return name if re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", name) else ""


NEWSLETTER_FORM = {
    "en": ("Radarak Weekly", "The week's new tech jobs in one short email, every Sunday.", "you@example.com", "Subscribe"),
    "ar": ("نشرة رادارك الأسبوعية", "وظايف التك الجديدة كل أسبوع في إيميل واحد قصير، كل يوم حد.", "you@example.com", "اشترك"),
}


def add_newsletter(files: dict[str, bytes], name: str | None = None) -> dict[str, bytes]:
    """With BUTTONDOWN_USERNAME set: switch on the app's signup box and put a signup form on the search pages."""
    name = newsletter_name(name)
    if not name:
        return files
    for path in [p for p in files if p.endswith(".html")]:
        html = files[path].decode("utf-8")
        html = html.replace('data-bd=""', f'data-bd="{name}"', 1)
        for lang, (title, text, ph, btn) in NEWSLETTER_FORM.items():
            html = html.replace(f"<!--newsletter:{lang}-->", (
                f'<section class="newsletter"><div><h2>{title}</h2><p>{text}</p></div>'
                f'<form action="https://buttondown.com/api/emails/embed-subscribe/{name}" method="post" target="_blank">'
                f'<input type="email" name="email" required placeholder="{ph}" aria-label="Email">'
                f'<input type="hidden" name="embed" value="1"><button class="primary" type="submit">{btn}</button></form></section>'))
        files[path] = html.encode("utf-8")
    return files


def site_base_url(domain: str | None = None) -> str:
    """The address people see: the custom domain when set, else the github.io address."""
    domain = clean_domain(os.environ.get("SITE_DOMAIN", "") if domain is None else domain)
    return f"https://{domain}/" if domain else GITHUB_PAGES_URL


def all_site_files(conn) -> dict[str, bytes]:
    """Everything that is published: the app, its data, and the pages for search engines."""
    from jobradar import seo_pages
    data = export_site_data(conn)
    seo = seo_pages.seo_files(json.loads(data["data/jobs.json"]), json.loads(data["data/meta.json"]), site_base_url())
    return {**site_files(), **data, **add_newsletter(add_analytics(seo))}


def site_files(site_dir: Path = SITE_DIR, analytics_code: str | None = None,
               domain: str | None = None) -> dict[str, bytes]:
    """The static website (HTML/CSS/JS) that goes next to the data files.
    With a GoatCounter code (env GOATCOUNTER_CODE) the counting tag is added to every page.
    With a custom domain (env SITE_DOMAIN, e.g. radarak.com) a CNAME file is published too: the branch is
    replaced on every publish, so without it GitHub Pages would drop the domain the next day."""
    if analytics_code is None:
        analytics_code = os.environ.get("GOATCOUNTER_CODE", "")
    if domain is None:
        domain = os.environ.get("SITE_DOMAIN", "")
    domain = clean_domain(domain)
    files = {}
    for path in sorted(site_dir.rglob("*")):
        if path.is_file() and not path.name.startswith(".") and "data" not in path.relative_to(site_dir).parts:
            files[path.relative_to(site_dir).as_posix()] = path.read_bytes()
    add_analytics(files, analytics_code)
    add_newsletter(files)
    if domain:
        files["CNAME"] = (domain + "\n").encode()
        for name in [n for n in files if n.endswith(".html")]:   # link previews need the address people see
            files[name] = files[name].replace(GITHUB_PAGES_URL.encode(), f"https://{domain}/".encode())
    files[".nojekyll"] = b""  # serve files as-is (no Jekyll processing)
    return files


# --------------------------------------------------------------------------- #
# Publishing (GitHub Git Data API)
# --------------------------------------------------------------------------- #
GH_RETRIES = 3          # GitHub sometimes answers 502/503/504 to heavy requests: wait and try again


def _gh(method: str, path: str, token: str, body: dict | None = None, ok=(200, 201),
        retries: int | None = None) -> dict | None:
    retries = GH_RETRIES if retries is None else retries
    for attempt in range(retries + 1):
        try:
            resp = requests.request(
                method, f"{GITHUB_API}{path}", json=body, timeout=180,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                         "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "job-market-radar"},
            )
        except (requests.ConnectionError, requests.Timeout):
            if attempt == retries:
                raise
            time.sleep(5 * (attempt + 1))
            continue
        if resp.status_code in (502, 503, 504) and attempt < retries:
            log.warning("GitHub %s %s -> HTTP %s, retrying", method, path, resp.status_code)
            time.sleep(5 * (attempt + 1))
            continue
        break
    if resp.status_code == 404 and method == "GET":
        return None
    if resp.status_code not in ok:
        raise RuntimeError(f"GitHub {method} {path} -> HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json() if resp.content else {}


TEXT_TYPES = (".html", ".css", ".js", ".json", ".xml", ".txt", ".webmanifest", ".md", ".svg")
TREE_BATCH_BYTES = 512 * 1024   # text sent inline per "create tree" request (bigger ones time out at GitHub)
TREE_BATCH_FILES = 150          # inline files per request
TREE_BATCH_ENTRIES = 800        # all files (reused ones too) per request: GitHub 502s on ~2,700 at once
INLINE_MAX_BYTES = 400 * 1024   # bigger files (data/jobs.json) are uploaded as blobs, never inline


def git_blob_sha(content: bytes) -> str:
    """The id git gives a file's content, so unchanged files are not uploaded again."""
    import hashlib
    return hashlib.sha1(b"blob %d\0" % len(content) + content).hexdigest()


def _existing_blobs(repo: str, branch: str, token: str) -> set[str]:
    try:
        tree = _gh("GET", f"/repos/{repo}/git/trees/{branch}?recursive=1", token)
    except RuntimeError:
        return set()
    return {e["sha"] for e in (tree or {}).get("tree", []) if e.get("type") == "blob"}


def _upload_blob(repo: str, token: str, content: bytes) -> str:
    return _gh("POST", f"/repos/{repo}/git/blobs", token,
               {"content": base64.b64encode(content).decode("ascii"), "encoding": "base64"})["sha"]


def _make_tree(repo: str, token: str, entries: list[dict], base: str | None) -> str:
    """Create a tree on top of `base`. If GitHub keeps failing (5xx), split the batch in half and try
    each half; a single inline file that still fails is uploaded as a blob instead."""
    body = {"tree": entries, **({"base_tree": base} if base else {})}
    try:
        return _gh("POST", f"/repos/{repo}/git/trees", token, body, retries=1)["sha"]
    except RuntimeError as exc:
        if "HTTP 5" not in str(exc) and "HTTP 422" not in str(exc):
            raise
        inline = [e for e in entries if "content" in e]
        if not inline:
            raise
        if len(entries) > 1:
            half = len(entries) // 2
            log.warning("publish: tree of %s files failed (%s), splitting", len(entries), str(exc)[:60])
            return _make_tree(repo, token, entries[half:], _make_tree(repo, token, entries[:half], base))
        e = entries[0]
        log.warning("publish: %s failed inline, uploading it as a blob", e["path"])
        sha = _upload_blob(repo, token, e["content"].encode("utf-8"))
        return _gh("POST", f"/repos/{repo}/git/trees", token,
                   {"tree": [{"path": e["path"], "mode": "100644", "type": "blob", "sha": sha}],
                    **({"base_tree": base} if base else {})})["sha"]


def publish(files: dict[str, bytes], repo: str, branch: str, token: str,
            message: str = "Daily site update") -> str:
    """Replace the branch content with `files` in a single commit. Returns the commit sha.
    Files already on the branch are reused by id; changed text files go inline in a few "create tree"
    requests (built on top of each other); only changed binary files are uploaded one by one. A daily
    publish of ~1,000 pages therefore takes a handful of API calls instead of one per file."""
    have = _existing_blobs(repo, branch, token)
    reused, inline, binary = [], [], []
    for path, content in sorted(files.items()):
        sha = git_blob_sha(content)
        if sha in have:
            reused.append({"path": path, "mode": "100644", "type": "blob", "sha": sha})
            continue
        try:
            text = content.decode("utf-8")
            is_text = path.endswith(TEXT_TYPES) or "." not in path.rsplit("/", 1)[-1] or path.endswith("CNAME")
        except UnicodeDecodeError:
            is_text = False
        if is_text and len(content) <= INLINE_MAX_BYTES:
            inline.append({"path": path, "mode": "100644", "type": "blob", "content": text})
        else:
            binary.append({"path": path, "mode": "100644", "type": "blob", "sha": _upload_blob(repo, token, content)})
    batches, cur, size, n_inline = [], [], 0, 0
    for entry in reused + binary + inline:
        text = entry.get("content")
        full = len(cur) >= TREE_BATCH_ENTRIES or (text is not None and n_inline and (
            size + len(text) > TREE_BATCH_BYTES or n_inline >= TREE_BATCH_FILES))
        if cur and full:
            batches.append(cur)
            cur, size, n_inline = [], 0, 0
        cur.append(entry)
        if text is not None:
            size += len(text)
            n_inline += 1
    batches.append(cur)
    tree_sha = None
    for i, batch in enumerate(batches, 1):
        log.info("publish: tree batch %s/%s (%s files, %s KB inline)", i, len(batches), len(batch),
                 sum(len(e.get("content", "")) for e in batch) // 1024)
        tree_sha = _make_tree(repo, token, batch, tree_sha)
    new_tree = {"sha": tree_sha}
    log.info("publish: %s files (%s unchanged, %s text, %s binary uploaded) in %s tree requests",
             len(files), len(reused), len(inline), len(binary), len(batches))
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
    files = all_site_files(conn)
    return publish(files, repo, branch, token,
                   message=f"Site update {dt.date.today().isoformat()}")
