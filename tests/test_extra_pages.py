"""Company pages, juniors corner, salary guide, newsletter (Buttondown mocked) and the signup box."""
import datetime as dt

from jobradar import extra_pages, newsletter, seo_pages, site_export

META = {"skills": ["SQL", "Python", "Airflow", "React"],
        "tracks": [{"name": "Data & Analytics", "roles": ["Data Engineer"]}],
        "countries": [{"name": "Egypt", "region": "MENA"}]}
TODAY = dt.date(2026, 10, 25)   # a Sunday


def job(i, company="Valeo", s="Mid", pay=None, co=("Egypt",), w="Onsite", p="2026-10-24", **kw):
    j = {"id": f"j{i}", "t": f"Data Engineer {i}", "c": company, "tr": "Data & Analytics", "r": "Data Engineer", "s": s,
         "w": w, "l": "Cairo, Egypt", "co": list(co), "rg": [], "p": p, "u": f"https://x.example/{i}", "k": [0, 1, 2], **kw}
    if pay:
        j["$"] = pay
    return j


JOBS = ([job(i) for i in range(4)] + [job(10 + i, company="Fawry", s="Junior") for i in range(2)]
        + [job(20 + i, company=f"Solo{i}", pay=[30 + i, 40 + i]) for i in range(6)]
        + [job(40, company="Old Co", p="2026-09-01")])


def pages():
    return seo_pages.seo_files(JOBS, META, "https://radarak.online/", TODAY)


def test_company_pages_only_for_companies_with_enough_jobs():
    f = pages()
    assert "companies/valeo/index.html" in f and "ar/companies/valeo/index.html" in f
    assert "companies/fawry/index.html" not in f                                  # 2 jobs
    page = f["companies/valeo/index.html"].decode()
    assert "<title>Valeo tech jobs (4 open) | Radarak</title>" in page and 'href="../../#q=Valeo"' in page
    assert 'href="../../companies/valeo/"' in f["jobs/egypt/index.html"].decode()  # role pages link to companies
    assert "companies/index.html" in f and "Valeo" in f["companies/index.html"].decode()


def test_juniors_corner_lists_only_entry_level_jobs():
    page = pages()["juniors/index.html"].decode()
    assert "2 intern and junior jobs at 1 companies" in page and 'href="../#junior=1"' in page
    assert "Data Engineer 10" in page and "Data Engineer 0<" not in page


def test_salary_guide_needs_enough_published_pay():
    f = pages()
    page = f["salaries/index.html"].decode()
    assert "Data Engineer" in page and "$38k" in page and "From 6 jobs that publish pay" in page
    assert "salaries/egypt/index.html" not in f                                   # 6 < MIN_SALARY_PLACE
    few = seo_pages.seo_files(JOBS[:6], META, "https://radarak.online/", TODAY)["salaries/index.html"].decode()
    assert "Not enough jobs publish pay here yet." in few


def test_new_pages_are_in_the_sitemap_and_menu():
    f = pages()
    sm = f["sitemap.xml"].decode()
    for u in ("companies/valeo/", "ar/companies/valeo/", "juniors/", "ar/salaries/"):
        assert f"https://radarak.online/{u}</loc>" in sm, u
    assert 'href="../../juniors/"' in f["jobs/egypt/index.html"].decode()


def test_digest_covers_the_week_by_place():
    subject, body = newsletter.build_digest(JOBS, META, "https://radarak.online/", TODAY)
    assert subject == "Radarak Weekly: 12 new tech jobs (19–25 Oct)"             # the September job is old
    assert "### Egypt: 12 new jobs" in body and "[See all Egypt jobs →](https://radarak.online/jobs/egypt/)" in body
    assert "](https://radarak.online/#job=j20), Solo0 · $30k–$40k" in body          # jobs with pay first
    assert "2 new intern and junior jobs" in body and "Most asked skills this week:** SQL, Python, Airflow" in body


class _Conn:
    def __init__(self):
        self.sent = set()

    def cursor(self):
        conn = self

        class C:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def execute(self, sql, params=None):
                self.row = None
                if sql.startswith("select 1"):
                    self.row = (1,) if params[0] in conn.sent else None
                elif sql.startswith("insert"):
                    conn.sent.add(params[0])

            def fetchone(self):
                return self.row
        return C()

    def commit(self):
        pass


def test_newsletter_is_created_once_per_week_on_newsletter_day(monkeypatch):
    posts = []

    class R:
        status_code = 201

        def json(self):
            return {"id": "em_1"}
    monkeypatch.setattr(newsletter.requests, "post", lambda url, **kw: posts.append((url, kw)) or R())
    monkeypatch.setenv("BUTTONDOWN_API_KEY", "KEY")
    monkeypatch.delenv("BUTTONDOWN_STATUS", raising=False)
    monkeypatch.delenv("NEWSLETTER_WEEKDAY", raising=False)
    conn = _Conn()
    assert "skipped" in newsletter.send_from_env(conn, JOBS, META, "https://radarak.online/", dt.date(2026, 10, 24))  # Saturday
    out = newsletter.send_from_env(conn, JOBS, META, "https://radarak.online/", TODAY)
    assert out["status"] == "draft" and out["id"] == "em_1"
    url, kw = posts[0]
    assert url == "https://api.buttondown.com/v1/emails" and kw["headers"]["Authorization"] == "Token KEY"
    assert kw["json"]["status"] == "draft" and kw["json"]["subject"].startswith("Radarak Weekly")
    assert newsletter.send_from_env(conn, JOBS, META, "https://radarak.online/", TODAY) == {"skipped": "already created this week"}
    monkeypatch.delenv("BUTTONDOWN_API_KEY")
    assert "skipped" in newsletter.send_from_env(conn, JOBS, META, "https://radarak.online/", TODAY)


def test_signup_box_appears_only_with_a_valid_newsletter_name():
    files = {"index.html": b'<section id="newsletter" data-bd="" hidden>',
             "jobs/egypt/index.html": b"<footer><!--newsletter:en--></footer>"}
    out = site_export.add_newsletter(dict(files), "radarak")
    assert b'data-bd="radarak"' in out["index.html"]
    assert b"embed-subscribe/radarak" in out["jobs/egypt/index.html"] and b"Radarak Weekly" in out["jobs/egypt/index.html"]
    assert site_export.add_newsletter(dict(files), "") == files
    assert site_export.add_newsletter(dict(files), 'x"><script>') == files


def test_job_lists_carry_filters_and_filter_data():
    f = pages()
    page = f["juniors/index.html"].decode()
    assert "data-filters" in page and 'data-f="t" data-mode="text"' in page
    assert 'data-f="co"' not in page                    # every junior job is in Egypt: a 1-option filter is left out
    assert 'data-co="Egypt"' in page and 'data-s="Junior"' in page and "data-ftoggle" in page
    assert 'src="../pages.js"' in page
    comp = f["companies/index.html"].decode()
    assert 'data-f="rem"' in comp and 'data-n="4"' in comp and 'data-co="Egypt"' in comp
    sal = f["salaries/index.html"].decode()
    assert 'data-list' in sal and 'data-f="t"' in sal and "data-goto" not in sal   # one place only: no switcher


def test_pages_script_is_published():
    files = site_export.site_files()
    assert "pages.js" in files and b"data-filters" in files["pages.js"]
