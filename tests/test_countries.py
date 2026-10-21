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
