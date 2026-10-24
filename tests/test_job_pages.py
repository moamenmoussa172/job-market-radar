"""One page per job (Google for Jobs), RSS feeds and the Telegram links."""
import datetime as dt
import json
import re
import xml.etree.ElementTree as ET

from jobradar import alerts, job_pages, seo_pages

LONG = "<p>" + "We build data pipelines with Spark and Airflow. " * 12 + "</p>"
META = {"skills": ["SQL", "Python", "Airflow", "React"],
        "tracks": [{"name": "Data & Analytics", "roles": ["Data Engineer", "Data Analyst"]}],
        "countries": [{"name": "Egypt", "region": "MENA"}, {"name": "Saudi Arabia", "region": "MENA"},
                      {"name": "Germany", "region": "Europe"}],
        "telegram": [{"u": "https://t.me/radarak_egypt", "pl": ["Egypt"]}, {"u": "https://t.me/radarak_remote", "pl": ["Remote"]}]}


def job(i, w="Onsite", co=("Egypt",), **kw):
    return {"id": f"a{i:011d}", "t": f"Data Engineer {i}", "c": "AMAN", "tr": "Data & Analytics", "r": "Data Engineer",
            "s": "Mid", "w": w, "l": "Cairo, Egypt", "co": list(co), "rg": [], "p": "2026-10-19",
            "u": f"https://careers.example.com/{i}", "k": [0, 1, 2], **kw}


def site(today=dt.date(2026, 10, 20)):
    jobs = [job(i) for i in range(6)] + [job(10 + i, w="Remote", co=(), rg=["MENA"]) for i in range(5)] + [job(20)]
    details = {j["id"]: (LONG, "Full-time") for j in jobs}
    details.pop(jobs[-1]["id"])                       # job 20: no description from its source -> no page
    job_pages.give_pages(jobs, details, 100, job_pages.region_map(META))
    meta = json.loads(json.dumps(META))
    return jobs, meta, seo_pages.seo_files(jobs, meta, "https://radarak.online/", today)


def ld(page: str) -> list:
    raw = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S).group(1)
    return json.loads(raw.replace("<\\/", "</"))


# ------------------------------------------------------------------------------------------ descriptions
def test_description_keeps_structure_and_drops_the_rest():
    raw = ("&lt;h2&gt;About&lt;/h2&gt;&lt;div&gt;&lt;p&gt;Build &lt;b&gt;pipelines&lt;/b&gt;.&lt;/p&gt;&lt;/div&gt;"
           "&lt;ul&gt;&lt;li&gt;SQL&lt;/li&gt;&lt;li&gt;&lt;a href='http://x'&gt;Python&lt;/a&gt;&lt;/li&gt;&lt;/ul&gt;"
           "&lt;script&gt;alert(1)&lt;/script&gt;&lt;img src=x onerror=alert(1)&gt;")
    out, chars = job_pages.clean_description(raw)
    assert out == "<p><strong>About</strong></p><p>Build <strong>pipelines</strong>.</p><ul><li>SQL</li><li>Python</li></ul>"
    assert chars == 29
    assert "script" not in out and "href" not in out and "onerror" not in out


def test_plain_text_lines_become_paragraphs_and_text_is_escaped():
    out, _ = job_pages.clean_description("Line one <3\n\nLine two & more")
    assert out == "<p>Line one &lt;3</p><p>Line two &amp; more</p>"
    out2, _ = job_pages.clean_description("First\nSecond")
    assert out2 == "<p>First</p><p>Second</p>"


def test_broken_markup_and_huge_descriptions():
    out, _ = job_pages.clean_description("<p>open <b>bold <i>both</p><li>stray item")
    assert out == "<p>open <strong>bold <em>both</em></strong></p><ul><li>stray item</li></ul>"
    big = "".join(f"<p>{'x' * 990} {i}</p>" for i in range(40))
    out, chars = job_pages.clean_description(big)
    assert chars > job_pages.MAX_DESCRIPTION_CHARS and len(re.sub("<[^>]*>", "", out)) <= job_pages.MAX_DESCRIPTION_CHARS + 1000


# ------------------------------------------------------------------------------------------ which jobs
def test_only_jobs_with_a_description_and_a_country_get_a_page():
    jobs, _, f = site()
    with_page = [j for j in jobs if j.get("pg")]
    assert len(with_page) == 11 and not jobs[-1].get("pg")
    assert jobs[0]["pg"] == "job/data-engineer-0-at-aman-a00000000000/"
    assert "job/data-engineer-0-at-aman-a00000000000/index.html" in f
    ww = [job(1, w="Remote", co=(), ww=1, rg=["Worldwide"])]          # remote anywhere: Google needs a country
    assert job_pages.give_pages(ww, {ww[0]["id"]: (LONG, None)}, 10, job_pages.region_map(META)) == 0
    short = [job(2)]
    assert job_pages.give_pages(short, {short[0]["id"]: ("<p>Apply now</p>", None)}, 10) == 0
    many = [job(i) for i in range(5)]
    assert job_pages.give_pages(many, {j["id"]: (LONG, None) for j in many}, 3) == 3   # JOB_PAGES_MAX


def test_attach_details_without_a_warehouse_is_harmless():
    assert job_pages.attach_details(None, [job(1)], META, limit=10) == 0


# ------------------------------------------------------------------------------------------ the page
def test_job_page_has_valid_jobposting_markup():
    _, _, f = site()
    page = f["job/data-engineer-0-at-aman-a00000000000/index.html"].decode()
    posting, crumbs = ld(page)
    assert posting["@type"] == "JobPosting" and posting["title"] == "Data Engineer 0"
    assert posting["hiringOrganization"]["name"] == "AMAN" and posting["datePosted"] == "2026-10-19"
    assert posting["jobLocation"][0]["address"] == {"@type": "PostalAddress", "addressCountry": "Egypt",
                                                   "addressLocality": "Cairo"}
    assert posting["employmentType"] == "FULL_TIME" and "jobLocationType" not in posting
    assert "Spark and Airflow" in posting["description"] and posting["description"] in page.replace("<p><b>", "<p>")
    assert crumbs["@type"] == "BreadcrumbList"
    assert '<link rel="canonical" href="https://radarak.online/job/data-engineer-0-at-aman-a00000000000/">' in page
    assert 'href="https://careers.example.com/0"' in page and "Apply on AMAN's site" in page
    assert 'href="../../#job=a00000000000"' in page                     # open in the app
    assert 'href="../../jobs/egypt/data-engineer/"' in page               # similar jobs
    assert "hreflang" not in page and "https://t.me/radarak_egypt" in page


def test_remote_job_is_telecommute_open_to_the_region():
    jobs, _, f = site()
    page = f[jobs[6]["pg"] + "index.html"].decode()
    posting = ld(page)[0]
    assert posting["jobLocationType"] == "TELECOMMUTE" and "jobLocation" not in posting
    assert [c["name"] for c in posting["applicantLocationRequirements"]] == ["Egypt", "Saudi Arabia"]
    assert "fully remote job, open to people in MENA" in posting["description"]
    assert "https://t.me/radarak_remote" in page


def test_job_pages_do_not_change_from_day_to_day():
    a = site(dt.date(2026, 10, 20))[2]
    b = site(dt.date(2026, 10, 27))[2]
    pages = [k for k in a if k.startswith("job/")]
    assert pages and all(a[k] == b[k] for k in pages)


def test_lists_link_to_job_pages_and_sitemap_lists_them():
    jobs, _, f = site()
    country = f["jobs/egypt/index.html"].decode()
    assert 'href="../../job/data-engineer-0-at-aman-a00000000000/"' in country
    sm = f["sitemap-jobs.xml"].decode()
    ET.fromstring(sm)
    assert sm.count("<url>") == 11 and "<lastmod>2026-10-19</lastmod>" in sm
    assert "Sitemap: https://radarak.online/sitemap-jobs.xml" in f["robots.txt"].decode()


# ------------------------------------------------------------------------------------------ alerts
def test_telegram_links_only_for_public_channels():
    links = alerts.telegram_links("@radarak_egypt=Egypt;-1001234=Egypt;@radarak_gulf=Saudi Arabia|Qatar;bad")
    assert links == [{"u": "https://t.me/radarak_egypt", "pl": ["Egypt"]},
                     {"u": "https://t.me/radarak_gulf", "pl": ["Saudi Arabia", "Qatar"]}]
    assert alerts.telegram_links("") == []


def test_telegram_links_from_env_need_the_bot(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHANNELS", "@radarak_egypt=Egypt")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert alerts.telegram_links() == []                       # nothing posts there yet: don't link to it
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    assert alerts.telegram_links() == [{"u": "https://t.me/radarak_egypt", "pl": ["Egypt"]}]


def test_rss_feeds_for_country_and_track_pages():
    _, meta, f = site()
    assert meta["feeds"]["Egypt"] == "feeds/egypt.xml" and meta["feeds"]["Remote"] == "feeds/remote.xml"
    assert meta["feeds"]["Egypt|data-and-analytics"] == "feeds/egypt/data-and-analytics.xml"
    root = ET.fromstring(f["feeds/egypt.xml"])
    items = root.findall("./channel/item")
    links = [i.find("link").text for i in items]
    assert len(items) == 7 and links[0] == "https://radarak.online/#job=a00000000020"     # no page: opens in the app
    assert all(u.startswith("https://radarak.online/job/") for u in links[1:])
    assert root.find("./channel/title").text == "Tech jobs in Egypt"
    country = f["jobs/egypt/index.html"].decode()
    assert 'type="application/rss+xml"' in country and "https://radarak.online/feeds/egypt.xml" in country
    assert "https://t.me/radarak_egypt" in country and "data-alerts" in country
    ar = f["ar/jobs/egypt/index.html"].decode()
    assert "تيليجرام" in ar


def test_no_alerts_row_without_channels_or_feeds():
    assert alerts.alerts_block("Germany", {"telegram": [], "feeds": {}}, "../", "en") == ""
