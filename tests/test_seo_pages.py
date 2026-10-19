"""Pages for search engines: which pages exist, what they say, and the sitemap."""
import datetime as dt
import re

from jobradar import seo_pages, site_export

META = {"skills": ["SQL", "Python", "Airflow", "React"],
        "tracks": [{"name": "Data & Analytics", "roles": ["Data Engineer", "Data Analyst"]},
                   {"name": "Software Engineering", "roles": ["Frontend Engineer"]}],
        "countries": [{"name": "Egypt", "region": "MENA"}, {"name": "Germany", "region": "Europe"}]}


def job(i, role="Data Engineer", track="Data & Analytics", co=("Egypt",), w="Onsite", company=None, **kw):
    return {"id": f"j{i}", "t": f"{role} {i}", "c": company or f"Co{i % 4}", "tr": track, "r": role, "s": "Mid", "w": w,
            "l": "Cairo, Egypt", "co": list(co), "rg": [], "p": "2026-10-19", "u": f"https://jobs.example.com/{i}",
            "k": [0, 1, 2] if track == "Data & Analytics" else [3], **kw}


JOBS = ([job(i) for i in range(6)] + [job(10 + i, role="Data Analyst") for i in range(2)]          # 2 analysts: too few
        + [job(20 + i, role="Frontend Engineer", track="Software Engineering") for i in range(4)]   # 4: too few
        + [job(30 + i, w="Remote", co=(), rg=["MENA"]) for i in range(5)]                            # remote, open to MENA
        + [job(40, co=("Germany",))])


def files():
    return seo_pages.seo_files(JOBS, META, "https://radarak.online/", dt.date(2026, 10, 20))


def test_pages_exist_only_where_there_are_enough_jobs():
    f = files()
    assert "jobs/egypt/index.html" in f and "ar/jobs/egypt/index.html" in f
    assert "jobs/egypt/data-engineer/index.html" in f and "jobs/egypt/frontend-engineer/index.html" not in f
    assert "jobs/egypt/data-and-analytics/index.html" in f                      # 8 data jobs: a track page
    assert "jobs/egypt/data-analyst/index.html" not in f                        # 2 jobs: too thin
    assert "jobs/egypt/software-engineering/index.html" not in f                # 4 < MIN_TRACK_JOBS
    assert "jobs/germany/index.html" not in f                                   # 1 job
    assert "jobs/remote/index.html" in f and "jobs/index.html" in f and "ar/jobs/index.html" in f


def test_role_page_says_what_google_and_people_need():
    page = files()["jobs/egypt/data-engineer/index.html"].decode()
    assert "<title>Data Engineer jobs in Egypt (6 open) | Radarak</title>" in page
    assert '<link rel="canonical" href="https://radarak.online/jobs/egypt/data-engineer/">' in page
    assert 'hreflang="ar" href="https://radarak.online/ar/jobs/egypt/data-engineer/"' in page
    assert '"@type": "BreadcrumbList"' in page and "https://radarak.online/jobs/egypt/" in page
    assert 'href="../../../#job=j0"' in page                                    # opens the job in the app
    assert 'rel="nofollow noopener"' in page and "https://jobs.example.com/0" in page
    assert "Top skills: SQL, Python and Airflow" in page
    assert "Plus 5 remote jobs open to people in Egypt" in page                 # why the app shows more
    assert 'href="../../../#country=Egypt&amp;role=role%3AData%20Engineer"' in page


def test_arabic_page_is_right_to_left_and_translated():
    page = files()["ar/jobs/egypt/data-engineer/index.html"].decode()
    assert '<html lang="ar" dir="rtl">' in page and "وظايف Data Engineer في مصر" in page
    assert 'href="../../../../#job=j0"' in page                                 # one level deeper than English


def test_text_from_job_boards_is_escaped():
    bad = [job(i, company='<script>alert(1)</script>') for i in range(5)]
    page = seo_pages.seo_files(bad, META, "https://x.dev/")["jobs/egypt/data-engineer/index.html"].decode()
    assert "<script>alert" not in page and "&lt;script&gt;" in page


def test_sitemap_and_robots():
    f = files()
    sm = f["sitemap.xml"].decode()
    locs = re.findall(r"<loc>(.*?)</loc>", sm)
    assert locs[0] == "https://radarak.online/" and "https://radarak.online/ar/jobs/egypt/data-engineer/" in locs
    pages = [k for k in f if k.endswith("index.html") and k not in ("jobs/index.html", "ar/jobs/index.html")]
    assert len(locs) == len(pages) + 4                                          # + home, 2 indexes, report
    assert f["robots.txt"].decode().endswith("Sitemap: https://radarak.online/sitemap.xml\n")


def test_slugs_are_clean_and_unique():
    assert seo_pages.slug("ML / AI Engineer") == "ml-ai-engineer"
    assert seo_pages.slug("C# / .NET Developer") == "csharp-dotnet-developer"
    assert seo_pages.slug("Data & Analytics") == "data-and-analytics"


def test_published_pages_get_analytics_and_the_base_url(monkeypatch):
    monkeypatch.setenv("SITE_DOMAIN", "radarak.online")
    monkeypatch.setenv("GOATCOUNTER_CODE", "radarak")
    assert site_export.site_base_url() == "https://radarak.online/"
    monkeypatch.setattr(site_export, "export_site_data", lambda conn: {
        "data/jobs.json": site_export.json.dumps(JOBS).encode(), "data/meta.json": site_export.json.dumps(META).encode()})
    f = site_export.all_site_files(conn=None)
    assert b"goatcounter" in f["jobs/egypt/index.html"] and b"https://radarak.online/jobs/egypt/" in f["jobs/egypt/index.html"]
    assert "sitemap.xml" in f and "index.html" in f and f["CNAME"] == b"radarak.online\n"
