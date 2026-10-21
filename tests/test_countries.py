"""New countries: geo patterns place locations correctly; extra countries get searched without raising the API budget."""
import csv
import datetime as dt
import re
from pathlib import Path

from jobradar import seo_pages, sources

ROOT = Path(__file__).resolve().parents[1]


def _match(text: str) -> set[str]:
    rows = csv.DictReader((ROOT / "dbt/seeds/geo_patterns.csv").open(encoding="utf-8"))
    out = set()
    for r in rows:
        if r["country"] and re.search(r["pattern"].replace(r"\m", r"\b").replace(r"\M", r"\b"), text, re.I):
            out.add(r["country"])
    if re.search(r"\b(tbilisi|batumi)\b", text, re.I):
        out.discard("United States")  # same rule as int_posting_geo.sql
    return out


def test_new_countries_match():
    cases = {
        "Algiers, Algeria": "Algeria", "Erbil, Iraq": "Iraq", "Dhaka, Bangladesh": "Bangladesh",
        "Almaty": "Kazakhstan", "Bratislava, Slovakia": "Slovakia", "Tirana": "Albania",
        "Reykjavík": "Iceland", "Tbilisi, Georgia": "Georgia", "Kigali, Rwanda": "Rwanda",
        "Abidjan": "Ivory Coast", "الجزائر": "Algeria", "صنعاء": "Yemen", "Lucerne": "Switzerland",
        "King Abdullah Economic City, 02": "Saudi Arabia", "Mississauga, ON, CA": "Canada",
    }
    for text, country in cases.items():
        assert _match(text) == {country}, (text, _match(text))


def test_no_false_countries():
    assert _match("Benin City, Nigeria") == {"Nigeria"}
    assert _match("Stuttgart, Baden-Württemberg") == {"Germany"}
    assert _match("Atlanta, Georgia") == {"United States"}
    assert _match("Bogotá, CO") == {"Colombia"}


def test_every_country_has_code_region_and_arabic_name():
    rows = list(csv.DictReader((ROOT / "dbt/seeds/geo_patterns.csv").open(encoding="utf-8")))
    countries = {r["country"] for r in rows if r["country"] and r["region"]}
    codes = {r["country"] for r in csv.DictReader((ROOT / "dbt/seeds/country_codes.csv").open(encoding="utf-8"))}
    missing_ar = countries - set(seo_pages.AR_PLACES)
    assert not missing_ar, missing_ar
    assert {"Algeria", "Iraq", "Bangladesh", "Georgia", "Slovakia"} <= countries & codes


def test_extra_countries_share_the_same_budget():
    day = dt.date(2026, 10, 21)
    js = sources.jsearch_today(day)
    assert len(js) == sources.JSEARCH_PER_DAY
    extra = {c for c, _ in sources.EXTRA_SEARCH_COUNTRIES}
    assert sum(1 for _, code, _ in js if code in extra) == sources.JSEARCH_EXTRA_PER_DAY
    assert len(sources.jooble_today(day)) == sources.JOOBLE_PER_DAY
    # consecutive days visit different extra countries
    seen = {sources.jsearch_today(day + dt.timedelta(d))[-1][1] for d in range(10)}
    assert len(seen) == 10


def test_dropped_connection_is_retried_then_skipped(monkeypatch):
    import requests
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise requests.ConnectionError("Remote end closed connection without response")

    monkeypatch.setattr(sources.requests, "get", boom)
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    res = sources.extract_bundesagentur(queries=["Data Engineer"], pages=1)
    assert res.records == [] and "ConnectionError" in res.warnings[0]
    assert len(calls) == sources.CONNECT_RETRIES + 1


def test_reruns_on_the_same_day_do_not_spend_quota_again(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "BUDGET_FILE", tmp_path / "budget.json")
    day = dt.date(2026, 10, 21)
    assert sources.budget_left("jsearch", 6, 190, day) == 6
    sources.budget_spend("jsearch", 6, day)
    assert sources.budget_left("jsearch", 6, 190, day) == 0          # rerun same day: nothing left
    assert sources.budget_left("jsearch", 6, 190, day + dt.timedelta(1)) == 6   # next day: fresh
    sources.budget_spend("jsearch", 183, day + dt.timedelta(1))
    assert sources.budget_left("jsearch", 6, 190, day + dt.timedelta(2)) == 1   # month cap
    assert sources.budget_left("jsearch", 6, 190, dt.date(2026, 11, 1)) == 6    # new month


def test_jsearch_skips_when_budget_used(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "BUDGET_FILE", tmp_path / "budget.json")
    monkeypatch.setenv("JSEARCH_API_KEY", "x")
    sources.budget_spend("jsearch", sources.JSEARCH_PER_DAY)
    monkeypatch.setattr(sources.requests, "get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no call")))
    res = sources.extract_jsearch()
    assert res.records == [] and "budget" in res.warnings[0]


def test_remoteok_skips_legal_notice_and_non_tech(monkeypatch):
    feed = [{"last_updated": 1, "legal": "API Terms of Service: link back to the URL on Remote OK ..."},
            {"id": "1", "position": "Senior Data Engineer", "company": "Acme", "url": "https://remoteok.com/remote-jobs/1",
             "location": "Worldwide", "salary_min": 0, "salary_max": 0},
            {"id": "2", "position": "Construction Estimator", "company": "B", "url": "https://remoteok.com/remote-jobs/2"}]
    monkeypatch.setattr(sources, "_get_json", lambda url, **k: feed)
    res = sources.extract_remoteok()
    assert [r["id"] for r in res.records] == ["1"]
    assert sources.remoteok_id(res.records[0]) == "1"


def test_remoteok_links_are_followed_and_credited():
    from jobradar import site_export
    assert "remoteok" in site_export.DOFOLLOW_SOURCES and site_export.SOURCE_CREDITS["remoteok"] == "via Remote OK"
    html = seo_pages._job_li({"id": "x", "t": "Data Engineer", "c": "Acme", "u": "https://remoteok.com/remote-jobs/1",
                              "df": 1, "k": []}, "/", "en", dt.date(2026, 10, 22), [])
    assert 'rel="noopener"' in html and "nofollow" not in html
    other = seo_pages._job_li({"id": "y", "t": "Data Engineer", "c": "Acme", "u": "https://x.com", "k": []},
                              "/", "en", dt.date(2026, 10, 22), [])
    assert "nofollow" in other


def test_adzuna_covers_all_its_countries_and_currencies():
    sql = (ROOT / "dbt/models/staging/stg_adzuna.sql").read_text()
    for c in sources.ADZUNA_COUNTRIES:
        assert c in ("de", "nl", "fr", "es", "it", "at", "be") or f"'{c}' then" in sql, c


def test_new_companies_have_country_keywords():
    from jobradar import boards
    rows = csv.DictReader((ROOT / "dbt/seeds/companies.csv").open(encoding="utf-8"))
    countries = {r["country"] for r in rows} - {"Global", "Remote"}
    assert countries <= set(boards.COUNTRY_KEYWORDS), countries - set(boards.COUNTRY_KEYWORDS)
