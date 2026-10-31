"""Typical pay and company ratings, from OpenWeb Ninja (key OPENWEBNINJA_API_KEY in .env).

* Job Salary Data API: a salary estimate for a job title in a city (data from Glassdoor). Few jobs in Egypt
  and the Gulf publish pay, so jobs without a salary show "typical pay for this role in this city".
* Real-Time Glassdoor Data API (company-search): a company's rating and review count, shown on its
  company page only (never in the job list). Review text and logos are never stored or shown.

Both free plans are small (50 and 100 requests a month), so every run asks for only a few new answers,
most useful first (the role/city pairs and companies with the most open jobs), and keeps them for months
in raw.salary_estimates / raw.company_ratings. Budgets are counted with the same file as JSearch.
Nothing here ever fails the pipeline: without a key, or when the API is down, the site keeps what it has.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
from collections import Counter

import requests

from jobradar.sources import budget_left, budget_spend

log = logging.getLogger(__name__)

SALARY_URL = "https://api.openwebninja.com/job-salary-data/job-salary"
COMPANY_SEARCH_URL = "https://api.openwebninja.com/realtime-glassdoor-data/company-search"
SALARY_PER_DAY = int(os.environ.get("SALARY_REQUESTS_PER_DAY", "2"))
SALARY_PER_MONTH = int(os.environ.get("SALARY_REQUESTS_PER_MONTH", "45"))      # free plan: 50
RATINGS_PER_DAY = int(os.environ.get("RATINGS_REQUESTS_PER_DAY", "4"))
RATINGS_PER_MONTH = int(os.environ.get("RATINGS_REQUESTS_PER_MONTH", "95"))    # free plan: 100
SALARY_KEEP_DAYS = 180     # salaries move slowly
RATING_KEEP_DAYS = 90
MIN_SALARIES = 10          # an estimate needs this many salaries behind it to be shown
MIN_RATING_REVIEWS = 5
MIN_COMPANY_JOBS = 3       # only companies with a company page get a rating

# search title -> Radarak role families it stands for
PAY_ROLES: dict[str, tuple[str, ...]] = {
    "Data Engineer": ("Data Engineer", "Analytics Engineer"),
    "Data Analyst": ("Data Analyst", "BI Analyst / Developer"),
    "Data Scientist": ("Data Scientist",),
    "Machine Learning Engineer": ("ML / AI Engineer", "LLM / GenAI Engineer", "MLOps Engineer", "Computer Vision Engineer"),
    "Software Engineer": ("Software Engineer", "Full-Stack Engineer"),
    "Backend Developer": ("Backend Engineer",),
    "Frontend Developer": ("Frontend Engineer",),
    "Mobile Developer": ("Mobile Engineer", "iOS Engineer", "Android Engineer", "Cross-platform Mobile Engineer",
                         "Native Mobile Engineer (iOS + Android)"),
    "DevOps Engineer": ("DevOps / Platform Engineer", "Site Reliability Engineer", "Cloud / Infrastructure Engineer"),
    "QA Engineer": ("QA Automation Engineer", "QA / Test Engineer"),
    "UX Designer": ("UX / Product Designer", "UI / Visual Designer"),
    "Product Manager": ("Product Manager / Owner",),
    "Cyber Security Engineer": ("Security Engineer", "SOC / Security Analyst", "Penetration Tester / Red Team"),
    "SAP Consultant": ("ERP / CRM Consultant", "ERP / CRM Developer"),
    "Project Manager": ("Project Manager", "Technical Project / Program Manager"),
    "Account Manager": ("Account Manager",),
}
ROLE_TO_QUERY = {r: q for q, roles in PAY_ROLES.items() for r in roles}

# (city, country, location pattern, main city of the country)
PAY_CITIES: list[tuple[str, str, str, bool]] = [
    ("Cairo", "Egypt", r"cairo|giza|new\s+cairo|october|zayed|smart\s+village|heliopolis|maadi|nasr\s+city|"
                       r"new\s+capital|القاهرة|الجيزة", True),
    ("Alexandria", "Egypt", r"alexandria|الإسكندرية|الاسكندرية", False),
    ("Riyadh", "Saudi Arabia", r"riyadh|الرياض", True),
    ("Jeddah", "Saudi Arabia", r"jedd?ah|jiddah|جدة", False),
    ("Dubai", "United Arab Emirates", r"dubai|دبي", True),
    ("Abu Dhabi", "United Arab Emirates", r"abu\s*dhabi|أبوظبي|ابوظبي", False),
    ("Doha", "Qatar", r"doha|الدوحة", True),
    ("Kuwait City", "Kuwait", r"kuwait", True),
    ("Manama", "Bahrain", r"manama|المنامة", True),
    ("Muscat", "Oman", r"muscat|مسقط", True),
]
_CITY_RE = [(city, country, re.compile(pat, re.I)) for city, country, pat, _ in PAY_CITIES]
MAIN_CITY = {country: city for city, country, _, main in PAY_CITIES if main}
CITY_COUNTRY = {city: country for city, country, _, _ in PAY_CITIES}

DDL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE IF NOT EXISTS raw.salary_estimates (
    job_title   text        NOT NULL,
    city        text        NOT NULL,
    status      text        NOT NULL,   -- ok | empty | error
    estimate    jsonb,
    fetched_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (job_title, city)
);
CREATE TABLE IF NOT EXISTS raw.company_ratings (
    company     text        NOT NULL PRIMARY KEY,
    status      text        NOT NULL,   -- ok | no_match | error
    rating      jsonb,
    fetched_at  timestamptz NOT NULL DEFAULT now()
);
"""


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()


def api_key() -> str:
    return os.environ.get("OPENWEBNINJA_API_KEY", "").strip() or os.environ.get("JSEARCH_API_KEY", "").strip()


# ------------------------------------------------------------------------------------------ which city / role
def job_city(location: str | None, countries: list[str], work_mode: str | None) -> str | None:
    """The PAY_CITIES city of an office job: from the location text, else the main city of its one country."""
    if work_mode == "Remote" or not countries:
        return None
    text = location or ""
    for city, country, rx in _CITY_RE:
        if country in countries and rx.search(text):
            return city
    if len(countries) == 1:
        return MAIN_CITY.get(countries[0])
    return None


def pay_query(role_family: str | None) -> str | None:
    return ROLE_TO_QUERY.get(role_family or "")


# ------------------------------------------------------------------------------------------ salary estimates
def parse_salary(payload: dict) -> dict | None:
    """The first estimate of a Job Salary Data answer, with only the fields we use."""
    rows = (payload or {}).get("data") or []
    r = rows[0] if rows and isinstance(rows[0], dict) else None
    if not r or r.get("median_salary") in (None, 0):
        return None

    def n(k):
        v = r.get(k)
        return round(float(v)) if isinstance(v, (int, float)) else None
    return {"min": n("min_salary"), "median": n("median_salary"), "max": n("max_salary"),
            "base_median": n("median_base_salary"), "currency": (r.get("salary_currency") or "").upper(),
            "period": (r.get("salary_period") or "").upper(), "count": int(r.get("salary_count") or 0),
            "updated": (r.get("salaries_updated_at") or "")[:10], "location": r.get("location"),
            "link": r.get("publisher_link"), "confidence": r.get("confidence")}


def salary_todo(conn, limit: int, today: dt.date | None = None) -> list[tuple[str, str]]:
    """(job title, city) pairs to ask for, the ones with the most open jobs first, skipping fresh answers."""
    today = today or dt.date.today()
    with conn.cursor() as cur:
        cur.execute("""select role_family, location_text, primary_country, work_mode from marts.fct_job_postings
                       where is_active and primary_country = any(%s)""", (list(MAIN_CITY),))
        demand: Counter = Counter()
        for role, loc, country, mode in cur.fetchall():
            q, city = pay_query(role), job_city(loc, [country], mode)
            if q and city:
                demand[(q, city)] += 1
        cur.execute("select job_title, city from raw.salary_estimates where fetched_at > %s",
                    (today - dt.timedelta(days=SALARY_KEEP_DAYS),))
        fresh = set(cur.fetchall())
    return [pair for pair, _ in demand.most_common() if pair not in fresh][:limit]


def fetch_salary(key: str, title: str, city: str) -> dict:
    resp = requests.get(SALARY_URL, params={"job_title": title.lower(), "location": f"{city}, {CITY_COUNTRY[city]}"},
                        headers={"X-API-Key": key}, timeout=40)
    resp.raise_for_status()
    return resp.json()


def save_salary(conn, title: str, city: str, status: str, estimate: dict | None) -> None:
    with conn.cursor() as cur:
        cur.execute("""insert into raw.salary_estimates (job_title, city, status, estimate, fetched_at)
                       values (%s, %s, %s, %s, now())
                       on conflict (job_title, city) do update
                       set status = excluded.status, estimate = coalesce(excluded.estimate, raw.salary_estimates.estimate),
                           fetched_at = now()""",
                    (title, city, status, json.dumps(estimate) if estimate else None))
    conn.commit()


# ------------------------------------------------------------------------------------------ company ratings
_SUFFIX = re.compile(r"\b(inc|llc|ltd|limited|co|corp|corporation|company|plc|gmbh|sa|sae|fz|fzco|fze|l\.?l\.?c|group"
                     r"|holding|holdings|egypt|ksa|uae|mena|technologies|technology)\b\.?", re.I)


def norm_company(name: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", _SUFFIX.sub(" ", (name or "").lower()))


def match_company(name: str, results: list[dict]) -> dict | None:
    """The search result that is really this company: same name (ignoring Inc/LLC/Egypt/...), or one name
    starting with the other when both are long enough. Never a guess."""
    want = norm_company(name)
    if not want:
        return None
    results = [r for r in results or [] if isinstance(r, dict)]
    for r in results:                                     # an exact name first, wherever it is in the list
        if norm_company(r.get("name")) == want:
            return r
    for r in results:                                     # "Delivery Hero" ~ "Delivery Hero SE", not "Paymob" ~ "Paymobile Systems"
        got = norm_company(r.get("name"))
        short, long_ = sorted((got, want), key=len)
        if len(short) >= 5 and long_.startswith(short) and len(long_) - len(short) <= 3:
            return r
    return None


def parse_rating(r: dict) -> dict | None:
    if not r or r.get("rating") in (None, 0):
        return None
    return {"rating": round(float(r["rating"]), 1), "reviews": int(r.get("review_count") or 0),
            "name": r.get("name"), "link": r.get("company_link"), "hq": r.get("headquarters_location"),
            "size": r.get("company_size")}


def ratings_todo(conn, limit: int, today: dt.date | None = None) -> list[str]:
    """Companies with a company page, most open jobs in Egypt and the Gulf first, skipping fresh answers."""
    today = today or dt.date.today()
    with conn.cursor() as cur:
        cur.execute("""select company_name,
                              count(*) filter (where primary_country = any(%s)) as local_jobs, count(*) as jobs
                       from marts.fct_job_postings
                       where is_active and company_name is not null
                       group by 1 having count(*) >= %s
                       order by 2 desc, 3 desc""", (list(MAIN_CITY), MIN_COMPANY_JOBS))
        companies = [r[0] for r in cur.fetchall() if r[1] > 0]
        cur.execute("select company from raw.company_ratings where fetched_at > %s",
                    (today - dt.timedelta(days=RATING_KEEP_DAYS),))
        fresh = {r[0] for r in cur.fetchall()}
    return [c for c in companies if c not in fresh][:limit]


def fetch_company(key: str, name: str) -> dict:
    resp = requests.get(COMPANY_SEARCH_URL, params={"query": name, "limit": 5}, headers={"X-API-Key": key}, timeout=40)
    resp.raise_for_status()
    return resp.json()


def save_rating(conn, company: str, status: str, rating: dict | None) -> None:
    with conn.cursor() as cur:
        cur.execute("""insert into raw.company_ratings (company, status, rating, fetched_at) values (%s, %s, %s, now())
                       on conflict (company) do update
                       set status = excluded.status, rating = coalesce(excluded.rating, raw.company_ratings.rating),
                           fetched_at = now()""",
                    (company, status, json.dumps(rating) if rating else None))
    conn.commit()


# ------------------------------------------------------------------------------------------ the daily run
def run(conn, today: dt.date | None = None) -> dict:
    """Ask for today's share of salary estimates and ratings. Never raises."""
    key = api_key()
    if not key:
        return {"skipped": "OPENWEBNINJA_API_KEY not set"}
    counts = {"salaries": 0, "ratings": 0, "errors": 0}
    try:
        ensure_schema(conn)
        todo = salary_todo(conn, budget_left("salary_data", SALARY_PER_DAY, SALARY_PER_MONTH, today), today)
        for title, city in todo:
            budget_spend("salary_data", 1, today)
            try:
                est = parse_salary(fetch_salary(key, title, city))
                save_salary(conn, title, city, "ok" if est else "empty", est)
                counts["salaries"] += 1
            except requests.RequestException as exc:
                log.warning("salary %s / %s failed: %s", title, city, exc)
                counts["errors"] += 1
        todo = ratings_todo(conn, budget_left("glassdoor", RATINGS_PER_DAY, RATINGS_PER_MONTH, today), today)
        for company in todo:
            budget_spend("glassdoor", 1, today)
            try:
                hit = match_company(company, (fetch_company(key, company) or {}).get("data") or [])
                rating = parse_rating(hit) if hit else None
                save_rating(conn, company, "ok" if rating else "no_match", rating)
                counts["ratings"] += 1
            except requests.RequestException as exc:
                log.warning("rating %s failed: %s", company, exc)
                counts["errors"] += 1
    except Exception as exc:  # noqa: BLE001 - extras never break the pipeline
        log.warning("salary/rating enrichment stopped: %s", exc)
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
    log.info("enrichment: %s", counts)
    return counts


# ------------------------------------------------------------------------------------------ for the site
def load_estimates(conn) -> list[dict]:
    """Shown estimates: enough salaries behind them. Compact keys for meta.json."""
    try:
        with conn.cursor() as cur:
            cur.execute("""select job_title, city, estimate from raw.salary_estimates
                           where status = 'ok' and estimate is not null order by city, job_title""")
            rows = cur.fetchall()
    except Exception as exc:  # noqa: BLE001 - table missing on a fresh install
        log.info("no salary estimates yet (%s)", exc)
        conn.rollback()
        return []
    out = []
    for title, city, e in rows:
        e = e if isinstance(e, dict) else json.loads(e)
        if (e.get("count") or 0) < MIN_SALARIES or not e.get("median"):
            continue
        out.append({"q": title, "city": city, "co": CITY_COUNTRY.get(city), "cur": e.get("currency"),
                    "per": e.get("period") or "MONTH", "lo": e.get("min"), "md": e.get("median"), "hi": e.get("max"),
                    "n": e.get("count"), "up": (e.get("updated") or "")[:7], "u": e.get("link")})
    return out


def load_ratings(conn) -> dict[str, dict]:
    try:
        with conn.cursor() as cur:
            cur.execute("select company, rating from raw.company_ratings where status = 'ok' and rating is not null")
            rows = cur.fetchall()
    except Exception as exc:  # noqa: BLE001
        log.info("no company ratings yet (%s)", exc)
        conn.rollback()
        return {}
    out = {}
    for company, r in rows:
        r = r if isinstance(r, dict) else json.loads(r)
        if (r.get("reviews") or 0) >= MIN_RATING_REVIEWS:
            out[company] = r
    return out


def attach_estimates(jobs: list[dict], estimates: list[dict]) -> int:
    """job["pe"] = index into meta["pay_est"], for office jobs without a published salary."""
    idx = {(e["q"], e["city"]): i for i, e in enumerate(estimates)}
    n = 0
    for j in jobs:
        if j.get("$"):
            continue
        q, city = pay_query(j.get("r")), job_city(j.get("l"), j.get("co") or [], j.get("w"))
        i = idx.get((q, city))
        if i is None and city and q:          # e.g. Alexandria not fetched yet: the country's main city, named as such
            i = idx.get((q, MAIN_CITY.get(CITY_COUNTRY.get(city))))
        if i is not None:
            j["pe"] = i
            n += 1
    return n
