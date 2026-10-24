"""One page per job, so the jobs can show up in Google's job search ("Google for Jobs").

Google only lists a job from a page about that one job, with JobPosting structured data and the full
job description on the page. The app (index.html) can't do that: it is one page built in the browser.

Which jobs get a page
* jobs from company career sites (Greenhouse, Lever, Workday, ...; JOB_PAGE_SOURCES). Jobs that come
  from other job boards (Adzuna, Jooble, JSearch, Remote OK, ...) don't: those are the boards' listings,
  and JSearch's are already Google's own.
* with a real description (at least MIN_DESCRIPTION_CHARS characters) and at least one country.
* at most JOB_PAGES_MAX (env), the jobs most visitors need first (remote, Middle East & Africa).

Pages are written so they only change when the job changes (no "updated today", no "3 days ago"):
the site is pushed every day and unchanged pages cost nothing. A job that closes drops out of the
export, its page disappears (404) and Google removes it, as its guidelines ask.
"""
from __future__ import annotations

import datetime as dt
import html
import logging
import os
import re
from html.parser import HTMLParser

from jobradar.seo_pages import REMOTE, T, _date, _e, _shell, slug

log = logging.getLogger(__name__)

# company career sites (the board readers in sources.ATS_FETCHERS)
JOB_PAGE_SOURCES = ("greenhouse", "lever", "ashby", "smartrecruiters", "workable", "recruitee", "personio", "breezy",
                    "teamtailor", "workday", "successfactors", "phenom", "oracle")
MIN_DESCRIPTION_CHARS = 400
MAX_DESCRIPTION_CHARS = 8000
MAX_COUNTRIES = 60          # remote jobs open to a whole region list many countries
JOB_DIR = "job"

DETAILS_SQL = """
select left(f.job_id, 12), u.description_html, f.employment_type
from marts.fct_job_postings f
join intermediate.int_postings_unioned u on u.posting_key = f.primary_posting_key
where f.is_active
  and f.primary_source = any(%(sources)s)
  and length(coalesce(f.description_text, '')) >= %(min_chars)s
  and left(f.job_id, 12) = any(%(ids)s)
"""


def max_pages() -> int:
    try:
        return max(0, int(os.environ.get("JOB_PAGES_MAX", "12000")))
    except ValueError:
        return 12000


def job_path(job: dict) -> str:
    """job/<title>-at-<company>-<id>/ : readable, and stable for as long as the job is open."""
    words = slug(f"{job.get('t') or ''} at {job.get('c') or ''}")[:70].strip("-")
    return f"{JOB_DIR}/{words + '-' if words else ''}{job['id']}/"


# --------------------------------------------------------------------------- #
# Description clean-up: keep paragraphs, lists and bold; drop everything else
# --------------------------------------------------------------------------- #
_BLOCK = {"p", "div", "section", "article", "header", "footer", "blockquote", "table", "tr", "h1", "h2", "h3", "h4",
          "h5", "h6", "pre", "dl", "dt", "dd", "hr", "main", "aside", "figure"}
_HEAD = {"h1", "h2", "h3", "h4", "h5", "h6", "dt"}
_LIST = {"ul", "ol"}
_INLINE = {"strong": "strong", "b": "strong", "em": "em", "i": "em"}
_SKIP = {"script", "style", "noscript", "iframe", "svg", "head", "title", "template", "button", "form"}


class _Clean(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.in_p = False
        self.lists = 0          # open <ul>/<ol>
        self.in_li = False
        self.inline: list[str] = []
        self.skip = 0
        self.chars = 0

    # paragraphs open lazily (on the first text) so empty <div>s leave nothing behind
    def _close_inline(self):
        while self.inline:
            self.out.append(f"</{self.inline.pop()}>")

    def _close_p(self):
        if self.in_p:
            self._close_inline()
            self.out.append("</p>")
            self.in_p = False

    def _close_li(self):
        if self.in_li:
            self._close_inline()
            self.out.append("</li>")
            self.in_li = False

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP:
            self.skip += 1
        elif self.skip:
            return
        elif tag in _LIST:
            self._close_p()
            self._close_li()
            if self.lists == 0:
                self.out.append("<ul>")
            self.lists += 1
        elif tag == "li":
            self._close_p()
            self._close_li()
            if self.lists == 0:            # a stray <li>: treat it as a one-item list
                self.out.append("<ul>")
                self.lists = 1
            self.out.append("<li>")
            self.in_li = True
        elif tag in _BLOCK:
            self._close_p()
            if tag in _HEAD:
                self._open_text()
                self.out.append("<strong>")
                self.inline.append("strong")
        elif tag == "br":
            if self.in_p or self.in_li:
                self.out.append("<br>")
        elif tag in _INLINE and _INLINE[tag] not in self.inline:
            self._open_text()
            self.out.append(f"<{_INLINE[tag]}>")
            self.inline.append(_INLINE[tag])

    def handle_endtag(self, tag):
        if tag in _SKIP:
            self.skip = max(0, self.skip - 1)
        elif self.skip:
            return
        elif tag in _LIST:
            self._close_li()
            if self.lists:
                self.lists -= 1
                if self.lists == 0:
                    self.out.append("</ul>")
        elif tag == "li":
            self._close_li()
        elif tag in _BLOCK:
            self._close_p()
        elif tag in _INLINE and _INLINE[tag] in self.inline:
            while self.inline:
                t = self.inline.pop()
                self.out.append(f"</{t}>")
                if t == _INLINE[tag]:
                    break

    def _open_text(self):
        if self.lists and not self.in_li:
            self.out.append("<li>")
            self.in_li = True
        elif not self.lists and not self.in_p:
            self.out.append("<p>")
            self.in_p = True

    def handle_data(self, data):
        if self.skip:
            return
        text = re.sub(r"\s+", " ", data)
        if not text.strip() and not (self.in_p or self.in_li):
            return
        if not (self.in_p or self.in_li):
            text = text.lstrip()
        self._open_text()
        self.out.append(html.escape(text, quote=False))
        self.chars += len(text.strip())

    def result(self) -> str:
        self._close_p()
        self._close_li()
        if self.lists:
            self.out.append("</ul>")
        s = "".join(self.out)
        s = re.sub(r"<(p|li|strong|em)>\s*</\1>", "", s)
        s = re.sub(r"<ul>\s*</ul>", "", s)
        s = re.sub(r"(<br>\s*){2,}", "<br>", s)
        return s.strip()


def clean_description(raw: str | None) -> tuple[str, int]:
    """Job description HTML -> (safe HTML with only p/ul/li/br/strong/em, number of text characters).
    Plain text keeps its line breaks as paragraphs. Some boards send the HTML escaped (&lt;p&gt;)."""
    raw = (raw or "").strip()
    if not raw:
        return "", 0
    if "&lt;" in raw and raw.count("<") < raw.count("&lt;"):
        raw = html.unescape(raw)
    if not re.search(r"</?[a-zA-Z][^>]*>", raw):      # plain text: blank lines / newlines are paragraphs
        paras = [p.strip() for p in re.split(r"\n\s*\n|\r\n\r\n|\n", raw) if p.strip()]
        raw = "".join(f"<p>{html.escape(p, quote=False)}</p>" for p in paras)
    p = _Clean()
    try:
        p.feed(raw)
        p.close()
    except Exception:  # noqa: BLE001 - broken markup: fall back to the plain text
        text = re.sub(r"<[^>]*>", " ", raw)
        text = re.sub(r"\s+", " ", html.unescape(text)).strip()
        return (f"<p>{html.escape(text, quote=False)}</p>" if text else ""), len(text)
    out = p.result()
    if p.chars > MAX_DESCRIPTION_CHARS:     # very long postings: keep whole paragraphs up to the limit
        kept, n = [], 0
        for part in re.split(r"(?<=</p>)|(?<=</ul>)", out):
            n += len(re.sub(r"<[^>]*>", "", part))
            if n > MAX_DESCRIPTION_CHARS and kept:
                break
            kept.append(part)
        out = "".join(kept)
    return out, p.chars


# --------------------------------------------------------------------------- #
# Which jobs get a page
# --------------------------------------------------------------------------- #
def applicant_countries(job: dict, region_countries: dict[str, list[str]]) -> list[str]:
    """Where people can work from: the job's countries, plus for a remote job every country of the regions
    it is open to ("MENA" -> Egypt, Saudi Arabia, ...). Empty for remote-anywhere jobs: Google needs a country."""
    out = list(job.get("co") or [])
    if job.get("w") == REMOTE:
        for r in job.get("rg") or []:
            out += [c for c in region_countries.get(r, []) if c not in out]
    return out


def region_map(meta: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for c in meta.get("countries") or []:
        if c.get("region"):
            out.setdefault(c["region"], []).append(c["name"])
    return out


def attach_details(conn, jobs: list[dict], meta: dict, limit: int | None = None) -> int:
    """Give eligible jobs (in list order, so the core jobs first) a page: sets job["pg"] (its path),
    job["_d"] (clean description HTML), job["_et"] (employment type) and job["_ac"] (countries applicants
    can be in). Returns the number of pages."""
    limit = max_pages() if limit is None else limit
    if not limit:
        return 0
    regions = region_map(meta)
    ids = [j["id"] for j in jobs if applicant_countries(j, regions)]
    if not ids or conn is None:
        return 0
    try:
        with conn.cursor() as cur:
            cur.execute(DETAILS_SQL, {"sources": list(JOB_PAGE_SOURCES), "min_chars": MIN_DESCRIPTION_CHARS, "ids": ids})
            details = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    except Exception as exc:  # noqa: BLE001 - the site still publishes, just without job pages
        log.warning("job pages skipped: %s", exc)
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
        return 0
    return give_pages(jobs, details, limit, regions)


def give_pages(jobs: list[dict], details: dict[str, tuple[str | None, str | None]], limit: int,
               region_countries: dict[str, list[str]] | None = None) -> int:
    n, seen = 0, set()
    for j in jobs:
        if n >= limit:
            break
        ac = applicant_countries(j, region_countries or {})
        if j["id"] in seen or j["id"] not in details or not ac:
            continue
        desc, chars = clean_description(details[j["id"]][0])
        if chars < MIN_DESCRIPTION_CHARS:
            continue
        seen.add(j["id"])
        j["pg"], j["_d"], j["_et"], j["_ac"] = job_path(j), desc, details[j["id"]][1], ac
        n += 1
    log.info("job pages: %s jobs get their own page (limit %s)", n, limit)
    return n


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def employment_type(job: dict) -> list[str]:
    s = (job.get("_et") or "").lower()
    out = []
    if job.get("s") == "Intern / Student" or "intern" in s:
        out.append("INTERN")
    for word, value in (("full", "FULL_TIME"), ("permanent", "FULL_TIME"), ("part", "PART_TIME"),
                        ("contract", "CONTRACTOR"), ("freelance", "CONTRACTOR"), ("temp", "TEMPORARY")):
        if word in s and value not in out:
            out.append(value)
    return out


def _locality(job: dict) -> str | None:
    """The city, when the job is in one country and its location starts with a city name."""
    co = job.get("co") or []
    loc = (job.get("l") or "").strip()
    if len(co) != 1 or not loc or any(ch in loc for ch in ";|/"):
        return None
    first = loc.split(",")[0].strip()
    if (not first or len(first) > 40 or first.lower() == co[0].lower()
            or first.lower() in ("remote", "hybrid", "onsite", "on-site", "anywhere", "multiple locations")):
        return None
    return first


def place_label(job: dict) -> str:
    if job.get("w") == REMOTE:
        return "Remote"
    co = job.get("co") or []
    loc = _locality(job)
    if loc:
        return f"{loc}, {co[0]}"
    return ", ".join(co[:3]) + (" +" if len(co) > 3 else "")


def remote_line(job: dict) -> str:
    if job.get("w") != REMOTE:
        return ""
    co = job.get("co") or []
    regions = [r for r in job.get("rg") or [] if r != "Worldwide"]
    if regions:
        where = ", ".join(co + regions[:-1]) + (" and " if co or len(regions) > 1 else "") + regions[-1]
        where = where.replace(", and", " and")
    else:
        where = ", ".join(co[:8]) + (f" and {len(co) - 8} more countries" if len(co) > 8 else "")
    return f"This is a fully remote job, open to people in {where}."


def jobposting_jsonld(job: dict, url: str) -> dict:
    co = (job.get("_ac") or job.get("co") or [])[:MAX_COUNTRIES]
    rl = remote_line(job)
    data = {
        "@context": "https://schema.org/", "@type": "JobPosting",
        "title": job.get("t"),
        "description": (f"<p>{html.escape(rl, quote=False)}</p>" if rl else "") + (job.get("_d") or ""),
        "datePosted": job.get("p"),
        "hiringOrganization": {"@type": "Organization", "name": job.get("c") or "Confidential"},
        "identifier": {"@type": "PropertyValue", "name": job.get("c") or "Radarak", "value": job["id"]},
        "directApply": False,
        "url": url,
    }
    et = employment_type(job)
    if et:
        data["employmentType"] = et if len(et) > 1 else et[0]
    if job.get("w") == REMOTE:
        data["jobLocationType"] = "TELECOMMUTE"
        data["applicantLocationRequirements"] = [{"@type": "Country", "name": c} for c in co]
    else:
        city = _locality(job)
        data["jobLocation"] = [{"@type": "Place", "address": {"@type": "PostalAddress", "addressCountry": c,
                                                              **({"addressLocality": city} if city else {})}}
                               for c in co]
    return data


def _alerts_html(place: str | None, meta: dict, rel: str) -> str:
    from jobradar.alerts import alerts_block
    return alerts_block(place, meta, rel, "en")


def render_job_page(job: dict, meta: dict, base: str, place_pages: dict[str, dict[str, str]]) -> str:
    """place_pages: {place: {"": country page path, "track:<x>": track page, "role:<x>": role page}}."""
    t = T["en"]
    path = job["pg"]
    rel = "../" * path.count("/")
    url = base + path
    skills = meta.get("skills", [])
    title, company = job.get("t") or "", job.get("c") or ""
    where = place_label(job)
    is_remote = job.get("w") == REMOTE
    main_place = REMOTE if is_remote else (job.get("co") or [None])[0]
    posted = dt.date.fromisoformat(job["p"]) if job.get("p") else None

    facts = ["Fully remote" if is_remote else (job.get("w") or "")]
    if job.get("s") and job.get("s") != "Not stated":
        facts.append(job["s"])
    if job.get("r"):
        facts.append(job["r"])
    if posted:
        facts.append("Posted " + _date(posted, "en"))
    flags = job.get("f") or 0
    if flags & 1:
        facts.append(t["visa"])
    if flags & 2:
        facts.append("Nationals only")
    if flags & 4:
        facts.append("Arabic required")
    pay = ""
    if job.get("$"):
        lo, hi = job["$"]
        pay = f"${lo}k" if lo == hi else f"${lo}k–${hi}k"
        facts.append(pay + " a year (converted to USD)")
    sk_names = [skills[i] for i in job.get("k", []) if i < len(skills)]
    sk_html = "".join(f"<span>{_e(s)}</span>" for s in sk_names[:12])
    apply_rel = "noopener" if job.get("df") else "nofollow noopener"
    rl = remote_line(job)

    pp = place_pages.get(main_place, {}) if main_place else {}
    more = []
    if pp.get("role:" + (job.get("r") or "")):
        more.append((pp["role:" + job["r"]], f"More {job['r']} jobs" + ("" if is_remote else f" in {main_place}")))
    if pp.get("track:" + (job.get("tr") or "")):
        more.append((pp["track:" + job["tr"]], f"{job['tr']} jobs" + (" (remote)" if is_remote else f" in {main_place}")))
    if pp.get(""):
        more.append((pp[""], "All remote tech jobs" if is_remote else f"All tech jobs in {main_place}"))
    more_html = "".join(f'<a href="{_e(rel + h)}">{_e(x)}</a>' for h, x in more)

    crumbs = [(t["home"], rel, base), (t["jobs"], rel + "jobs/", base + "jobs/")]
    if pp.get(""):
        crumbs.append(("Remote" if is_remote else main_place, rel + pp[""], base + pp[""]))
    crumbs.append((title, None, url))
    crumb_html = " › ".join(f'<a href="{_e(h)}">{_e(x)}</a>' if h else f"<span>{_e(x)}</span>" for x, h, _ in crumbs)
    breadcrumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": x, "item": u} for i, (x, _, u) in enumerate(crumbs)]}

    page_title = f"{title} at {company} · {where} | Radarak" if company else f"{title} · {where} | Radarak"
    desc = (f"{company or 'A company'} is hiring: {title}, {where}"
            + (f", {job['s'].lower()} level" if job.get("s") and job["s"] != "Not stated" else "")
            + (f". Skills: {', '.join(sk_names[:5])}" if sk_names else "")
            + (f". Pay about {pay} a year" if pay else "")
            + ". Apply on the company's career site.")
    apply_btn = (f'<a class="primary" href="{_e(job.get("u"))}" target="_blank" rel="{apply_rel}" '
                 f'data-apply>Apply on {_e(company or "the company")}\'s site →</a>')
    body = f"""  <main class="seo jobpage">
    <nav class="crumbs" aria-label="Breadcrumb">{crumb_html}</nav>
    <h1>{_e(title)}</h1>
    <p class="lead"><b>{_e(company)}</b> · {_e(where)}</p>
    <p class="m">{_e(" · ".join(x for x in facts if x))}</p>
    {f'<p class="sk">{sk_html}</p>' if sk_html else ''}
    <div class="ctarow">{apply_btn}<a class="ghostbtn" href="{_e(rel)}#job={_e(job['id'])}">Open in Radarak</a></div>
    <section class="jd"><h2>About the job</h2>
      {f'<p><b>{_e(rl)}</b></p>' if rl else ''}{job.get('_d') or ''}
    </section>
    <p class="note">This job is posted on {_e(company or "the company")}'s career site. Radarak links to the original posting: apply there.</p>
    <div class="ctarow">{apply_btn}</div>
    {_alerts_html(main_place, meta, rel)}
    {f'<section><h2>Similar jobs</h2><div class="links">{more_html}</div></section>' if more_html else ''}
  </main>"""
    return _shell("en", rel, page_title, desc, url, None, None, None, body,
                  [jobposting_jsonld(job, url), breadcrumbs], base + "og.png")


def job_page_files(jobs: list[dict], meta: dict, base: str,
                   place_pages: dict[str, dict[str, str]]) -> tuple[dict[str, bytes], list[tuple[str, str]]]:
    """Pages for every job that has job["pg"], and (url, lastmod) pairs for sitemap-jobs.xml."""
    files, urls, seen = {}, [], set()
    for j in jobs:
        if not j.get("pg") or j["pg"] in seen:
            continue
        seen.add(j["pg"])
        files[j["pg"] + "index.html"] = render_job_page(j, meta, base, place_pages).encode()
        urls.append((base + j["pg"], j.get("fs") or j.get("p") or ""))
    return files, urls


def sitemap(urls: list[tuple[str, str]]) -> bytes:
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join(f"  <url><loc>{_e(u)}</loc>" + (f"<lastmod>{_e(d)}</lastmod>" if d else "") + "</url>\n"
                      for u, d in urls)
            + "</urlset>\n").encode()

