"""End-to-end tests of the published website, in a real browser (Chromium via Playwright).

Run against the live site or a local copy of the gh-pages branch:
    pip install pytest playwright && python -m playwright install chromium
    SITE_URL=https://radarak.online  python -m pytest tests/e2e -v
    SITE_DIR=path/to/gh-pages-clone  python -m pytest tests/e2e -v      (served on localhost)

Counts on the page are checked against counts computed here, independently, from data/jobs.json,
so a wrong filter shows up as a failed test, not just "the page loaded".
"""
from __future__ import annotations

import datetime as dt
import functools
import http.server
import io
import json
import os
import re
import threading
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pytest

pw = pytest.importorskip("playwright.sync_api")

SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
SITE_DIR = os.environ.get("SITE_DIR", "")
if not SITE_URL and not SITE_DIR:
    pytest.skip("set SITE_URL or SITE_DIR to run the website tests", allow_module_level=True)

FLAG = {"visa": 1, "nationals": 2, "arabic": 4, "longOpen": 8}
JUNIOR = {"Intern / Student", "Junior"}
PAGE = 30


# --------------------------------------------------------------------------- server + data
@pytest.fixture(scope="session")
def base():
    if SITE_URL:
        yield SITE_URL
        return
    handler = functools.partial(_Quiet, directory=SITE_DIR)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://localhost:{srv.server_address[1]}"   # "localhost" so the service worker may register
    srv.shutdown()


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def fetch(base: str, path: str) -> bytes:
    if SITE_DIR and not SITE_URL:
        p = Path(SITE_DIR) / path.lstrip("/").split("?")[0].split("#")[0]
        if p.is_dir():
            p = p / "index.html"
        return p.read_bytes()
    with urllib.request.urlopen(base + "/" + path.lstrip("/"), timeout=60) as r:
        return r.read()


def exists(base: str, path: str) -> bool:
    try:
        fetch(base, path)
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def data(base):
    jobs = json.loads(fetch(base, "data/jobs.json"))
    if exists(base, "data/jobs-more.json"):          # the rest of the list (outside the Middle East / Africa)
        jobs += json.loads(fetch(base, "data/jobs-more.json"))
    meta = json.loads(fetch(base, "data/meta.json"))
    region = {c["name"]: c["region"] for c in meta["countries"]}
    return {"jobs": jobs, "meta": meta, "region": region}


def expected(data, country="", track="", q="", remote=False, visa=False, junior=False, pay=False,
             week=False, hide_nat=True, seniority="", work_mode="", skill="") -> int:
    """Number of results the page should show (same title at the same company counts once)."""
    meta, region = data["meta"], data["region"]
    week_ago = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)).date().isoformat()
    skill_idx = meta["skills"].index(skill) if skill else -1
    keys = set()
    for j in data["jobs"]:
        f = j.get("f") or 0
        if track and j["tr"] != track: continue
        if seniority and j["s"] != seniority: continue
        if work_mode and j["w"] != work_mode: continue
        if skill_idx >= 0 and skill_idx not in j["k"]: continue
        if remote and j["w"] != "Remote": continue
        if visa and not f & FLAG["visa"]: continue
        if junior and j["s"] not in JUNIOR: continue
        if pay and not j.get("$"): continue
        if week and (j["p"] < week_ago or f & FLAG["longOpen"]): continue
        if hide_nat and f & FLAG["nationals"]: continue
        if q:
            text = " ".join([j["t"], j.get("c") or "", j.get("r") or "", *[meta["skills"][k] for k in j["k"]]]).lower()
            if not all(w in text for w in [q.lower()]): continue
        if country and not (country in j["co"] or (j["w"] == "Remote" and (j.get("ww") == 1 or region.get(country) in j["rg"]
                                                                          or "Worldwide" in j["rg"]))):
            continue
        keys.add(j["t"].lower() + "|" + (j.get("c") or "").lower())
    return len(keys)


# --------------------------------------------------------------------------- browser
@pytest.fixture(scope="session")
def browser():
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


class Page:
    """A fresh visitor (empty storage) with JS errors collected."""

    def __init__(self, browser, base, width=1366, height=1000, storage: dict | None = None, mobile=False):
        self.ctx = browser.new_context(viewport={"width": width, "height": height}, is_mobile=mobile,
                                       has_touch=mobile, permissions=["clipboard-read", "clipboard-write"])
        init = "localStorage.setItem('jr_lang', JSON.stringify('en'));"
        for k, v in (storage or {}).items():
            init += f"localStorage.setItem({json.dumps(k)}, {json.dumps(json.dumps(v))});"
        self.ctx.add_init_script(f"if (!sessionStorage.getItem('_seeded')) {{ {init} sessionStorage.setItem('_seeded','1'); }}")
        self.p = self.ctx.new_page()
        self.errors: list[str] = []
        self.p.on("pageerror", lambda e: self.errors.append(f"pageerror: {e}"))
        self.p.on("console", lambda m: self.errors.append(f"console: {m.text}") if m.type == "error"
                  and "goatcounter" not in m.text.lower() and "ERR_NAME_NOT_RESOLVED" not in m.text
                  and "Failed to load resource" not in m.text else None)
        self.base = base

    def open(self, path="", wait_jobs=True):
        self.p.goto(self.base + "/" + path)
        if wait_jobs:
            self.p.wait_for_function("document.querySelector('#count') && /\\d/.test(document.querySelector('#count').textContent)"
                                     " && !document.querySelector('#jobList[aria-busy]')"
                                     " && !/…/.test(document.querySelector('#countLabel').textContent)", timeout=30000)
        return self.p

    def count(self) -> int:
        return int(self.p.locator("#count").inner_text().replace(",", ""))

    def close(self):
        self.ctx.close()


@pytest.fixture
def page(browser, base):
    made = []

    def make(**kw):
        pg = Page(browser, base, **kw)
        made.append(pg)
        return pg
    yield make
    for pg in made:
        pg.close()


def no_errors(pg: Page):
    assert not pg.errors, "\n".join(pg.errors[:5])


# =========================================================================== 1. data files
def test_data_files_are_valid(data):
    jobs, meta = data["jobs"], data["meta"]
    assert len(jobs) > 1000 and meta["listed_jobs"] == len(jobs)
    ids = [j["id"] for j in jobs]
    assert len(ids) == len(set(ids)), "duplicate job ids"
    countries = {c["name"] for c in meta["countries"]}
    today = dt.date.today().isoformat()
    for j in jobs:
        assert j["t"] and j["u"].startswith(("http://", "https://")), j
        assert j["w"] in ("Remote", "Hybrid", "Onsite"), j["w"]
        assert set(j["co"]) <= countries, (j["id"], j["co"])
        assert all(0 <= k < len(meta["skills"]) for k in j["k"])
        assert j["p"] <= today, ("posted in the future", j["id"], j["p"])
        if j.get("$"):
            assert j["$"][0] <= j["$"][1], j


def test_no_israel_and_palestine_listed(data):
    names = {c["name"] for c in data["meta"]["countries"]}
    assert "Israel" not in names and "Excluded" not in names and "Palestine" in names
    blob = json.dumps(data["jobs"]).lower()
    assert '"israel"' not in blob and "tel aviv" not in json.dumps([j["co"] for j in data["jobs"]]).lower()


def test_source_credits(data):
    by = {j.get("by") for j in data["jobs"]}
    assert "Jobs by Adzuna" in by
    for j in data["jobs"]:
        if j.get("by") == "via Remote OK":
            assert j.get("df") == 1 and "remoteok.com" in j["u"].lower()


def test_salaries_are_plausible(data):
    odd = [(j["t"], j["$"]) for j in data["jobs"] if j.get("$") and (j["$"][1] > 900 or j["$"][0] < 3)]
    assert len(odd) <= len(data["jobs"]) * 0.001, f"{len(odd)} salaries outside $3k-$900k a year, e.g. {odd[:5]}"


# =========================================================================== 2. main page
def test_home_loads_without_errors(page, data):
    pg = page()
    pg.open()
    assert pg.count() == expected(data)
    assert pg.p.locator("#jobList > li.job").count() == min(PAGE, expected(data))
    assert "Jobs by Adzuna" in pg.p.locator("#footText").inner_text()
    no_errors(pg)


@pytest.mark.parametrize("country", ["Egypt", "Saudi Arabia", "United Arab Emirates", "Germany", "Palestine", "Algeria"])
def test_country_filter(page, data, country):
    pg = page()
    p = pg.open()
    p.select_option("#country", country)
    p.wait_for_timeout(300)
    assert pg.count() == expected(data, country=country)
    assert f"country={country.replace(' ', '+')}" in p.url
    no_errors(pg)


def test_track_pills(page, data):
    pg = page()
    p = pg.open()
    p.select_option("#country", "Egypt")
    pill = p.locator("#trackPills .tpill[data-track^='track:']").first
    track = pill.get_attribute("data-track")[6:]
    pill_n = int(pill.locator(".n").inner_text().replace(",", ""))
    pill.click()
    p.wait_for_timeout(300)
    assert pg.count() == expected(data, country="Egypt", track=track) == pill_n
    assert "track%3A" in p.url
    no_errors(pg)


def test_keyword_search(page, data):
    pg = page()
    p = pg.open()
    p.fill("#q", "python")
    p.wait_for_timeout(400)
    assert pg.count() == expected(data, q="python") > 0
    p.fill("#q", "zzqqxx-no-such-job")
    p.wait_for_timeout(400)
    assert pg.count() == 0 and p.locator("#empty").is_visible()
    p.click("#emptyReset")
    p.wait_for_timeout(300)
    assert pg.count() == expected(data)
    no_errors(pg)


@pytest.mark.parametrize("flag", ["remote", "visa", "junior", "pay", "week"])
def test_quick_toggles(page, data, flag):
    pg = page()
    p = pg.open()
    p.click(f".toggle[data-flag='{flag}']")
    p.wait_for_timeout(300)
    assert p.locator(f".toggle[data-flag='{flag}']").get_attribute("aria-pressed") == "true"
    assert pg.count() == expected(data, **{flag: True})
    assert p.locator(f".fchip[data-flag-off='{flag}']").count() == 1       # active-filter chip
    no_errors(pg)


def test_show_nationals_only_jobs(page, data):
    pg = page()
    p = pg.open()
    p.click(".toggle[data-flag='hideNat']")
    p.wait_for_timeout(300)
    assert pg.count() == expected(data, hide_nat=False) >= expected(data)


def test_sidebar_filters(page, data):
    pg = page()
    p = pg.open()
    p.select_option("#seniority", "Senior")
    p.select_option("#workMode", "Remote")
    p.wait_for_timeout(300)
    assert pg.count() == expected(data, seniority="Senior", work_mode="Remote")
    skill = "Python" if "Python" in data["meta"]["skills"] else data["meta"]["skills"][0]
    p.select_option("#skill", skill)
    p.wait_for_timeout(300)
    assert pg.count() == expected(data, seniority="Senior", work_mode="Remote", skill=skill)
    chips = p.locator("#activeFilters .fchip").count()
    assert chips == 3
    p.click("#chipsClear")
    p.wait_for_timeout(300)
    assert pg.count() == expected(data) and p.locator("#activeFilters .fchip").count() == 0
    no_errors(pg)


def test_filters_survive_reload_and_shared_link(page, data):
    pg = page()
    p = pg.open("#country=Egypt&role=track%3AData+%26+Analytics&remote=1")
    assert pg.count() == expected(data, country="Egypt", track="Data & Analytics", remote=True)
    p.reload()
    p.wait_for_timeout(1500)
    assert pg.count() == expected(data, country="Egypt", track="Data & Analytics", remote=True)
    no_errors(pg)


def test_sort_by_salary(page, data):
    pg = page()
    p = pg.open()
    p.select_option("#sort", "pay")
    p.wait_for_timeout(400)
    first = p.locator("#jobList > li.job").first.locator(".fact.pay").inner_text()
    top = max((j["$"][0] + j["$"][1], j["$"]) for j in data["jobs"] if j.get("$") and not (j.get("f", 0) & 2))[1]
    want = f"${top[0]}k" if top[0] == top[1] else f"${top[0]}k – ${top[1]}k"
    assert first == want


def test_load_more(page, data):
    pg = page()
    p = pg.open()
    p.click("#more")
    p.wait_for_timeout(300)
    assert p.locator("#jobList > li.job").count() == min(2 * PAGE, expected(data))


def test_job_details_panel(page, data):
    pg = page()
    p = pg.open()
    row = p.locator("#jobList > li.job").first
    jid = row.get_attribute("data-jid")
    row.locator("h3 a").click()
    p.wait_for_selector("#jobDrawer:not([hidden])")
    assert f"job={jid}" in p.url
    job = next(j for j in data["jobs"] if j["id"] == jid)
    apply = p.locator("#jobDrawer .apply")
    assert apply.get_attribute("href") == job["u"]
    assert ("nofollow" in apply.get_attribute("rel")) != bool(job.get("df"))
    p.keyboard.press("Escape")
    p.wait_for_timeout(300)
    assert "job=" not in p.url and p.locator("#jobDrawer").is_hidden()
    no_errors(pg)


def test_job_deep_link(page, data):
    jid = data["jobs"][5]["id"]
    pg = page()
    p = pg.open(f"#job={jid}")
    p.wait_for_selector("#jobDrawer:not([hidden])")
    assert data["jobs"][5]["t"] in p.locator("#drawerBody").inner_text()
    no_errors(pg)


def test_remote_ok_links_are_followed(page, data):
    rok = [j for j in data["jobs"] if j.get("df")]
    if not rok:
        pytest.skip("no Remote OK jobs in the data yet")
    pg = page()
    p = pg.open(f"#job={rok[0]['id']}")
    p.wait_for_selector("#jobDrawer:not([hidden])")
    rel = p.locator("#jobDrawer .apply").get_attribute("rel")
    assert "nofollow" not in rel and "via Remote OK" in p.locator("#drawerBody").inner_text()


def test_save_apply_and_saved_tab(page, data):
    pg = page()
    p = pg.open()
    row = p.locator("#jobList > li.job").first
    jid = row.get_attribute("data-jid")
    row.locator(f"[data-id='{jid}']").click()
    assert p.locator("#savedCount").inner_text() == "1"
    p.reload()
    p.wait_for_timeout(1500)
    assert p.locator("#savedCount").inner_text() == "1", "saved job lost after reload"
    p.click("#tab-saved")
    assert p.locator("#savedList li.job").count() == 1
    p.click(f"#savedList [data-applied='{jid}']")
    p.wait_for_timeout(200)
    assert "Applied" in p.locator("#savedList").inner_text()
    p.click("[data-saved-view='done']")
    assert p.locator("#savedList li.job").count() == 1
    p.click("[data-saved-view='todo']")
    assert p.locator("#savedList li.job").count() == 0
    no_errors(pg)


def test_report_closed_hides_job(page, data):
    pg = page()
    p = pg.open()
    before = pg.count()
    row = p.locator("#jobList > li.job").first
    jid = row.get_attribute("data-jid")
    row.locator("h3 a").click()
    p.wait_for_selector("#jobDrawer:not([hidden])")
    p.click("#reportJob")
    p.wait_for_timeout(300)
    assert p.locator("#toast").is_visible()
    assert p.locator(f"#jobList > li.job[data-jid='{jid}']").count() == 0
    assert pg.count() <= before
    no_errors(pg)


def test_whatsapp_and_copy_link(page, data):
    pg = page()
    p = pg.open()
    row = p.locator("#jobList > li.job").first
    wa = row.locator("a[href^='https://wa.me/']")
    assert wa.count() == 1
    assert "%23job%3D" in wa.get_attribute("href")
    row.locator("h3 a").click()
    p.wait_for_selector("#jobDrawer:not([hidden])")
    p.click("#copyJob")
    p.wait_for_timeout(300)
    copied = p.evaluate("navigator.clipboard.readText()")
    assert "#job=" in copied
    no_errors(pg)


def test_my_skills_and_match(page, data):
    pg = page()
    p = pg.open()
    for s in ("SQL", "Python"):
        p.fill("#mySkillInput", s)
        p.press("#mySkillInput", "Enter")
    p.wait_for_timeout(300)
    assert p.locator("#mySkills .chip").count() == 2
    assert p.locator("#sort").input_value() == "match"
    assert p.locator("#jobList .ring").count() > 0
    p.locator("#mySkills .chip").first.click()
    assert p.locator("#mySkills .chip").count() == 1
    p.reload()
    p.wait_for_timeout(1500)
    assert p.locator("#mySkills .chip").count() == 1, "skills not remembered"
    no_errors(pg)


def test_learn_next(page, data):
    pg = page(storage={"jr_mySkills": ["SQL", "Python"]})
    p = pg.open()
    p.wait_for_selector("#learnNext:not([hidden])")
    steps = p.locator("#learnNext .learnsteps li")
    assert steps.count() >= 1
    skill = steps.first.locator("b").inner_text()
    steps.first.locator("[data-learn-see]").click()
    p.wait_for_timeout(300)
    assert p.locator("#skill").input_value() == skill
    no_errors(pg)


def test_cv_paste(page, data):
    pg = page()
    p = pg.open()
    p.click("#cvPasteBtn")
    p.fill("#cvText", "Data Engineer, 3 years of experience. Skills: Python, SQL, Apache Airflow, dbt, PostgreSQL, Docker.")
    p.click("#cvRead")
    p.wait_for_timeout(500)
    skills = p.locator("#mySkills .chip").all_inner_texts()
    found = {s.replace(" ✕", "") for s in skills}
    assert {"Python", "SQL"} <= found, found
    no_errors(pg)


def _pdf_bytes(text: str) -> bytes:
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in text.split("\n"):
        c.drawString(50, y, line)
        y -= 20
    c.save()
    return buf.getvalue()


def _docx_bytes(text: str) -> bytes:
    import docx
    d = docx.Document()
    for line in text.split("\n"):
        d.add_paragraph(line)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


@pytest.mark.parametrize("kind", ["pdf", "docx"])
def test_cv_upload(page, data, kind, tmp_path):
    pytest.importorskip("reportlab" if kind == "pdf" else "docx")
    text = "Jane Doe - Backend Developer\nExperience: 4 years\nSkills: Java, Spring, Kubernetes, AWS, SQL"
    f = tmp_path / f"cv.{kind}"
    f.write_bytes(_pdf_bytes(text) if kind == "pdf" else _docx_bytes(text))
    pg = page()
    p = pg.open()
    p.set_input_files("#cvFile", str(f))
    p.wait_for_function("document.querySelectorAll('#mySkills .chip').length >= 3", timeout=20000)
    found = {s.replace(" ✕", "") for s in p.locator("#mySkills .chip").all_inner_texts()}
    assert {"Java", "Kubernetes", "AWS"} <= found, found
    no_errors(pg)


def test_new_since_last_visit(page, data):
    gen = data["meta"]["generated_at"][:10]
    earlier = (dt.date.fromisoformat(gen) - dt.timedelta(days=3)).isoformat()
    pg = page(storage={"jr_visit": {"data": earlier, "prev": None}})
    p = pg.open()
    p.wait_for_selector("#newBanner:not([hidden])")
    p.click("#newToggle")
    p.wait_for_timeout(300)
    n_new = pg.count()
    want = len({j["t"].lower() + "|" + (j.get("c") or "").lower() for j in data["jobs"]
                if (j.get("fs") or j["p"]) > earlier and not (j.get("f", 0) & 2)})
    assert n_new == want and 0 < n_new < expected(data)
    no_errors(pg)


def test_arabic(page, data):
    pg = page()
    p = pg.open()
    p.click("#lang")
    p.wait_for_timeout(400)
    assert p.evaluate("document.documentElement.dir") == "rtl" and p.evaluate("document.documentElement.lang") == "ar"
    assert re.search(r"[؀-ۿ]", p.locator("#heroTitle").inner_text())
    p.reload()
    p.wait_for_timeout(1500)
    assert p.evaluate("document.documentElement.lang") == "ar", "language not remembered"
    assert pg.count() == expected(data)
    no_errors(pg)


@pytest.mark.parametrize("tab", ["insights", "trends", "about", "saved"])
def test_tabs(page, data, tab):
    pg = page()
    p = pg.open()
    p.click(f"#tab-{tab}")
    p.wait_for_timeout(800)
    assert p.locator(f"#{tab}").is_visible()
    if tab == "insights":
        assert p.locator("#skillBars li, #skillBars .bar, #skillBars > *").count() > 0
    if tab == "trends":   # the chart needs 14 days of history; before that a "coming soon" note shows
        history = json.loads(fetch(pg.base, "data/trends.json"))["history_days"]
        if history >= 14:
            assert p.locator("#weeklyChart *").count() > 0
        else:
            assert p.locator("#weeklyHint").inner_text().strip()
    if tab == "about":
        assert "Sources" in p.locator("#aboutText").inner_text()
    assert f"tab={tab}" in p.url
    no_errors(pg)


def test_newsletter_box(page, data):
    pg = page()
    p = pg.open()
    if not p.locator("#newsletter").get_attribute("data-bd"):
        pytest.skip("newsletter not configured")
    assert p.locator("#newsletter").is_visible()
    assert p.locator("#nlForm").get_attribute("action").startswith("https://buttondown.com/api/emails/embed-subscribe/")
    assert p.locator("#nlEmail").get_attribute("type") == "email"


def test_slash_focuses_search(page, data):
    pg = page()
    p = pg.open()
    p.locator("body").click(position={"x": 5, "y": 5})
    p.keyboard.press("/")
    assert p.evaluate("document.activeElement.id") in ("q", "qMini")


def test_data_load_error_message(browser, base):
    pg = Page(browser, base)
    pg.p.route("**/data/jobs.json", lambda r: r.fulfill(status=500, body="x"))
    pg.open(wait_jobs=False)
    pg.p.wait_for_selector("#empty:not([hidden])", timeout=15000)
    assert pg.p.locator("#empty").inner_text().strip()
    pg.close()


def test_pwa_manifest_and_service_worker(page, base):
    man = json.loads(fetch(base, "manifest.webmanifest"))
    assert man["name"] and man["start_url"] and man["display"] in ("standalone", "minimal-ui")
    for icon in man["icons"]:
        assert exists(base, icon["src"]), icon["src"]
    pg = page()
    p = pg.open()
    if urlparse(base).hostname in ("localhost",) or base.startswith("https"):
        p.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.getRegistration().then(r => !!r)", timeout=10000)


# =========================================================================== 3. phones
def test_mobile_layout_and_filter_sheet(page, data):
    pg = page(width=390, height=844, mobile=True)
    p = pg.open()
    assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "page scrolls sideways"
    p.click("#filterOpen")
    p.wait_for_timeout(300)
    assert p.evaluate("document.body.classList.contains('sheet-open')")
    p.click(".toggle[data-flag='remote']")
    p.wait_for_timeout(300)
    assert str(expected(data, remote=True)) in p.locator("#sheetDone").inner_text().replace(",", "")
    p.click("#sheetDone")
    p.wait_for_timeout(300)
    assert not p.evaluate("document.body.classList.contains('sheet-open')")
    assert pg.count() == expected(data, remote=True)
    no_errors(pg)


@pytest.mark.parametrize("path", ["", "ar/", "jobs/egypt/", "ar/jobs/egypt/", "companies/", "juniors/", "salaries/", "report.html"])
def test_no_sideways_scroll_on_phones(page, path):
    pg = page(width=360, height=740, mobile=True)
    p = pg.open(path, wait_jobs=False)
    p.wait_for_timeout(1500)
    assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), f"{path or '/'} scrolls sideways"
    no_errors(pg)


# =========================================================================== 4. static pages
def _html_files(base):
    if SITE_DIR and not SITE_URL:
        root = Path(SITE_DIR)
        return [str(p.relative_to(root)).replace(os.sep, "/") for p in root.rglob("*.html") if ".git" not in p.parts]
    sm = fetch(base, "sitemap.xml").decode()
    return [urlparse(u).path.lstrip("/") or "index.html" for u in re.findall(r"<loc>([^<]+)</loc>", sm)]


def test_internal_links_resolve(base):
    broken = []
    pages = _html_files(base)
    for path in pages:
        html = fetch(base, path).decode("utf-8", "replace")
        page_url = "http://x/" + path
        for ref in re.findall(r'(?:href|src)="([^"#]+)', html):
            if ref.startswith(("http", "mailto:", "tel:", "data:", "javascript:")):
                continue
            target = urlparse(urljoin(page_url, ref)).path.lstrip("/")
            if not exists(base, target or "index.html"):
                broken.append(f"{path} -> {ref}")
    assert not broken, f"{len(broken)} broken links, e.g. {broken[:8]}"


def test_sitemap_robots_cname(base):
    sm = fetch(base, "sitemap.xml").decode()
    locs = re.findall(r"<loc>([^<]+)</loc>", sm)
    assert len(locs) > 50 and all(u.startswith("https://radarak.online/") for u in locs)
    missing = [u for u in locs if not exists(base, urlparse(u).path.lstrip("/") or "index.html")]
    assert not missing, missing[:5]
    assert "sitemap" in fetch(base, "robots.txt").decode().lower()
    if SITE_DIR:
        assert fetch(base, "CNAME").decode().strip() == "radarak.online"


def test_seo_tags(base):
    for path in ["index.html", "jobs/egypt/index.html", "ar/jobs/egypt/index.html", "companies/index.html"]:
        html = fetch(base, path).decode()
        assert re.search(r'<link rel="canonical" href="https://radarak\.online/', html), path
        assert "<title>" in html and 'name="description"' in html, path
        if path.startswith(("jobs/", "ar/jobs/")):
            assert 'hreflang="ar"' in html and 'hreflang="en"' in html, path


def test_versioned_assets_match_files(base):
    import hashlib
    html = fetch(base, "index.html").decode() + fetch(base, "jobs/egypt/index.html").decode()
    refs = set(re.findall(r'(?:href|src)="(?:\.\./)*/?([\w./-]+\.(?:css|js))\?v=([0-9a-f]+)"', html))
    assert refs, "no ?v= asset versions found"
    for path, v in refs:
        assert hashlib.sha1(fetch(base, path)).hexdigest()[:10] == v, f"{path}?v={v} is stale (browsers keep the old file)"


def _country_pages(base):
    return sorted({m.group(1) for p in _html_files(base) if (m := re.match(r"jobs/([\w-]+)/index\.html$", p))})


def test_every_country_page_loads(base, data):
    places = _country_pages(base)
    assert len(places) >= 30
    for place in places:
        for prefix in ("", "ar/"):
            html = fetch(base, f"{prefix}jobs/{place}/index.html").decode()
            assert "data-filters" in html and "<li" in html, f"{prefix}jobs/{place}/"


@pytest.mark.parametrize("path", ["jobs/egypt/", "ar/jobs/saudi-arabia/", "jobs/remote/"])
def test_country_page_filters(page, path):
    pg = page()
    p = pg.open(path, wait_jobs=False)
    p.wait_for_selector("[data-filters].js-on")
    block = p.locator("[data-filters]").first
    items = block.locator("[data-list] > li")
    total = items.count()
    visible = lambda: block.locator("[data-list] > li:not([hidden])").count()
    assert visible() == min(total, int(block.get_attribute("data-page") or total))
    text = block.locator("[data-f][data-mode='text']")
    if text.count():
        word = items.first.locator("h3").inner_text().split()[0]
        text.first.fill(word)
        p.wait_for_timeout(300)
        n = block.locator("[data-list] > li:not([hidden])").count()
        assert 0 < n <= total
        assert "f=" in p.url
        block.locator("[data-clear]").click()
        p.wait_for_timeout(200)
    sel = block.locator("select[data-f]").first
    if sel.count():
        opts = sel.locator("option").all()
        if len(opts) > 1:
            sel.select_option(index=1)
            p.wait_for_timeout(300)
            v = sel.input_value().lower()
            key = sel.get_attribute("data-f")
            shown = block.locator("[data-list] > li:not([hidden])")
            for i in range(min(shown.count(), 10)):
                d = (shown.nth(i).get_attribute(f"data-{key}") or "").lower()
                assert v == d or v in d.split("|"), (key, v, d)
    no_errors(pg)


def test_companies_page(page):
    pg = page()
    p = pg.open("companies/", wait_jobs=False)
    p.wait_for_selector("[data-filters].js-on")
    block = p.locator("[data-filters]").first
    total = block.locator("[data-list] > li").count()
    assert total > 50
    word = block.locator("[data-list] > li").nth(3).get_attribute("data-t").split()[0]
    block.locator("[data-f][data-mode='text']").first.fill(word)
    p.wait_for_timeout(300)
    n = block.locator("[data-list] > li:not([hidden])").count()
    assert 0 < n < total
    first_link = block.locator("[data-list] > li:not([hidden]) a").first.get_attribute("href")
    assert first_link
    no_errors(pg)


def test_juniors_page(page, data):
    pg = page()
    p = pg.open("juniors/", wait_jobs=False)
    p.wait_for_selector("[data-filters].js-on")
    items = p.locator("[data-filters] [data-list] > li")
    assert items.count() > 0
    for i in range(min(items.count(), 20)):
        assert items.nth(i).get_attribute("data-s") in JUNIOR
    no_errors(pg)


def test_salaries_page_and_place_switcher(page):
    pg = page()
    p = pg.open("salaries/", wait_jobs=False)
    p.wait_for_timeout(800)
    assert "$" in p.locator("main").inner_text()
    goto = p.locator("select[data-goto]")
    if goto.count():
        opt = goto.locator("option").nth(1)
        target = opt.get_attribute("value")
        goto.select_option(index=1)
        p.wait_for_url(re.compile(re.escape(target.strip("./").split("/")[-2] if "/" in target else target)), timeout=10000)
    no_errors(pg)


def test_report_page(page):
    pg = page()
    p = pg.open("report.html", wait_jobs=False)
    p.wait_for_timeout(2000)
    post = p.locator("#post").input_value()
    assert post.strip(), "report post text is empty"
    sel = p.locator("select").first
    if sel.count() and sel.locator("option").count() > 1:
        sel.select_option(index=1)
        p.wait_for_timeout(500)
    no_errors(pg)


def test_remote_ok_links_on_static_pages(base, data):
    rok = {j["u"] for j in data["jobs"] if j.get("df")}
    if not rok:
        pytest.skip("no Remote OK jobs in the data yet")
    html = fetch(base, "jobs/remote/index.html").decode()
    for m in re.finditer(r'<a class="go" href="([^"]+)" target="_blank" rel="([^"]+)"', html):
        url = m.group(1).replace("&amp;", "&")
        if url in rok:
            assert "nofollow" not in m.group(2)
        else:
            assert "nofollow" in m.group(2)


# =========================================================================== 5. the two job files
def _more_exists(base):
    if not exists(base, "data/jobs-more.json"):
        pytest.skip("site not split into two job files yet")


def test_split_files_cover_every_listed_job(base, data):
    _more_exists(base)
    core = json.loads(fetch(base, "data/jobs.json"))
    meta = data["meta"]
    assert len(data["jobs"]) == meta["listed_jobs"] and meta["more_jobs"] == len(data["jobs"]) - len(core)
    core_regions = set(meta["core_regions"])
    for j in core:
        assert j["w"] == "Remote" or any(data["region"].get(c) in core_regions for c in j["co"]) \
            or core_regions & set(j["rg"]), j["id"]


def test_core_country_never_downloads_the_rest(page, base, data):
    _more_exists(base)
    pg = page()
    asked = []
    pg.p.on("request", lambda r: asked.append(r.url) if "jobs-more" in r.url else None)
    p = pg.open("#country=Egypt")
    p.wait_for_timeout(1500)
    assert not asked, "Egypt visitors should only download the first file"
    assert pg.count() == expected(data, country="Egypt")
    no_errors(pg)


@pytest.mark.parametrize("country", ["", "Germany", "United States"])
def test_other_countries_load_the_rest(page, base, data, country):
    _more_exists(base)
    pg = page()
    p = pg.open(f"#country={country.replace(' ', '+')}" if country else "")
    p.wait_for_function("!/…/.test(document.querySelector('#countLabel').textContent)", timeout=30000)
    assert pg.count() == expected(data, country=country)
    no_errors(pg)


def test_switching_to_a_far_country_loads_the_rest(page, base, data):
    _more_exists(base)
    pg = page()
    p = pg.open("#country=Egypt")
    p.select_option("#country", "Germany")
    p.wait_for_function("!/…/.test(document.querySelector('#countLabel').textContent)", timeout=30000)
    p.wait_for_timeout(300)
    assert pg.count() == expected(data, country="Germany") > 0
    no_errors(pg)


def test_shared_link_to_a_job_in_the_second_file(page, base, data):
    _more_exists(base)
    other = json.loads(fetch(base, "data/jobs-more.json"))[0]
    pg = page()
    p = pg.open(f"#country=Egypt&job={other['id']}")
    p.wait_for_selector("#jobDrawer:not([hidden])", timeout=30000)
    assert other["t"] in p.locator("#drawerBody").inner_text()
    no_errors(pg)


def test_saved_job_from_the_second_file_is_not_called_closed(page, base, data):
    _more_exists(base)
    other = json.loads(fetch(base, "data/jobs-more.json"))[0]
    saved = {other["id"]: {"t": other["t"], "c": other["c"], "l": other["l"], "u": other["u"], "sv": "2026-10-20"}}
    pg = page(storage={"jr_saved": saved, "jr_country": "Egypt"})
    p = pg.open()
    p.click("#tab-saved")
    p.wait_for_selector(f"#savedList li.job[data-jid='{other['id']}']", timeout=30000)
    assert p.locator("#savedList li.job.closed").count() == 0
    no_errors(pg)


def test_report_page_uses_both_files(page, base):
    _more_exists(base)
    pg = page()
    asked = []
    pg.p.on("request", lambda r: asked.append(r.url) if "jobs-more" in r.url else None)
    pg.open("report.html", wait_jobs=False)
    pg.p.wait_for_timeout(2000)
    assert asked
    no_errors(pg)


# --------------------------------------------------------------------------- alerts + job pages (update 62)
def test_telegram_row_follows_the_country(page, data):
    chans = data["meta"].get("telegram") or []
    if not chans:
        pytest.skip("no public Telegram channels configured")
    pg = page()
    for ch in chans:
        place = next((x for x in ch["pl"] if x != "Remote"), None)
        if not place:
            continue
        p = pg.open(f"#country={place}")
        row = p.locator("#alertRow")
        assert row.is_visible() and row.locator("a.tg").get_attribute("href") == ch["u"]
        break
    assert p.locator("#footTg").is_visible() and p.locator("#footTg a").count() == len(chans)
    row.locator("[data-hide]").click()
    assert not row.is_visible()
    p.reload()
    p.wait_for_timeout(800)
    assert not p.locator("#alertRow").is_visible()               # stays hidden


def test_job_pages_have_jobposting_markup(base):
    if not exists(base, "sitemap-jobs.xml"):
        pytest.skip("no job pages published yet")
    locs = re.findall(r"<loc>([^<]+)</loc>", fetch(base, "sitemap-jobs.xml").decode())
    assert locs
    for u in locs[:: max(1, len(locs) // 15)][:15]:
        html = fetch(base, urlparse(u).path.lstrip("/")).decode()
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        posting = json.loads(blocks[0].replace("<\\/", "</"))[0]
        assert posting["@type"] == "JobPosting" and posting["title"] and posting["hiringOrganization"]["name"]
        assert len(re.sub("<[^>]*>", "", posting["description"])) >= 400 and posting["datePosted"]
        assert posting.get("jobLocation") or posting.get("applicantLocationRequirements")
        assert f'<link rel="canonical" href="{u}">' in html and "data-apply" in html


def test_rss_feeds_parse(base, data):
    feeds = data["meta"].get("feeds") or {}
    if not feeds:
        pytest.skip("no feeds published yet")
    import xml.etree.ElementTree as ET
    for path in list(feeds.values())[:10]:
        root = ET.fromstring(fetch(base, path))
        assert root.find("./channel/title").text and root.findall("./channel/item")
