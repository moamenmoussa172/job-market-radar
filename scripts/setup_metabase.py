"""Create (or re-create) the Job Market Radar dashboard in Metabase via its API.

Run it inside the Airflow container (it has Python, `requests`, the warehouse
credentials, and the dbt seeds mounted), from the project folder:

  PowerShell:
    Get-Content scripts\\setup_metabase.py -Raw | docker compose exec -T `
      -e MB_ADMIN_EMAIL=you@example.com -e MB_ADMIN_PASSWORD=YourPassw0rd `
      airflow-scheduler python -

Safe to re-run: it logs in if Metabase is already set up, reuses the database
connection, and replaces the previous version of the dashboard.
"""
from __future__ import annotations

import csv
import os
import re
import sys
import time
import uuid

import requests

MB_URL = os.environ.get("MB_URL", "http://metabase:3000").rstrip("/")
ADMIN_EMAIL = os.environ.get("MB_ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.environ.get("MB_ADMIN_PASSWORD", "")
DB_NAME = "Job Market Radar"
DASHBOARD_NAME = "Tech Job Market Radar"
LEGACY_DASHBOARD_NAMES = ["Data Job Market Radar"]  # archived on re-run
CARD_PREFIX = "JMR - "
SEEDS_DIR = os.environ.get("SEEDS_DIR", "/opt/airflow/dbt/seeds")

def _seed_column(filename: str, column: str, order_by: str | None = None) -> list[str]:
    path = os.path.join(SEEDS_DIR, filename)
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if order_by:
        rows.sort(key=lambda r: (int(r[order_by]), r[column]))
    seen, out = set(), []
    for r in rows:
        v = r[column]
        if v and v not in seen and r.get("track") != "Not tech":
            seen.add(v)
            out.append(v)
    return out


def roles() -> list[str]:
    return _seed_column("role_tracks.csv", "role_family", "track_order")


def tracks() -> list[str]:
    return _seed_column("role_tracks.csv", "track", "track_order")


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
class MetabaseError(RuntimeError):
    pass


def fail(msg: str) -> None:
    print(f"\nERROR: {msg}", file=sys.stderr)
    sys.exit(1)


class Client:
    def __init__(self, base: str):
        self.base = base
        self.s = requests.Session()

    def call(self, method: str, path: str, body: dict | None = None, ok=(200, 202, 204)):
        r = self.s.request(method, f"{self.base}{path}", json=body, timeout=120)
        if r.status_code not in ok:
            raise MetabaseError(f"{method} {path} -> HTTP {r.status_code}: {r.text[:800]}")
        if not r.content:
            return None
        try:
            return r.json()
        except ValueError:
            return r.text


def wait_for_metabase(c: Client, timeout_s: int = 300) -> None:
    print(f"Waiting for Metabase at {MB_URL} ...", end="", flush=True)
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            r = c.s.get(f"{MB_URL}/api/health", timeout=5)
            if r.status_code == 200 and r.json().get("status") == "ok":
                print(" ready.")
                return
        except (requests.RequestException, ValueError):
            pass
        print(".", end="", flush=True)
        time.sleep(5)
    fail("Metabase did not become healthy in 5 minutes. Check: docker compose logs metabase")


def login_or_setup(c: Client) -> None:
    props = c.call("GET", "/api/session/properties")
    token = props.get("setup-token")
    already = props.get("has-user-setup")
    if not already and token:
        print("Creating the Metabase admin user ...")
        res = c.call("POST", "/api/setup", {
            "token": token,
            "user": {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
                     "first_name": "Job Radar", "last_name": "Admin"},
            "prefs": {"site_name": "Job Market Radar"},
        })
    else:
        print("Metabase is already set up - logging in ...")
        res = c.call("POST", "/api/session", {"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    session_id = res.get("id") if isinstance(res, dict) else None
    if not session_id:
        fail(f"Could not get a session from Metabase: {res}")
    c.s.headers["X-Metabase-Session"] = session_id


def ensure_database(c: Client) -> int:
    dbs = c.call("GET", "/api/database")
    dbs = dbs.get("data", dbs) if isinstance(dbs, dict) else dbs
    for db in dbs:
        if db.get("name") == DB_NAME:
            print(f"Reusing database connection '{DB_NAME}' (id {db['id']}).")
            return db["id"]
    print(f"Connecting Metabase to the warehouse as '{DB_NAME}' ...")
    db = c.call("POST", "/api/database", {
        "name": DB_NAME,
        "engine": "postgres",
        "details": {
            "host": os.environ.get("WAREHOUSE_DB_HOST", "postgres"),
            "port": 5432,
            "dbname": "jobradar",
            "user": os.environ["WAREHOUSE_DB_USER"],
            "password": os.environ["WAREHOUSE_DB_PASSWORD"],
            "ssl": False,
        },
    })
    return db["id"]


def archive_previous(c: Client) -> None:
    """Archive the old dashboard + JMR cards so re-runs don't pile up copies."""
    try:
        dashboards = c.call("GET", "/api/dashboard/") or []
        dashboards = dashboards.get("data", dashboards) if isinstance(dashboards, dict) else dashboards
        for d in dashboards:
            if d.get("name") in [DASHBOARD_NAME, *LEGACY_DASHBOARD_NAMES] and not d.get("archived"):
                c.call("PUT", f"/api/dashboard/{d['id']}", {"archived": True})
                print(f"Archived previous dashboard (id {d['id']}).")
        cards = c.call("GET", "/api/card/") or []
        cards = cards.get("data", cards) if isinstance(cards, dict) else cards
        for card in cards:
            if str(card.get("name", "")).startswith(CARD_PREFIX) and not card.get("archived"):
                c.call("PUT", f"/api/card/{card['id']}", {"archived": True})
    except MetabaseError as exc:
        print(f"  (warning: could not archive old items: {exc})")


# --------------------------------------------------------------------------- #
# Dashboard definition
# --------------------------------------------------------------------------- #
def seed_values(filename: str, column: str) -> list[str]:
    path = os.path.join(SEEDS_DIR, filename)
    with open(path, encoding="utf-8") as fh:
        return sorted({row[column] for row in csv.DictReader(fh) if row.get(column)})


# A "remote job I can apply to from {{country}}, or an office job in {{country}}"
ELIGIBLE_FROM_COUNTRY = """
  exists (
    select 1 from marts.bridge_job_regions r
    where r.job_id = f.job_id
      and (
            r.country = {{country}}
         or (f.work_mode = 'Remote' and r.region = 'Worldwide')
         or (f.work_mode = 'Remote' and r.country is null and r.region in (
                select distinct g.region from seeds.geo_patterns g where g.country = {{country}}))
      )
  )"""

# Shared by the next-best-skill cards. {{my_skills}} is free text such as
# "SQL, Python, Airflow" (case-insensitive; defaults to "SQL, Python").
MY_SKILLS_CTES = """with me as (
  select distinct lower(trim(x)) as skill
  from unnest(string_to_array(coalesce([[{{my_skills}}, ]] 'SQL, Python'), ',')) as x
  where trim(x) <> ''
),
jobs as (
  select job_id from marts.fct_job_postings f
  where is_active [[and track = {{track}}]] [[and role_family = {{role}}]] [[and """ + ELIGIBLE_FROM_COUNTRY + """]]
),
js as (
  select b.job_id, lower(b.skill) as skill
  from marts.bridge_job_skills b join jobs using (job_id)
),
stats as (
  select job_id,
         count(*) as total,
         count(*) filter (where skill in (select skill from me)) as known
  from js group by 1
)"""

CARDS = [
    # ---- row 0: headline numbers -------------------------------------------
    dict(key="kpi_active", name="Active tech jobs", display="scalar", tags=["role"],
         pos=(0, 0, 5, 3), viz={},
         sql="select count(*) as jobs from marts.fct_job_postings f where is_active "
             "[[and track = {{track}}]] [[and role_family = {{role}}]]"),
    dict(key="kpi_worldwide", name="Remote jobs open worldwide", display="scalar", tags=["role"],
         pos=(0, 5, 5, 3), viz={},
         sql="select count(*) as jobs from marts.fct_job_postings f where is_active "
             "and remote_scope = 'Worldwide' [[and track = {{track}}]] [[and role_family = {{role}}]]"),
    dict(key="kpi_eligible", name="Jobs you can apply to (pick your country)", display="scalar",
         tags=["role", "country"], pos=(0, 10, 5, 3), viz={},
         sql="select count(*) as jobs from marts.fct_job_postings f where is_active "
             "[[and track = {{track}}]] [[and role_family = {{role}}]] [[and " + ELIGIBLE_FROM_COUNTRY + "]]"),
    dict(key="kpi_companies", name="Companies hiring", display="scalar", tags=["role"],
         pos=(0, 15, 5, 3), viz={},
         sql="select count(distinct lower(company_name)) as companies from marts.fct_job_postings f "
             "where is_active [[and track = {{track}}]] [[and role_family = {{role}}]]"),
    # ---- row 3: the market by track -----------------------------------------
    dict(key="by_track", name="Active jobs by track and work mode", display="bar", tags=[],
         pos=(3, 0, 24, 8),
         viz={"graph.dimensions": ["track", "work_mode"], "graph.metrics": ["jobs"],
              "stackable.stack_type": "stacked"},
         sql="select track, work_mode, count(*) as jobs from marts.fct_job_postings f where is_active "
             "[[and " + ELIGIBLE_FROM_COUNTRY.strip() + "]] group by 1, 2 order by 1, 2"),
    # ---- row 11: what to learn / how people work ---------------------------
    dict(key="top_skills", name="Top skills for this role (% of jobs)", display="row", tags=["role"],
         pos=(11, 0, 12, 9),
         viz={"graph.dimensions": ["skill"], "graph.metrics": ["pct_of_jobs"],
              "graph.max_categories_enabled": False},
         sql="""with j as (
  select job_id from marts.fct_job_postings f where is_active [[and track = {{track}}]] [[and role_family = {{role}}]]
)
select s.skill, round(100.0 * count(distinct s.job_id) / nullif((select count(*) from j), 0), 1) as pct_of_jobs
from marts.bridge_job_skills s join j using (job_id)
group by 1 order by 2 desc limit 15"""),
    dict(key="work_mode", name="Remote vs hybrid vs onsite", display="pie", tags=["role"],
         pos=(11, 12, 12, 9), viz={"pie.dimension": "work_mode", "pie.metric": "jobs"},
         sql="select work_mode, count(*) as jobs from marts.fct_job_postings f where is_active "
             "[[and track = {{track}}]] [[and role_family = {{role}}]] group by 1 order by 2 desc"),
    # ---- row 12: where -----------------------------------------------------
    dict(key="remote_by_region", name="Remote jobs you can apply to, by your region", display="bar",
         tags=["role"], pos=(20, 0, 12, 8),
         viz={"graph.dimensions": ["region"], "graph.metrics": ["remote_jobs"]},
         sql="select region, sum(remote_jobs) as remote_jobs from reporting.rpt_remote_eligibility "
             "where 1 = 1 [[and track = {{track}}]] [[and role_family = {{role}}]] group by 1 order by 2 desc"),
    dict(key="onsite_countries", name="Top countries for onsite & hybrid jobs", display="row",
         tags=["role"], pos=(20, 12, 12, 8),
         viz={"graph.dimensions": ["country"], "graph.metrics": ["jobs"]},
         sql="select country, sum(jobs) as jobs from reporting.rpt_jobs_by_country "
             "where work_mode <> 'Remote' [[and track = {{track}}]] [[and role_family = {{role}}]] "
             "group by 1 order by 2 desc limit 15"),
    # ---- row 20: next skill / seniority ------------------------------------
    dict(key="skill_pairs", name="If you know this skill, the next skills employers pair with it (%)",
         display="row", tags=["skill"], pos=(28, 0, 12, 8),
         viz={"graph.dimensions": ["skill_b"], "graph.metrics": ["pct_of_skill_a_jobs"]},
         sql="select skill_b, pct_of_skill_a_jobs from reporting.rpt_skill_pairs "
             "where skill_a = coalesce([[{{skill}}, ]] 'SQL') order by 2 desc limit 15"),
    dict(key="seniority", name="Seniority mix", display="bar", tags=["role"], pos=(28, 12, 12, 8),
         viz={"graph.dimensions": ["seniority"], "graph.metrics": ["jobs"]},
         sql="select seniority, count(*) as jobs from marts.fct_job_postings f where is_active "
             "[[and track = {{track}}]] [[and role_family = {{role}}]] group by 1 order by 2 desc"),
    dict(key="kpi_salary_share", name="Jobs that post a salary", display="scalar", tags=["role"],
         pos=(0, 20, 4, 3), viz={},
         sql="select count(*) filter (where has_comparable_salary) || ' of ' || count(*) as jobs "
             "from marts.fct_job_postings f where is_active [[and track = {{track}}]] [[and role_family = {{role}}]]"),
    # ---- row 28: salary ----------------------------------------------------
    dict(key="salary_by_role", name="Salary by role: annual USD, middle 50% and median (jobs that post pay)",
         display="bar", tags=["country"], pos=(36, 0, 14, 9),
         viz={"graph.dimensions": ["role_family"], "graph.metrics": ["p25_usd", "median_usd", "p75_usd"]},
         sql="""select role_family,
       round(percentile_cont(0.25) within group (order by salary_annual_mid_usd)::numeric, -3) as p25_usd,
       round(percentile_cont(0.50) within group (order by salary_annual_mid_usd)::numeric, -3) as median_usd,
       round(percentile_cont(0.75) within group (order by salary_annual_mid_usd)::numeric, -3) as p75_usd,
       count(*) as jobs_with_salary
from marts.fct_job_postings f
where is_active and has_comparable_salary [[and track = {{track}}]] [[and """ + ELIGIBLE_FROM_COUNTRY + """]]
group by 1 having count(*) >= 3 order by median_usd desc"""),
    dict(key="salary_by_seniority", name="Median salary by seniority (annual USD)", display="bar",
         tags=["role", "country"], pos=(36, 14, 10, 9),
         viz={"graph.dimensions": ["seniority"], "graph.metrics": ["median_usd"]},
         sql="""select seniority,
       round(percentile_cont(0.5) within group (order by salary_annual_mid_usd)::numeric, -3) as median_usd,
       count(*) as jobs_with_salary
from marts.fct_job_postings f
where is_active and has_comparable_salary [[and track = {{track}}]] [[and role_family = {{role}}]] [[and """ + ELIGIBLE_FROM_COUNTRY + """]]
group by 1 having count(*) >= 2 order by median_usd"""),
    # ---- row 37: next best skill --------------------------------------------
    dict(key="next_skill", name="Next skill to learn: extra jobs you would match (you have 60%+ of their skills)",
         display="row", tags=["my_skills", "role", "country"], pos=(45, 0, 16, 9),
         viz={"graph.dimensions": ["skill"], "graph.metrics": ["extra_jobs_you_would_match"],
              "graph.max_categories_enabled": False},
         sql=MY_SKILLS_CTES + """,
gains as (
  select js.skill, count(*) as extra_jobs_you_would_match
  from js join stats s using (job_id)
  where js.skill not in (select skill from me)
    and s.known::numeric / s.total < 0.6
    and (s.known + 1)::numeric / s.total >= 0.6
  group by 1
)
select d.skill, g.extra_jobs_you_would_match
from gains g join marts.dim_skills d on lower(d.skill) = g.skill
order by 2 desc, 1 limit 12"""),
    dict(key="match_now", name="Jobs you match today (60%+ of their listed skills)", display="scalar",
         tags=["my_skills", "role", "country"], pos=(45, 16, 8, 9), viz={},
         sql=MY_SKILLS_CTES + """
select count(*) filter (where known::numeric / total >= 0.6) || ' of ' || count(*) as jobs
from stats"""),
    # ---- row 46: trend -----------------------------------------------------
    dict(key="trend", name="Skill trend: % of jobs listed each day (top 8 skills)", display="line",
         tags=[], pos=(54, 0, 24, 8),
         viz={"graph.dimensions": ["snapshot_date", "skill"], "graph.metrics": ["pct_of_jobs"]},
         sql="""select snapshot_date, skill, pct_of_jobs
from reporting.rpt_skill_trend_daily
where skill in (
  select skill from reporting.rpt_skill_trend_daily
  group by skill order by sum(jobs_with_skill) desc limit 8
)
order by 1, 2"""),
    # ---- row 54: the list --------------------------------------------------
    dict(key="job_list", name="Jobs you can apply to", display="table", tags=["role", "country"],
         pos=(62, 0, 24, 12), viz={},
         sql="select job_title, company_name, role_family, seniority, work_mode, remote_scope,\n"
             "       coalesce(remote_eligibility_text, location_text) as where_or_who_can_apply,\n"
             "       salary_annual_min_usd, salary_annual_max_usd,\n"
             "       first_seen_date, listed_on, job_url\n"
             "from marts.fct_job_postings f\n"
             "where is_active [[and track = {{track}}]] [[and role_family = {{role}}]] [[and " + ELIGIBLE_FROM_COUNTRY + "]]\n"
             "order by first_seen_date desc, job_title limit 500"),
    # ---- row 66: original boards (aggregator sources) -----------------------
    dict(key="publishers", name="Where these jobs were first posted (LinkedIn, Indeed, Bayt, ... via JSearch / Jooble)",
         display="row", tags=["role", "country"], pos=(74, 0, 24, 8),
         viz={"graph.dimensions": ["original_board"], "graph.metrics": ["jobs"],
              "graph.max_categories_enabled": False},
         sql="select original_board, sum(jobs) as jobs from reporting.rpt_jobs_by_publisher "
             "where 1 = 1 [[and track = {{track}}]] [[and role_family = {{role}}]] [[and country = {{country}}]] "
             "group by 1 order by 2 desc limit 15"),
]

# Each card's filter tags are derived from the {{variables}} its SQL uses.
for _card in CARDS:
    _used = set(re.findall(r"\{\{(\w+)\}\}", _card["sql"]))
    _card["tags"] = [t for t in ("track", "role", "country", "skill", "my_skills") if t in _used]

TAG_LABELS = {"track": "Track", "role": "Role", "country": "Country", "skill": "Skill", "my_skills": "My skills"}


def build_dashboard_parameters() -> list[dict]:
    return [
        {"id": "track", "name": "Track", "slug": "track", "type": "string/=", "sectionId": "string",
         "isMultiSelect": False, "values_source_type": "static-list",
         "values_source_config": {"values": tracks()}},
        {"id": "role", "name": "Role", "slug": "role", "type": "string/=", "sectionId": "string",
         "isMultiSelect": False, "values_source_type": "static-list",
         "values_source_config": {"values": roles()}},
        {"id": "country", "name": "Country", "slug": "country", "type": "string/=", "sectionId": "string", "isMultiSelect": False,
         "values_source_type": "static-list",
         "values_source_config": {"values": seed_values("geo_patterns.csv", "country")}},
        {"id": "skill", "name": "Skill", "slug": "skill", "type": "string/=", "sectionId": "string", "isMultiSelect": False,
         "default": ["SQL"], "values_source_type": "static-list",
         "values_source_config": {"values": seed_values("skills.csv", "skill")}},
        {"id": "my_skills", "name": "My skills (comma-separated)", "slug": "my_skills",
         "type": "string/=", "sectionId": "string", "isMultiSelect": False,
         "default": ["SQL, Python"]},
    ]


def create_card(c: Client, db_id: int, spec: dict) -> int:
    template_tags = {
        t: {"id": str(uuid.uuid4()), "name": t, "display-name": TAG_LABELS[t], "type": "text"}
        for t in spec["tags"]
    }
    card = c.call("POST", "/api/card", {
        "name": CARD_PREFIX + spec["name"],
        "display": spec["display"],
        "visualization_settings": spec["viz"],
        "dataset_query": {
            "database": db_id,
            "type": "native",
            "native": {"query": spec["sql"], "template-tags": template_tags},
        },
    })
    return card["id"]


def create_dashboard(c: Client, db_id: int) -> int:
    dash = c.call("POST", "/api/dashboard", {
        "name": DASHBOARD_NAME,
        "description": "Tech jobs (data, software, QA, UI/UX, DevOps, security): what to learn next and where to apply. Built by scripts/setup_metabase.py.",
    })
    dashcards = []
    for i, spec in enumerate(CARDS, start=1):
        card_id = create_card(c, db_id, spec)
        row, col, size_x, size_y = spec["pos"]
        dashcards.append({
            "id": -i, "card_id": card_id, "row": row, "col": col, "size_x": size_x, "size_y": size_y,
            # Show the clean title on the dashboard (the saved card keeps the JMR prefix,
            # which is how re-runs find and replace their own cards).
            "visualization_settings": {"card.title": spec["name"]},
            "parameter_mappings": [
                {"parameter_id": t, "card_id": card_id, "target": ["variable", ["template-tag", t]]}
                for t in spec["tags"]
            ],
        })
        print(f"  card {i:>2}/{len(CARDS)}: {spec['name']}")

    params = build_dashboard_parameters()
    try:
        c.call("PUT", f"/api/dashboard/{dash['id']}", {"parameters": params, "dashcards": dashcards})
    except MetabaseError as exc:
        # Older/newer Metabase versions may not accept static-list dropdowns;
        # fall back to plain text filters rather than failing.
        print(f"  (dropdown filters not accepted, using plain text filters instead: {exc})")
        plain = [{k: v for k, v in p.items() if not k.startswith("values_source")} for p in params]
        c.call("PUT", f"/api/dashboard/{dash['id']}", {"parameters": plain, "dashcards": dashcards})
    return dash["id"]


def main() -> None:
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        fail("Pass the Metabase admin login with -e MB_ADMIN_EMAIL=... -e MB_ADMIN_PASSWORD=... "
             "(password: 8+ characters with letters and digits).")
    c = Client(MB_URL)
    wait_for_metabase(c)
    try:
        login_or_setup(c)
        db_id = ensure_database(c)
        archive_previous(c)
        print("Building dashboard ...")
        dash_id = create_dashboard(c, db_id)
    except MetabaseError as exc:
        fail(str(exc))
    print(f"\nDone. Open http://localhost:3000/dashboard/{dash_id}")
    print(f"Log in with {ADMIN_EMAIL} and the password you passed.")


if __name__ == "__main__":
    main()
