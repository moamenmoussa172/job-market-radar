"""Typical pay (Glassdoor salary estimates) and company ratings."""
import datetime as dt

from jobradar import enrich, extra_pages

# shapes copied from real OpenWeb Ninja answers (Cairo data engineer, Paymob search)
SALARY_ANSWER = {"status": "OK", "data": [{
    "location": "Cairo Governorate", "job_title": "Data Engineer", "min_salary": 14187.5, "max_salary": 33750,
    "median_salary": 22250, "min_base_salary": 13000, "max_base_salary": 25000, "median_base_salary": 18500,
    "salary_period": "MONTH", "salary_currency": "EGP", "salary_count": 228,
    "salaries_updated_at": "2026-01-11T04:56:02.000Z", "publisher_name": "Glassdoor",
    "publisher_link": "https://www.glassdoor.com/Salaries/x.htm", "confidence": "HIGH"}]}
SEARCH_ANSWER = {"status": "OK", "data": [
    {"company_id": 1, "name": "Paymobile Systems", "rating": 4.5, "review_count": 3},
    {"company_id": 1350548, "name": "PayMob", "company_link": "https://www.glassdoor.com/Overview/Working-at-PayMob.htm",
     "rating": 3.2, "review_count": 149, "headquarters_location": "Cairo, Egypt", "company_size": "501 to 1000 Employees",
     "logo": "https://media.glassdoor.com/x.png", "company_description": "long text"}]}


def test_salary_answer_is_kept_small_and_rounded():
    e = enrich.parse_salary(SALARY_ANSWER)
    assert e == {"min": 14188, "median": 22250, "max": 33750, "base_median": 18500, "currency": "EGP", "period": "MONTH",
                 "count": 228, "updated": "2026-01-11", "location": "Cairo Governorate",
                 "link": "https://www.glassdoor.com/Salaries/x.htm", "confidence": "HIGH"}
    assert enrich.parse_salary({"status": "OK", "data": []}) is None
    assert enrich.parse_salary({"data": [{"median_salary": 0}]}) is None


def test_job_city_from_location_or_the_countrys_main_city():
    assert enrich.job_city("New Cairo, Cairo Governorate, Egypt", ["Egypt"], "Onsite") == "Cairo"
    assert enrich.job_city("Smart Village, Giza", ["Egypt"], "Hybrid") == "Cairo"
    assert enrich.job_city("Alexandria, Egypt", ["Egypt"], "Onsite") == "Alexandria"
    assert enrich.job_city("Egypt", ["Egypt"], "Onsite") == "Cairo"
    assert enrich.job_city("Jeddah, Saudi Arabia", ["Saudi Arabia"], "Onsite") == "Jeddah"
    assert enrich.job_city("Abu Dhabi", ["United Arab Emirates"], "Onsite") == "Abu Dhabi"
    assert enrich.job_city("Remote", ["Egypt"], "Remote") is None              # no city pay for remote jobs
    assert enrich.job_city("Berlin", ["Germany"], "Onsite") is None
    assert enrich.job_city("Cairo or Dubai", ["Egypt", "United Arab Emirates"], "Onsite") == "Cairo"
    assert enrich.job_city("Several places", ["Egypt", "United Arab Emirates"], "Onsite") is None


def test_roles_map_to_one_search_title():
    assert enrich.pay_query("Data Engineer") == "Data Engineer"
    assert enrich.pay_query("Analytics Engineer") == "Data Engineer"
    assert enrich.pay_query("iOS Engineer") == "Mobile Developer"
    assert enrich.pay_query("Engineering Leadership") is None                    # no fair estimate for managers of engineers
    assert enrich.pay_query(None) is None


def test_company_match_is_strict():
    hit = enrich.match_company("Paymob", SEARCH_ANSWER["data"])
    assert hit["company_id"] == 1350548                                         # not "Paymobile Systems"
    r = enrich.parse_rating(hit)
    assert r == {"rating": 3.2, "reviews": 149, "name": "PayMob", "link": "https://www.glassdoor.com/Overview/Working-at-PayMob.htm",
                 "hq": "Cairo, Egypt", "size": "501 to 1000 Employees"}
    assert "logo" not in r and "company_description" not in r                    # never stored
    assert enrich.match_company("Vodafone Egypt", [{"name": "Vodafone"}]) == {"name": "Vodafone"}
    assert enrich.match_company("Valeo", [{"name": "Valeant Pharmaceuticals"}]) is None
    assert enrich.match_company("AMAN Holding", [{"name": "Amanah"}]) is None
    assert enrich.match_company("", [{"name": "x"}]) is None


ESTIMATES = [
    {"q": "Data Engineer", "city": "Cairo", "co": "Egypt", "cur": "EGP", "per": "MONTH", "lo": 14188, "md": 22250,
     "hi": 33750, "n": 228, "up": "2026-01", "u": "https://www.glassdoor.com/Salaries/x.htm"},
    {"q": "Data Engineer", "city": "Riyadh", "co": "Saudi Arabia", "cur": "SAR", "per": "MONTH", "lo": 10625, "md": 12808,
     "hi": 21150, "n": 54, "up": "2024-07", "u": None},
]


def test_estimates_go_on_office_jobs_without_published_pay():
    jobs = [
        {"id": "a", "r": "Data Engineer", "l": "Maadi, Cairo", "co": ["Egypt"], "w": "Onsite"},
        {"id": "b", "r": "Data Engineer", "l": "Alexandria", "co": ["Egypt"], "w": "Onsite"},    # falls back to Cairo
        {"id": "c", "r": "Data Engineer", "l": "Cairo", "co": ["Egypt"], "w": "Onsite", "$": [20, 30]},  # has real pay
        {"id": "d", "r": "Data Engineer", "l": "Remote", "co": ["Egypt"], "w": "Remote"},
        {"id": "e", "r": "Data Analyst", "l": "Cairo", "co": ["Egypt"], "w": "Onsite"},           # no estimate yet
        {"id": "f", "r": "Data Engineer", "l": "Riyadh", "co": ["Saudi Arabia"], "w": "Hybrid"},
    ]
    assert enrich.attach_estimates(jobs, ESTIMATES) == 3
    assert [j.get("pe") for j in jobs] == [0, 0, None, None, None, 1]


def test_run_without_a_key_does_nothing(monkeypatch):
    monkeypatch.delenv("OPENWEBNINJA_API_KEY", raising=False)
    monkeypatch.delenv("JSEARCH_API_KEY", raising=False)
    assert enrich.run(conn=None) == {"skipped": "OPENWEBNINJA_API_KEY not set"}


def test_salary_page_shows_estimates_by_city_in_local_currency():
    html = extra_pages.estimates_block(ESTIMATES, "en")
    assert "Typical monthly pay in Egypt &amp; the Gulf" in html
    assert html.index("Cairo") < html.index("Riyadh")                          # more salaries behind it first
    assert "<b>22,250</b> EGP" in html and "14,188 – 33,750" in html and "Updated: 2024-07" in html
    assert "Glassdoor" in html
    ar = extra_pages.estimates_block(ESTIMATES, "ar")
    assert "القاهرة" in ar and "الرياض" in ar
    only_sa = extra_pages.estimates_block(ESTIMATES, "en", "Saudi Arabia")
    assert "Riyadh" in only_sa and "Cairo" not in only_sa
    assert extra_pages.estimates_block([], "en") == ""


def _company_jobs(n=3):
    return [{"id": f"p{i}", "t": f"Data Engineer {i}", "c": "Paymob", "tr": "Data & Analytics", "r": "Data Engineer",
             "s": "Mid", "w": "Onsite", "l": "Cairo", "co": ["Egypt"], "rg": [], "p": "2026-10-30",
             "u": f"https://x/{i}", "k": []} for i in range(n)]


def test_rating_shows_on_the_company_page_only():
    meta = {"skills": [], "pay_est": ESTIMATES, "_ratings": {"Paymob": {"rating": 3.2, "reviews": 149,
                                                                        "link": "https://www.glassdoor.com/o"}}}
    files, _ = extra_pages.extra_files(_company_jobs(), meta, "https://radarak.online/", dt.date(2026, 10, 31), {})
    page = files["companies/paymob/index.html"].decode()
    assert "3.2 / 5 on Glassdoor" in page and "from 149 employee reviews" in page and 'href="https://www.glassdoor.com/o"' in page
    assert "3.2 من 5 على Glassdoor" in files["ar/companies/paymob/index.html"].decode()
    sal = files["salaries/index.html"].decode()
    assert "Typical monthly pay" in sal and "Glassdoor" not in files["companies/index.html"].decode()
    meta["_ratings"] = {}
    files, _ = extra_pages.extra_files(_company_jobs(), meta, "https://radarak.online/", dt.date(2026, 10, 31), {})
    assert "Glassdoor" not in files["companies/paymob/index.html"].decode()
