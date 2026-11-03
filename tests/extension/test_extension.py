"""The Radarak Apply browser extension, loaded into a real Chromium (the engine of Chrome, Edge, Brave and Opera).

Practice application forms built like the real Greenhouse, Lever, Ashby and Workable forms are served over
HTTPS on their real host names (the browser's resolver points those names at a local server), so the
extension runs exactly as it would on the real sites. radarak.online is served from a local copy of the site.

    SITE_DIR=path/to/site-copy python -m pytest tests/extension -v

SITE_DIR must be a copy of the published site (gh-pages) with the current site/app.js, style.css and
index.html copied over it.
"""
from __future__ import annotations

import hashlib
import http.server
import json
import os
import socketserver
import ssl
import subprocess
import threading
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
SITE_DIR = os.environ.get("SITE_DIR", "")
if not SITE_DIR:
    pytest.skip("set SITE_DIR to run the extension tests", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "extension"
PAGES = Path(__file__).resolve().parent / "pages"
HOSTS = ["radarak.online", "boards.greenhouse.io", "jobs.lever.co", "jobs.ashbyhq.com", "apply.workable.com",
         "careers.acme-example.com"]

CV_DE = """Ahmed Example - Data Engineer
Experience
2019 - Present  Data Engineer at Example Payments, Cairo
Built batch and streaming pipelines with Python, SQL, Apache Airflow, Apache Spark, dbt and Kafka on AWS.
Modelled the warehouse in PostgreSQL and Snowflake; CI/CD with Git and Docker.
Education
2014 - 2018 Bachelor of Computer Science
"""
CV_AN = """Ahmed Example - Data Analyst
Experience
2020 - Present  Data Analyst at Example Retail
Dashboards in Power BI and Tableau, reporting in Excel, queries in SQL. Presented insights to managers every week.
"""


def extension_id(path: Path) -> str:
    """Chrome's id for an unpacked extension: sha256 of its folder path, first 32 hex digits as a-p."""
    h = hashlib.sha256(str(path).encode()).hexdigest()[:32]
    return "".join(chr(ord("a") + int(c, 16)) for c in h)


class _Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def translate_path(self, path):
        host = (self.headers.get("Host") or "").split(":")[0]
        base = Path(SITE_DIR) if host == "radarak.online" else PAGES / host
        rel = path.split("?")[0].split("#")[0].lstrip("/")
        p = base / rel
        if p.is_dir():
            p = p / "index.html"
        elif not p.exists() and (base / (rel + ".html")).exists():
            p = base / (rel + ".html")
        return str(p)


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    d = tmp_path_factory.mktemp("tls")
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2", "-subj", "/CN=localhost",
                    "-keyout", str(d / "k.pem"), "-out", str(d / "c.pem")], check=True, capture_output=True)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(d / "c.pem", d / "k.pem")
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _Handler)
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()


@pytest.fixture(scope="module")
def browser_ctx(server, tmp_path_factory):
    rules = ", ".join(f"MAP {h} 127.0.0.1:{server}" for h in HOSTS)
    with pw.sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(tmp_path_factory.mktemp("profile")), channel="chromium", headless=True,
            ignore_https_errors=True, accept_downloads=True, viewport={"width": 1280, "height": 900}, timezone_id="Africa/Cairo",
            args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", f"--host-resolver-rules={rules}",
                  "--ignore-certificate-errors", "--no-proxy-server"])
        ctx.add_init_script("try { localStorage.setItem('jr_lang', JSON.stringify('en')); } catch (e) {}")
        yield ctx
        ctx.close()


@pytest.fixture(scope="module")
def kit_ready(browser_ctx, tmp_path_factory):
    """Fill the Apply kit on radarak.online (details + 2 CVs) and let the extension copy it."""
    d = tmp_path_factory.mktemp("cvs")
    (d / "data-engineer.txt").write_text(CV_DE)
    (d / "analyst.txt").write_text(CV_AN)
    p = browser_ctx.new_page()
    errors = []
    p.on("pageerror", lambda e: errors.append(str(e)))
    p.goto("https://radarak.online/#tab=kit")
    p.wait_for_selector("#kit:not([hidden]) #k-first", timeout=30000)
    for k, v in {"first": "Ahmed", "last": "Example", "email": "ahmed@example.com", "phone": "+20 100 000 0000",
                 "country": "Egypt", "city": "Cairo", "linkedin": "https://linkedin.com/in/ahmed",
                 "portfolio": "https://github.com/ahmed", "notice": "1 month", "salary": "40,000 EGP / month"}.items():
        p.fill(f"#k-{k}", v)
    for f in ("data-engineer.txt", "analyst.txt"):
        with p.expect_file_chooser() as fc:
            p.click("#kitAddCv")
        fc.value.set_files(str(d / f))
        p.wait_for_function(f"document.querySelectorAll('.kcv').length >= {1 if f.startswith('data') else 2}", timeout=15000)
    p.wait_for_timeout(1200)                         # the site pushes the kit to the extension
    yield p
    assert not errors, errors


def popup(ctx):
    pg = ctx.new_page()
    pg.goto(f"chrome-extension://{extension_id(EXT)}/popup.html")
    pg.wait_for_selector("#main :is(.ok, a, p)")
    return pg


def ext_storage(ctx):
    pg = ctx.new_page()
    pg.goto(f"chrome-extension://{extension_id(EXT)}/popup.html")
    data = pg.evaluate("chrome.storage.local.get(null)")
    pg.close()
    return data


def fill_click(page):
    btn = page.locator("#radarak-apply >> button.b")
    btn.wait_for(timeout=15000)
    btn.click()
    note = page.locator("#radarak-apply >> .n")
    note.wait_for(state="visible")
    return note.inner_text()


def file_name(page, sel):
    return page.eval_on_selector(sel, "el => el.files.length ? el.files[0].name : ''")


# ------------------------------------------------------------------------------------------ tests
def test_the_kit_is_copied_into_the_extension(browser_ctx, kit_ready):
    assert kit_ready.evaluate("document.documentElement.dataset.radarakExt") == "1"
    assert "extension connected" in kit_ready.locator(".kitext").inner_text()
    data = ext_storage(browser_ctx)
    assert data["kit"]["profile"]["first"] == "Ahmed" and len(data["kit"]["cvs"]) == 2
    assert len(data["files"]) == 2 and all(f["data"].startswith("data:") for f in data["files"].values())
    pg = popup(browser_ctx)
    assert "Kit ready for Ahmed: 2 CVs, 1 letter" in pg.inner_text("#main")
    if os.environ.get("SHOT_DIR"):
        pg.set_viewport_size({"width": 320, "height": 300})
        pg.screenshot(path=os.path.join(os.environ["SHOT_DIR"], "ext-popup.png"))
    pg.close()


def test_clicking_apply_on_radarak_remembers_the_job_and_best_cv(browser_ctx, kit_ready):
    jobs = json.loads((Path(SITE_DIR) / "data" / "jobs.json").read_text())
    job = next(j for j in jobs if j.get("r") == "Data Engineer" and len(j["k"]) >= 3 and j.get("c"))
    p = kit_ready
    p.goto("https://radarak.online/#job=" + job["id"])
    p.wait_for_selector("#drawerBody .dfit li.best")
    best_name = p.locator("#drawerBody .dfit li.best .fname").inner_text()
    apply = p.locator("#drawerBody a.apply")
    cv_id = apply.get_attribute("data-cv")
    assert cv_id
    apply.evaluate("a => { a.target = ''; a.href = 'javascript:void 0'; }")   # stay here; the real job site isn't needed
    apply.click()
    p.wait_for_timeout(300)
    pending = ext_storage(browser_ctx)["pending"]
    assert pending["cvId"] == cv_id and pending["title"] == job["t"] and pending["company"] == job["c"]
    assert job["c"] in pending["letter"]
    assert "Data Engineer CV" in best_name


def test_greenhouse_form(browser_ctx, kit_ready):
    p = browser_ctx.new_page()
    p.goto("https://boards.greenhouse.io/acme/jobs/4001")
    note = fill_click(p)
    assert "Filled" in note and "Data Engineer CV" in note
    v = lambda s: p.input_value(s)   # noqa: E731
    assert (v("#first_name"), v("#last_name"), v("#email"), v("#phone")) == ("Ahmed", "Example", "ahmed@example.com", "+20 100 000 0000")
    assert v("#q1") == "https://linkedin.com/in/ahmed" and v("#q2") == "https://github.com/ahmed" and v("#q3") == "1 month"
    assert p.eval_on_selector("#q4", "s => s.options[s.selectedIndex].text") == "5-7"        # 7 years from the CV
    assert file_name(p, "#resume") == "data-engineer.txt"                                   # the CV that fits best
    assert file_name(p, "#cover_letter") == "cover-letter.txt"
    # never guessed: how you heard, work authorisation, current company
    assert v("#q5") == "" and v("#q6") == "" and v("#q7") == ""
    assert p.eval_on_selector("#application_form", "f => f.dataset.submitted || ''") == ""   # nothing submitted
    if os.environ.get("SHOT_DIR"):
        p.screenshot(path=os.path.join(os.environ["SHOT_DIR"], "ext-greenhouse.png"), full_page=True)
    p.close()


def test_lever_form(browser_ctx, kit_ready):
    p = browser_ctx.new_page()
    p.goto("https://jobs.lever.co/acme/1234/apply")
    fill_click(p)
    v = lambda n: p.input_value(f"[name='{n}']")   # noqa: E731
    assert v("name") == "Ahmed Example" and v("email") == "ahmed@example.com" and v("phone") == "+20 100 000 0000"
    assert v("urls[LinkedIn]") == "https://linkedin.com/in/ahmed" and v("urls[GitHub]") == "https://github.com/ahmed"
    assert v("org") == ""                                                                  # current company: left alone
    assert file_name(p, "[name=resume]") in ("data-engineer.txt", "analyst.txt")
    letter = p.input_value("[name=comments]")
    assert "Acme" in letter and "{company}" not in letter and "Ahmed Example" in letter      # this company, not the last one
    p.close()


def test_ashby_single_page_app_keeps_the_values(browser_ctx, kit_ready):
    p = browser_ctx.new_page()
    p.goto("https://jobs.ashbyhq.com/acme/5678/application")
    p.wait_for_selector("#_systemfield_name")                                               # the form shows up late
    fill_click(p)
    state = json.loads(p.inner_text("#state"))
    s = state["state"]
    assert s["_systemfield_name"] == "Ahmed Example" and s["_systemfield_email"] == "ahmed@example.com"
    assert s["phone"] == "+20 100 000 0000" and s["linkedin"] == "https://linkedin.com/in/ahmed"
    assert s["location"] == "Cairo, Egypt" and s["salary"] == "40,000 EGP / month"           # no country field: "City, Country"
    assert "Acme" in s["cl"]
    assert state["files"]["resume"] in ("data-engineer.txt", "analyst.txt")                   # the app saw the file
    if os.environ.get("SHOT_DIR"):
        p.screenshot(path=os.path.join(os.environ["SHOT_DIR"], "ext-ashby.png"), full_page=True)
    p.close()


def test_workable_form(browser_ctx, kit_ready):
    p = browser_ctx.new_page()
    p.goto("https://apply.workable.com/acme/j/ABC123/apply")
    fill_click(p)
    v = lambda n: p.input_value(f"[name='{n}']")   # noqa: E731
    assert (v("firstname"), v("lastname"), v("email"), v("phone"), v("city")) == ("Ahmed", "Example", "ahmed@example.com", "+20 100 000 0000", "Cairo")
    assert v("country") == "EG" and v("QA_salary") == "40,000 EGP / month" and v("QA_notice") == "1 month"
    assert v("headline") == "" and v("pw") == ""
    assert file_name(p, "[name=resume]") != "" and "Acme" in v("cover_letter")
    p.close()


def test_greenhouse_inside_a_company_careers_page(browser_ctx, kit_ready):
    p = browser_ctx.new_page()
    p.goto("https://careers.acme-example.com/")
    frame = p.frame_locator("#grnhse_iframe")
    frame.locator("#radarak-apply >> button.b").click(timeout=15000)
    f = p.frame(url=lambda u: "boards.greenhouse.io/embed" in u)
    f.wait_for_function("document.querySelector('#email').value !== ''")
    assert f.input_value("#first_name") == "Ahmed" and f.input_value("#email") == "ahmed@example.com"
    assert f.eval_on_selector("#resume", "el => el.files.length") == 1
    p.close()


def test_no_button_on_other_sites_and_popup_fill_works_anywhere(browser_ctx, kit_ready):
    p = browser_ctx.new_page()
    p.goto("https://careers.acme-example.com/apply.html")
    p.wait_for_timeout(800)
    assert p.locator("#radarak-apply").count() == 0                                          # only where we were asked
    # "Fill this page" in the popup injects the same two files into the page (activeTab needs a real click on
    # the toolbar icon, which a test can't make), so run those files here with the extension's stored kit
    data = ext_storage(browser_ctx)
    p.evaluate("d => { window.chrome = { storage: { local: { get: async () => d } } }; }", data)
    p.add_script_tag(path=str(EXT / "src" / "common.js"))
    p.add_script_tag(path=str(EXT / "src" / "fill.js"))
    res = p.evaluate("() => window.__radarakFill({})")
    assert res["ok"] and set(res["filled"]) >= {"full", "email", "phone", "CV"}
    assert p.input_value("#nm") == "Ahmed Example" and p.input_value("#em") == "ahmed@example.com"
    assert p.input_value("#mob") == "+20 100 000 0000" and p.input_value("#co") == ""
    p.close()


def test_filling_twice_never_overwrites_your_answers(browser_ctx, kit_ready):
    p = browser_ctx.new_page()
    p.goto("https://boards.greenhouse.io/acme/jobs/4001")
    p.fill("#email", "other@example.com")
    fill_click(p)
    assert p.input_value("#email") == "other@example.com" and p.input_value("#first_name") == "Ahmed"
    p.locator("#radarak-apply >> button.b").click()
    assert p.input_value("#first_name") == "Ahmed"
    p.close()


def test_deleting_the_kit_on_radarak_clears_the_extension(browser_ctx, kit_ready):
    p = kit_ready
    p.goto("https://radarak.online/#tab=kit")
    p.wait_for_selector("#kitWipe")
    p.click("#kitWipe"); p.click("#kitWipe")
    p.wait_for_function("!document.querySelector('.kcv')")
    p.wait_for_timeout(1200)
    data = ext_storage(browser_ctx)
    assert not data["kit"]["cvs"] and not data["files"] and not any(data["kit"]["profile"].values())
    g = browser_ctx.new_page()
    g.goto("https://boards.greenhouse.io/acme/jobs/4001")
    note = fill_click(g)
    assert "Set up your Apply kit first" in note or "Nothing to fill" in note
    assert g.input_value("#first_name") == ""
    g.close()


def test_the_store_package_has_every_file():
    import zipfile
    import sys
    sys.path.insert(0, str(EXT))
    import build  # noqa: E402
    outs = build.build()
    names = set(zipfile.ZipFile(outs[0]).namelist())
    manifest = json.loads((EXT / "manifest.json").read_text())
    needed = {"manifest.json", manifest["action"]["default_popup"], *manifest["icons"].values()}
    for cs in manifest["content_scripts"]:
        needed |= set(cs["js"])
    assert needed <= names, needed - names
    assert outs[0].read_bytes() == outs[1].read_bytes()           # the download on radarak.online = the store upload
