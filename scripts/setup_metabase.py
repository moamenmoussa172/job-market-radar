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
DASHBOARD_NAME = "Radarak: Tech Job Market"
LEGACY_DASHBOARD_NAMES = ["Data Job Market Radar", "Tech Job Market Radar"]  # archived on re-run
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


SENIORITIES = ["Intern / Student", "Junior", "Mid", "Senior", "Lead / Principal", "Head / Director", "Not stated"]
WORK_MODES = ["Remote", "Hybrid", "Onsite"]
DEFAULT_MY_SKILLS = ["SQL", "Python"]

FACT = "marts.fct_job_postings f"
POSTED = "coalesce(f.posted_at::date, f.first_seen_date)"
SENIORITY_ORDER = ("case f.seniority when 'Intern / Student' then 1 when 'Junior' then 2 when 'Mid' then 3 "
                   "when 'Senior' then 4 when 'Lead / Principal' then 5 when 'Head / Director' then 6 else 7 end")

# A remote job open to people in {{country}}, or an office / hybrid job in {{country}}.
ELIGIBLE_FROM_COUNTRY = """exists (
    select 1 from marts.bridge_job_regions r
    where r.job_id = f.job_id
      and (
            r.country = {{country}}
         or (f.work_mode = 'Remote' and r.region = 'Worldwide')
         or (f.work_mode = 'Remote' and r.country is null and r.region in (
                select distinct g.region from seeds.geo_patterns g where g.country = {{country}}))
      )
  )"""

_FILTERS = [
    ("industry", "f.industry = {{industry}}"),
    ("track", "f.track = {{track}}"),
    ("role", "f.role_family = {{role}}"),
    ("seniority", "f.seniority = {{seniority}}"),
    ("work_mode", "f.work_mode = {{work_mode}}"),
    ("country", ELIGIBLE_FROM_COUNTRY),
    ("skill", "exists (select 1 from marts.bridge_job_skills sk where sk.job_id = f.job_id and sk.skill = {{skill}})"),
    ("requirement", "case {{requirement}}"
                    " when 'Visa / relocation offered' then f.offers_visa_or_relocation"
                    " when 'Open to all nationalities' then not f.nationals_only"
                    " when 'Nationals only' then f.nationals_only"
                    " when 'Arabic required' then f.arabic_required"
                    " when 'Arabic not required' then not f.arabic_required"
                    " else true end"),
]
REQUIREMENTS = ["Visa / relocation offered", "Open to all nationalities", "Nationals only",
                "Arabic required", "Arabic not required"]


def where(*skip: str) -> str:
    """Active jobs + every dashboard filter except the ones in `skip` (optional [[...]] blocks)."""
    return "f.is_active " + " ".join(f"[[and {cond}]]" for tag, cond in _FILTERS if tag not in skip)


# {{my_skills}} is a field filter on marts.dim_skills.skill (multi-select dropdown).
# Metabase renders it as  "marts"."dim_skills"."skill" IN ('SQL', 'Python')  or  1 = 1  when empty;
# empty falls back to SQL + Python.
MY_SKILLS_PICKED_FIELD = "select lower(skill) as skill from marts.dim_skills where {{my_skills}}"
# Fallback when the field can't be found in Metabase's metadata: a comma-separated text box.
MY_SKILLS_PICKED_TEXT = ("select distinct lower(trim(x)) as skill from unnest(string_to_array("
                         "coalesce([[{{my_skills}}, ]] 'SQL, Python'), ',')) as x where trim(x) <> ''")


def my_skills_ctes(job_where: str) -> str:
    return f"""with picked as (
  {MY_SKILLS_PICKED_FIELD}
),
me as (
  select skill from picked
  where (select count(*) from picked) < (select count(*) from marts.dim_skills)
  union all
  select lower(x) from unnest(array{DEFAULT_MY_SKILLS!r}::text[]) as x
  where (select count(*) from picked) >= (select count(*) from marts.dim_skills)
),
jobs as (
  select f.job_id from {FACT} where {job_where}
),
js as (
  select b.job_id, b.skill as skill_name, lower(b.skill) as skill
  from marts.bridge_job_skills b join jobs using (job_id)
),
stats as (
  select job_id,
         count(*) as total,
         count(*) filter (where skill in (select skill from me)) as known
  from js group by 1
)"""


def col(name: str, **settings) -> dict:
    """Metabase column formatting, keyed the way the frontend stores it."""
    return {f'["name","{name}"]': settings}


PCT = dict(number_style="percent", decimals=0)
USD = dict(number_style="currency", currency="USD", currency_style="symbol", decimals=0)


def usd_k(expr: str) -> str:
    return f"'$' || round({expr} / 1000.0)::int || 'k'"


JOB_TABLE_COLUMNS = ["Job title", "Company", "Industry", "Skill match", "Role", "Seniority", "Work mode",
                     "Location / who may apply", "Salary (USD / year)", "Notes", "Skills to add", "Posted", "Found on"]
JOB_TABLE_VIZ = {
    "table.row_index": False,
    # job_url stays in the result (hidden) so the job title can link to it
    "table.columns": [{"name": c, "enabled": True} for c in JOB_TABLE_COLUMNS]
                     + [{"name": "job_url", "enabled": False}],
    "column_settings": {
        **col("Job title", view_as="link", link_url="{{job_url}}"),
        **col("Skill match", **PCT),
    },
}


def job_table_sql(order: str, limit: int) -> str:
    """Job list; the job title links to the posting. order = 'match' (best match first) or 'newest'."""
    if order == "match":
        order_by = """-- jobs you match (60%+) first, then the ones where you have the most of the asked skills, newest first
order by (s.known::numeric / nullif(s.total, 0) >= 0.6) desc nulls last, s.known desc nulls last,
         "Skill match" desc nulls last, "Posted" desc, "Job title" """
    else:
        order_by = 'order by "Posted" desc, "Skill match" desc nulls last, "Job title"'
    return my_skills_ctes(where()) + f""",
gaps as (
  select job_id, string_agg(skill_name, ', ' order by skill_name) as skills_to_add
  from js where skill not in (select skill from me) group by 1
)
select f.job_title as "Job title", f.company_name as "Company", f.industry as "Industry",
       s.known::numeric / nullif(s.total, 0) as "Skill match",
       f.role_family as "Role", f.seniority as "Seniority", f.work_mode as "Work mode",
       coalesce(f.remote_eligibility_text, f.location_text) as "Location / who may apply",
       case when f.has_comparable_salary then
         {usd_k('f.salary_annual_min_usd')} || ' - ' || {usd_k('f.salary_annual_max_usd')} end as "Salary (USD / year)",
       nullif(concat_ws(', ',
           case when f.offers_visa_or_relocation then 'Visa / relocation offered' end,
           case when f.nationals_only then 'Nationals only' end,
           case when f.arabic_required then 'Arabic required' end), '') as "Notes",
       g.skills_to_add as "Skills to add",
       {POSTED} as "Posted",
       f.listed_on as "Found on",
       f.job_url
from {FACT}
join jobs using (job_id)
left join stats s using (job_id)
left join gaps g using (job_id)
{order_by}
limit {limit}"""


PIE_VIZ = {"pie.dimension": "work_mode", "pie.metric": "jobs", "pie.show_total": True,
           "pie.show_legend": True, "pie.percent_visibility": "legend"}
PIE_SQL = (f"select f.work_mode, count(*) as jobs from {FACT} where {where('work_mode')} "
           "group by 1 order by 2 desc")
MAP_VIZ = {"map.type": "region", "map.region": "world_countries",
           "map.dimension": "country_code", "map.metric": "jobs"}
MAP_SQL = f"""select c.code as country_code, f.primary_country as country, count(*) as jobs
from {FACT} join seeds.country_codes c on c.country = f.primary_country
where {where('work_mode', 'country')} and f.work_mode <> 'Remote'
group by 1, 2 order by 3 desc"""

TABS = [
    ("overview", "1. Market overview"),
    ("mena", "2. Middle East"),
    ("skills", "3. Skills to learn"),
    ("where", "4. Where to work"),
    ("salary", "5. Salary"),
    ("jobs", "6. Find jobs"),
]
MENA = "f.primary_region = 'MENA'"

# Text cards: (tab, row, height, markdown)
CLICKS = {  # card key -> {result column: dashboard filter it sets when clicked}
    "by_track": {"track": "track"}, "work_mode_overview": {"work_mode": "work_mode"},
    "work_mode": {"work_mode": "work_mode"}, "roles_demand": {"role": "role"},
    "seniority": {"seniority": "seniority"}, "by_industry": {"industry": "industry"},
    "top_skills": {"skill": "skill"}, "next_skill": {"skill": "skill"}, "rising_skills": {"skill": "skill"},
    "my_skill_demand": {"skill": "skill"}, "salary_by_role": {"role": "role"},
    "salary_by_seniority": {"seniority": "seniority"}, "salary_by_industry": {"industry": "industry"},
    "salary_by_skill": {"skill": "skill"},
    "onsite_countries": {"country": "country"}, "me_by_country": {"country": "country"},
    "me_roles": {"role": "role"},
}

TEXTS = [
    ("overview", 0, 2,
     "**Start here.** Use the dropdowns above: pick a **Track** or **Role**, an **Industry** (banking, fintech, "
     "telecom, ...), and **Your country** to see only jobs "
     "you can apply to (local office/hybrid jobs plus remote jobs open to your region). Every card follows the "
     "filters, and you can **click any bar** to filter by it. Pick a **Must-have skill** to see only jobs that "
     "ask for it. More detail in the tabs: **Middle East**, **Skills to learn**, **Where to work**, **Salary**, "
     "**Find jobs**. Data: active tech job postings from 14 sources, refreshed daily."),
    ("mena", 0, 2,
     "**Middle East.** Tech jobs in Egypt, the Gulf, Jordan and North Africa. *Nationals only* = the posting is "
     "limited to Saudi / Emirati / Qatari / ... nationals; *Arabic required* = Arabic is a required language; "
     "*Visa / relocation* = the employer offers sponsorship or relocation (useful for moving abroad). "
     "Use the **Requirements** filter to hide nationals-only jobs. Click a country or role to filter."),
    ("skills", 0, 2,
     "**What to learn next.** Pick your **Role**, then tick the skills you already have in **My skills**. "
     "*Next skill to learn* shows the one skill that would make you a match (60%+ of a job's listed skills) "
     "for the most extra jobs."),
    ("where", 0, 2,
     "**Where the jobs are.** Remote jobs are split by who may apply (worldwide or only certain regions). "
     "Office and hybrid jobs are shown by country. Pick **Your country** to see what is open to you."),
    ("salary", 0, 2,
     "**Pay.** Only jobs that publish a salary are counted, annualized and converted to USD at the ECB rate "
     "of the day the job was first seen. *Middle 50%* = from the 25th to the 75th percentile. "
     "Groups with fewer than 3 salaries are hidden."),
    ("jobs", 0, 2,
     "**Jobs to apply to**, best skill match first (set **My skills** on any tab). "
     "Click a **job title** to open the posting. "
     "*Skills to add* lists what each job asks for that you don't have yet."),
]

CARDS = [
    # =========================== 1. Market overview ===========================
    dict(key="kpi_active", tab="overview", name="Active jobs", display="scalar", pos=(2, 0, 4, 3), viz={},
         sql=f"select count(*) as jobs from {FACT} where {where()}"),
    dict(key="kpi_new", tab="overview", name="Posted in the last 7 days", display="scalar", pos=(2, 4, 4, 3),
         viz={},
         sql=f"select count(*) filter (where {POSTED} >= current_date - 7) as new_jobs from {FACT} where {where()}"),
    dict(key="kpi_remote_share", tab="overview", name="Remote share", display="scalar", pos=(2, 8, 4, 3),
         viz={"column_settings": col("remote_share", **PCT)},
         sql=f"select avg((f.work_mode = 'Remote')::int)::numeric as remote_share from {FACT} "
             f"where {where('work_mode')}"),
    dict(key="kpi_companies", tab="overview", name="Companies hiring", display="scalar", pos=(2, 12, 4, 3),
         viz={},
         sql=f"select count(distinct lower(f.company_name)) as companies from {FACT} where {where()}"),
    dict(key="kpi_salary_share", tab="overview", name="Jobs that show a salary", display="scalar",
         pos=(2, 16, 4, 3), viz={"column_settings": col("salary_share", **PCT)},
         sql=f"select avg(f.has_comparable_salary::int)::numeric as salary_share from {FACT} where {where()}"),
    dict(key="kpi_median_salary", tab="overview", name="Median salary (USD / year)", display="scalar",
         pos=(2, 20, 4, 3), viz={"column_settings": col("median_usd", **USD)},
         sql=f"select round(percentile_cont(0.5) within group (order by f.salary_annual_mid_usd)::numeric, -3) "
             f"as median_usd from {FACT} where {where()} and f.has_comparable_salary"),
    dict(key="by_track", tab="overview", name="Jobs by track and work mode", display="bar", pos=(5, 0, 16, 9),
         viz={"graph.dimensions": ["track", "work_mode"], "graph.metrics": ["jobs"],
              "stackable.stack_type": "stacked", "graph.y_axis.title_text": "Active jobs",
              "graph.x_axis.title_text": ""},
         sql=f"select f.track, f.work_mode, count(*) as jobs from {FACT} where {where('track')} "
             "group by 1, 2 order by 1, 2"),
    dict(key="work_mode_overview", tab="overview", name="Remote vs hybrid vs onsite", display="pie",
         pos=(5, 16, 8, 9), viz=PIE_VIZ, sql=PIE_SQL),
    dict(key="roles_demand", tab="overview", name="Most in-demand roles (all active vs posted in the last 7 days)",
         display="row", pos=(14, 0, 12, 10),
         viz={"graph.dimensions": ["role"], "graph.metrics": ["active_jobs", "posted_last_7_days"],
              "graph.max_categories_enabled": False},
         sql=f"select f.role_family as role, count(*) as active_jobs, "
             f"count(*) filter (where {POSTED} >= current_date - 7) as posted_last_7_days "
             f"from {FACT} where {where('role')} group by 1 order by 2 desc limit 15"),
    dict(key="seniority", tab="overview", name="Seniority mix: how open is this market to juniors?",
         display="bar", pos=(14, 12, 12, 10),
         viz={"graph.dimensions": ["seniority"], "graph.metrics": ["jobs"], "graph.x_axis.title_text": "",
              "graph.show_values": True},
         sql=f"select f.seniority, count(*) as jobs from {FACT} where {where('seniority')} "
             f"group by 1, {SENIORITY_ORDER} order by {SENIORITY_ORDER}"),
    dict(key="map_overview", tab="overview", name="Office & hybrid jobs on the map", display="map",
         pos=(24, 0, 12, 9), viz=MAP_VIZ, sql=MAP_SQL),
    dict(key="by_industry", tab="overview",
         name="Tech jobs by industry (company list + name rules; 'Not identified' hidden)", display="row",
         pos=(33, 0, 24, 10),
         viz={"graph.dimensions": ["industry", "track"], "graph.metrics": ["jobs"],
              "stackable.stack_type": "stacked", "graph.max_categories_enabled": False},
         sql=f"""select f.industry, f.track, count(*) as jobs from {FACT}
where {where('industry')} and f.industry <> 'Not identified'
group by 1, 2 order by sum(count(*)) over (partition by f.industry) desc, 1, 2"""),
    dict(key="new_per_day", tab="overview", name="New postings per day (last 30 days)", display="line",
         pos=(43, 0, 24, 6),
         viz={"graph.dimensions": ["posted_date"], "graph.metrics": ["jobs"], "graph.x_axis.title_text": ""},
         sql=f"select {POSTED} as posted_date, count(*) as jobs from {FACT} "
             f"where {where()} and {POSTED} >= current_date - 30 group by 1 order by 1"),
    dict(key="top_companies", tab="overview", name="Companies with the most open jobs", display="table",
         pos=(24, 12, 12, 9), viz={"column_settings": col("Remote share", **PCT)},
         sql=f"""select f.company_name as "Company", count(*) as "Open jobs",
       count(distinct f.role_family) as "Different roles",
       avg((f.work_mode = 'Remote')::int)::numeric as "Remote share",
       max({POSTED}) as "Latest posting"
from {FACT} where {where()} and f.company_name is not null
group by 1 order by 2 desc, 1 limit 50"""),

    dict(key="newest_jobs", tab="overview", name="Newest jobs for you (click a job title to open it)",
         display="table", pos=(49, 0, 24, 12), viz=JOB_TABLE_VIZ, sql=job_table_sql("newest", 100)),

    # =========================== 2. Middle East ===========================
    dict(key="me_jobs", tab="mena", name="Tech jobs in the Middle East", display="scalar", pos=(2, 0, 6, 3),
         viz={}, sql=f"select count(*) as jobs from {FACT} where {where('country')} and {MENA}"),
    dict(key="me_nationals", tab="mena", name="Limited to nationals", display="scalar", pos=(2, 6, 6, 3),
         viz={"column_settings": col("share", **PCT)},
         sql=f"select avg(f.nationals_only::int)::numeric as share from {FACT} "
             f"where {where('country', 'requirement')} and {MENA}"),
    dict(key="me_arabic", tab="mena", name="Arabic required", display="scalar", pos=(2, 12, 6, 3),
         viz={"column_settings": col("share", **PCT)},
         sql=f"select avg(f.arabic_required::int)::numeric as share from {FACT} "
             f"where {where('country', 'requirement')} and {MENA}"),
    dict(key="me_salary", tab="mena", name="Median salary (USD / year)", display="scalar", pos=(2, 18, 6, 3),
         viz={"column_settings": col("median_usd", **USD)},
         sql=f"select round(percentile_cont(0.5) within group (order by f.salary_annual_mid_usd)::numeric, -3) "
             f"as median_usd from {FACT} where {where('country')} and {MENA} and f.has_comparable_salary"),
    dict(key="me_by_country", tab="mena", name="Jobs by country and track (click a country to filter)",
         display="row", pos=(5, 0, 14, 10),
         viz={"graph.dimensions": ["country", "track"], "graph.metrics": ["jobs"],
              "stackable.stack_type": "stacked", "graph.max_categories_enabled": False},
         sql=f"""select f.primary_country as country, f.track, count(*) as jobs from {FACT}
where {where('country')} and {MENA} and f.primary_country is not null
group by 1, 2 order by sum(count(*)) over (partition by f.primary_country) desc, 1, 2"""),
    dict(key="me_country_table", tab="mena", name="Compare Middle East countries", display="table",
         pos=(5, 14, 10, 10),
         viz={"column_settings": {**col("Nationals only", **PCT), **col("Arabic required", **PCT),
                                  **col("Median salary (USD)", **USD)}},
         sql=f"""select f.primary_country as "Country", count(*) as "Jobs",
       avg(f.nationals_only::int)::numeric as "Nationals only",
       avg(f.arabic_required::int)::numeric as "Arabic required",
       count(*) filter (where f.work_mode = 'Remote') as "Remote",
       case when count(*) filter (where f.has_comparable_salary) >= 3 then
         round(percentile_cont(0.5) within group (order by f.salary_annual_mid_usd)
               filter (where f.has_comparable_salary)::numeric, -3) end as "Median salary (USD)"
from {FACT}
where {where('country', 'requirement')} and {MENA} and f.primary_country is not null
group by 1 order by 2 desc"""),
    dict(key="me_roles", tab="mena", name="Most in-demand roles in the Middle East", display="row",
         pos=(15, 0, 12, 10),
         viz={"graph.dimensions": ["role"], "graph.metrics": ["jobs"], "graph.show_values": True},
         sql=f"""select f.role_family as role, count(*) as jobs from {FACT}
where {where('role', 'country')} and {MENA} group by 1 order by 2 desc limit 15"""),
    dict(key="me_companies", tab="mena", name="Middle East companies hiring the most", display="table",
         pos=(15, 12, 12, 10), viz={},
         sql=f"""select f.company_name as "Company", f.industry as "Industry",
       string_agg(distinct f.primary_country, ', ') as "Countries", count(*) as "Open jobs"
from {FACT} where {where('country')} and {MENA} and f.company_name is not null
group by 1, 2 order by 4 desc, 1 limit 50"""),
    dict(key="relocation_jobs", tab="mena",
         name="Jobs abroad that offer visa sponsorship or relocation (click a job title to open it)",
         display="table", pos=(25, 0, 24, 12),
         viz={"table.row_index": False,
              "table.columns": [{"name": c, "enabled": True} for c in
                                ["Job title", "Company", "Country", "Role", "Seniority", "Work mode", "Industry",
                                 "Salary (USD / year)", "Posted"]] + [{"name": "job_url", "enabled": False}],
              "column_settings": col("Job title", view_as="link", link_url="{{job_url}}")},
         sql=f"""select f.job_title as "Job title", f.company_name as "Company", f.primary_country as "Country",
       f.role_family as "Role", f.seniority as "Seniority", f.work_mode as "Work mode", f.industry as "Industry",
       case when f.has_comparable_salary then
         {usd_k('f.salary_annual_min_usd')} || ' - ' || {usd_k('f.salary_annual_max_usd')} end as "Salary (USD / year)",
       {POSTED} as "Posted", f.job_url
from {FACT}
where {where('country', 'requirement')} and f.offers_visa_or_relocation
order by {POSTED} desc, 1 limit 300"""),

    # =========================== 3. Skills to learn ===========================
    dict(key="top_skills", tab="skills",
         name="Top skills employers ask for (% of jobs) - pick a Must-have skill to see what goes with it",
         display="row",
         pos=(2, 0, 12, 10),
         viz={"graph.dimensions": ["skill"], "graph.metrics": ["pct_of_jobs"],
              "graph.max_categories_enabled": False, "graph.show_values": True},
         sql=f"""with j as (select f.job_id from {FACT} where {where()})
select s.skill, round(100.0 * count(distinct s.job_id) / nullif((select count(*) from j), 0), 1) as pct_of_jobs
from marts.bridge_job_skills s join j using (job_id)
where 1 = 1 [[and s.skill <> {{{{skill}}}}]]
group by 1 order by 2 desc limit 15"""),
    dict(key="skill_areas", tab="skills", name="Skill areas employers ask for (% of jobs)", display="row",
         pos=(2, 12, 12, 10),
         viz={"graph.dimensions": ["skill_area"], "graph.metrics": ["pct_of_jobs"],
              "graph.max_categories_enabled": False, "graph.show_values": True},
         sql=f"""with j as (select f.job_id from {FACT} where {where()})
select s.category as skill_area,
       round(100.0 * count(distinct s.job_id) / nullif((select count(*) from j), 0), 1) as pct_of_jobs
from marts.bridge_job_skills s join j using (job_id)
group by 1 order by 2 desc"""),
    dict(key="next_skill", tab="skills",
         name="Next skill to learn: extra jobs you would match if you added it", display="row",
         pos=(12, 0, 14, 10),
         viz={"graph.dimensions": ["skill"], "graph.metrics": ["extra_jobs_you_would_match"],
              "graph.max_categories_enabled": False, "graph.show_values": True},
         sql=my_skills_ctes(where()) + """,
gains as (
  select js.skill, min(js.skill_name) as skill_name, count(*) as extra_jobs_you_would_match
  from js join stats s using (job_id)
  where js.skill not in (select skill from me)
    and s.known::numeric / s.total < 0.6
    and (s.known + 1)::numeric / s.total >= 0.6
  group by 1
)
select skill_name as skill, extra_jobs_you_would_match
from gains order by 2 desc, 1 limit 12"""),
    dict(key="match_now", tab="skills", name="Jobs you already match (60%+ of their skills)", display="scalar",
         pos=(12, 14, 5, 4), viz={},
         sql=my_skills_ctes(where()) + """
select count(*) filter (where known::numeric / total >= 0.6) as jobs_you_match from stats"""),
    dict(key="match_rate", tab="skills", name="Share of jobs you match", display="scalar",
         pos=(12, 19, 5, 4), viz={"column_settings": col("match_rate", **PCT)},
         sql=my_skills_ctes(where()) + """
select avg((known::numeric / total >= 0.6)::int)::numeric as match_rate from stats"""),
    dict(key="my_skill_demand", tab="skills", name="How in demand your skills are (% of jobs)", display="row",
         pos=(16, 14, 10, 6),
         viz={"graph.dimensions": ["skill"], "graph.metrics": ["pct_of_jobs"], "graph.show_values": True},
         sql=my_skills_ctes(where()) + """
select min(js.skill_name) as skill,
       round(100.0 * count(distinct js.job_id) / nullif((select count(*) from jobs), 0), 1) as pct_of_jobs
from js where js.skill in (select skill from me)
group by js.skill order by 2 desc"""),
    dict(key="rising_skills", tab="skills",
         name="Rising skills: share in jobs posted in the last 14 days minus share in older jobs (points)",
         display="row", pos=(22, 0, 24, 9),
         viz={"graph.dimensions": ["skill"], "graph.metrics": ["change_pts"], "graph.show_values": True},
         sql=f"""with j as (
  select f.job_id, {POSTED} >= current_date - 14 as is_new from {FACT} where {where()}
),
n as (select count(*) filter (where is_new) as new_jobs, count(*) filter (where not is_new) as old_jobs from j),
s as (
  select b.skill, count(*) filter (where j.is_new) as new_with, count(*) filter (where not j.is_new) as old_with
  from marts.bridge_job_skills b join j using (job_id) group by 1
)
select s.skill,
       round(100.0 * s.new_with / n.new_jobs - 100.0 * s.old_with / n.old_jobs, 1) as change_pts,
       round(100.0 * s.new_with / n.new_jobs, 1) as pct_of_new_jobs,
       round(100.0 * s.old_with / n.old_jobs, 1) as pct_of_older_jobs
from s cross join n
where n.new_jobs >= 20 and n.old_jobs >= 20 and s.new_with + s.old_with >= 10
order by 2 desc limit 12"""),
    dict(key="trend", tab="skills", name="Skill trend: % of listed jobs each day (top 8 skills)", display="line",
         pos=(31, 0, 24, 8),
         viz={"graph.dimensions": ["snapshot_date", "skill"], "graph.metrics": ["pct_of_jobs"],
              "graph.x_axis.title_text": ""},
         sql="""select snapshot_date, skill, pct_of_jobs
from reporting.rpt_skill_trend_daily
where skill in (
  select skill from reporting.rpt_skill_trend_daily
  group by skill order by sum(jobs_with_skill) desc limit 8
)
order by 1, 2"""),

    # =========================== 3. Where to work ===========================
    dict(key="work_mode", tab="where", name="Remote vs hybrid vs onsite", display="pie", pos=(2, 0, 8, 9),
         viz=PIE_VIZ, sql=PIE_SQL),
    dict(key="remote_by_region", tab="where", name="Remote jobs by who may apply", display="bar",
         pos=(2, 8, 16, 9),
         viz={"graph.dimensions": ["open_to"], "graph.metrics": ["remote_jobs"], "graph.show_values": True,
              "graph.x_axis.title_text": ""},
         sql=f"""select r.region as open_to, count(distinct f.job_id) as remote_jobs
from {FACT} join marts.bridge_job_regions r on r.job_id = f.job_id
where {where('work_mode', 'country')} and f.work_mode = 'Remote' and r.region is not null
group by 1 order by 2 desc"""),
    dict(key="map_where", tab="where", name="Office & hybrid jobs on the map", display="map",
         pos=(11, 0, 14, 11), viz=MAP_VIZ, sql=MAP_SQL),
    dict(key="onsite_countries", tab="where", name="Top countries for office & hybrid jobs", display="row",
         pos=(11, 14, 10, 11),
         viz={"graph.dimensions": ["country"], "graph.metrics": ["jobs"], "graph.show_values": True},
         sql=f"""select f.primary_country as country, count(*) as jobs from {FACT}
where {where('work_mode', 'country')} and f.work_mode <> 'Remote' and f.primary_country is not null
group by 1 order by 2 desc limit 15"""),
    dict(key="country_table", tab="where", name="Compare countries (office & hybrid jobs)", display="table",
         pos=(22, 0, 24, 10),
         viz={"column_settings": {**col("Hybrid share", **PCT), **col("Median salary (USD)", **USD)}},
         sql=f"""select f.primary_country as "Country", count(*) as "Jobs",
       avg((f.work_mode = 'Hybrid')::int)::numeric as "Hybrid share",
       count(*) filter (where f.seniority in ('Intern / Student', 'Junior')) as "Junior & intern jobs",
       count(*) filter (where f.has_comparable_salary) as "Jobs with salary",
       case when count(*) filter (where f.has_comparable_salary) >= 3 then
         round(percentile_cont(0.5) within group (order by f.salary_annual_mid_usd)
               filter (where f.has_comparable_salary)::numeric, -3) end as "Median salary (USD)"
from {FACT}
where {where('work_mode', 'country')} and f.work_mode <> 'Remote' and f.primary_country is not null
group by 1 order by 2 desc limit 40"""),
    dict(key="publishers", tab="where",
         name="Where these jobs were first posted (LinkedIn, Indeed, Bayt, ... via JSearch / Jooble)",
         display="row", pos=(32, 0, 24, 8),
         viz={"graph.dimensions": ["original_board"], "graph.metrics": ["jobs"],
              "graph.max_categories_enabled": False},
         sql="select original_board, sum(jobs) as jobs from reporting.rpt_jobs_by_publisher "
             "where 1 = 1 [[and track = {{track}}]] [[and role_family = {{role}}]] "
             "[[and work_mode = {{work_mode}}]] [[and country = {{country}}]] "
             "group by 1 order by 2 desc limit 15"),

    # =========================== 4. Salary ===========================
    dict(key="sal_p25", tab="salary", name="Lower range (25th percentile)", display="scalar", pos=(2, 0, 6, 3),
         viz={"column_settings": col("p25_usd", **USD)},
         sql=f"select round(percentile_cont(0.25) within group (order by f.salary_annual_mid_usd)::numeric, -3) "
             f"as p25_usd from {FACT} where {where()} and f.has_comparable_salary"),
    dict(key="sal_median", tab="salary", name="Median salary (USD / year)", display="scalar", pos=(2, 6, 6, 3),
         viz={"column_settings": col("median_usd", **USD)},
         sql=f"select round(percentile_cont(0.5) within group (order by f.salary_annual_mid_usd)::numeric, -3) "
             f"as median_usd from {FACT} where {where()} and f.has_comparable_salary"),
    dict(key="sal_p75", tab="salary", name="Upper range (75th percentile)", display="scalar", pos=(2, 12, 6, 3),
         viz={"column_settings": col("p75_usd", **USD)},
         sql=f"select round(percentile_cont(0.75) within group (order by f.salary_annual_mid_usd)::numeric, -3) "
             f"as p75_usd from {FACT} where {where()} and f.has_comparable_salary"),
    dict(key="sal_count", tab="salary", name="Jobs with a published salary", display="scalar", pos=(2, 18, 6, 3),
         viz={},
         sql=f"select count(*) filter (where f.has_comparable_salary) as jobs_with_salary from {FACT} "
             f"where {where()}"),
    dict(key="salary_by_role", tab="salary", name="Salary by role: middle 50% and median (USD / year)",
         display="bar", pos=(5, 0, 24, 9),
         viz={"graph.dimensions": ["role"], "graph.metrics": ["p25_usd", "median_usd", "p75_usd"],
              "graph.x_axis.title_text": ""},
         sql=f"""select f.role_family as role,
       round(percentile_cont(0.25) within group (order by f.salary_annual_mid_usd)::numeric, -3) as p25_usd,
       round(percentile_cont(0.50) within group (order by f.salary_annual_mid_usd)::numeric, -3) as median_usd,
       round(percentile_cont(0.75) within group (order by f.salary_annual_mid_usd)::numeric, -3) as p75_usd,
       count(*) as jobs_with_salary
from {FACT}
where {where('role')} and f.has_comparable_salary
group by 1 having count(*) >= 3 order by median_usd desc"""),
    dict(key="salary_by_seniority", tab="salary", name="Median salary by seniority (USD / year)", display="bar",
         pos=(14, 0, 12, 8),
         viz={"graph.dimensions": ["seniority"], "graph.metrics": ["median_usd"], "graph.show_values": True,
              "graph.x_axis.title_text": ""},
         sql=f"""select f.seniority,
       round(percentile_cont(0.5) within group (order by f.salary_annual_mid_usd)::numeric, -3) as median_usd,
       count(*) as jobs_with_salary
from {FACT}
where {where('seniority')} and f.has_comparable_salary
group by 1, {SENIORITY_ORDER} having count(*) >= 3 order by {SENIORITY_ORDER}"""),
    dict(key="salary_by_country", tab="salary", name="Median salary by country (USD / year)", display="row",
         pos=(14, 12, 12, 8),
         viz={"graph.dimensions": ["country"], "graph.metrics": ["median_usd"], "graph.show_values": True},
         sql=f"""select coalesce(f.primary_country, 'Remote (no country)') as country,
       round(percentile_cont(0.5) within group (order by f.salary_annual_mid_usd)::numeric, -3) as median_usd,
       count(*) as jobs_with_salary
from {FACT}
where {where('country')} and f.has_comparable_salary
group by 1 having count(*) >= 3 order by median_usd desc limit 15"""),
    dict(key="salary_by_industry", tab="salary", name="Median salary by industry (USD / year)", display="row",
         pos=(22, 0, 24, 8),
         viz={"graph.dimensions": ["industry"], "graph.metrics": ["median_usd"], "graph.show_values": True},
         sql=f"""select f.industry,
       round(percentile_cont(0.5) within group (order by f.salary_annual_mid_usd)::numeric, -3) as median_usd,
       count(*) as jobs_with_salary
from {FACT}
where {where('industry')} and f.has_comparable_salary and f.industry <> 'Not identified'
group by 1 having count(*) >= 3 order by median_usd desc"""),
    dict(key="salary_by_skill", tab="salary",
         name="Best-paid skills: median salary of jobs that ask for the skill (USD / year)", display="row",
         pos=(30, 0, 24, 9),
         viz={"graph.dimensions": ["skill"], "graph.metrics": ["median_usd"], "graph.show_values": True},
         sql=f"""select s.skill,
       round(percentile_cont(0.5) within group (order by f.salary_annual_mid_usd)::numeric, -3) as median_usd,
       count(*) as jobs_with_salary
from {FACT} join marts.bridge_job_skills s on s.job_id = f.job_id
where {where()} and f.has_comparable_salary
group by 1 having count(*) >= 5 order by median_usd desc limit 15"""),

    # =========================== 5. Find jobs ===========================
    dict(key="job_list", tab="jobs", name="Jobs you can apply to (best skill match first)", display="table",
         pos=(2, 0, 24, 16), viz=JOB_TABLE_VIZ, sql=job_table_sql("match", 500)),
]

FILTER_ORDER = ("industry", "track", "role", "seniority", "work_mode", "country", "skill", "requirement",
                "my_skills")
TAG_LABELS = {"industry": "Industry", "track": "Track", "role": "Role", "seniority": "Seniority", "work_mode": "Work mode",
              "country": "Your country", "my_skills": "My skills", "skill": "Must-have skill",
              "requirement": "Requirements"}

# Each card's filter tags are derived from the {{variables}} its SQL uses.
for _card in CARDS:
    _card["click"] = CLICKS.get(_card["key"], {})
    _used = set(re.findall(r"\{\{(\w+)\}\}", _card["sql"]))
    _card["tags"] = [t for t in FILTER_ORDER if t in _used]


def _dropdown(pid: str, values: list[str], multi: bool = False, default: list[str] | None = None) -> dict:
    p = {"id": pid, "name": TAG_LABELS[pid], "slug": pid, "type": "string/=", "sectionId": "string",
         "isMultiSelect": multi, "values_query_type": "list", "values_source_type": "static-list",
         "values_source_config": {"values": values}}
    if default:
        p["default"] = default
    return p


def build_dashboard_parameters(skills_as_field: bool = True) -> list[dict]:
    params = [
        _dropdown("industry", seed_values("companies.csv", "industry") + ["Not identified"]),
        _dropdown("track", tracks()),
        _dropdown("role", roles()),
        _dropdown("seniority", SENIORITIES),
        _dropdown("work_mode", WORK_MODES),
        _dropdown("country", seed_values("geo_patterns.csv", "country")),
    ]
    if skills_as_field:
        params.append(_dropdown("my_skills", seed_values("skills.csv", "skill"), multi=True,
                                default=DEFAULT_MY_SKILLS))
    else:  # comma-separated text box
        params.append({"id": "my_skills", "name": "My skills (comma-separated)", "slug": "my_skills",
                       "type": "string/=", "sectionId": "string", "isMultiSelect": False,
                       "values_query_type": "none", "default": [", ".join(DEFAULT_MY_SKILLS)]})
    params[6:6] = [_dropdown("skill", seed_values("skills.csv", "skill")),
                   _dropdown("requirement", REQUIREMENTS)]
    return params


# --------------------------------------------------------------------------- #
# Building it in Metabase
# --------------------------------------------------------------------------- #
def find_skill_field(c: Client, db_id: int, wait_s: int = 180) -> int | None:
    """Field id of marts.dim_skills.skill (needed for the multi-select My skills filter)."""
    deadline = time.time() + wait_s
    synced = False
    while True:
        try:
            meta = c.call("GET", f"/api/database/{db_id}/metadata")
            for table in meta.get("tables", []):
                if table.get("schema") == "marts" and table.get("name") == "dim_skills":
                    for field in table.get("fields", []):
                        if field.get("name") == "skill":
                            return field["id"]
        except MetabaseError as exc:
            print(f"  (could not read database metadata: {exc})")
            return None
        if time.time() > deadline:
            return None
        if not synced:
            print("  Asking Metabase to scan the warehouse tables ...")
            try:
                c.call("POST", f"/api/database/{db_id}/sync_schema")
            except MetabaseError:
                return None
            synced = True
        time.sleep(10)


def click_to_filter(spec: dict) -> dict:
    """Metabase cross-filtering: clicking a bar sets the matching dashboard filter."""
    mapping = {}
    for column, param in (spec.get("click") or {}).items():
        mapping[param] = {"id": param,
                          "source": {"type": "column", "id": column, "name": column},
                          "target": {"type": "parameter", "id": param}}
    return {"click_behavior": {"type": "crossfilter", "parameterMapping": mapping}} if mapping else {}


def create_card(c: Client, db_id: int, spec: dict, skill_field_id: int | None) -> int:
    sql = spec["sql"]
    template_tags = {}
    for t in spec["tags"]:
        tag = {"id": str(uuid.uuid4()), "name": t, "display-name": TAG_LABELS[t], "type": "text"}
        if t == "my_skills":
            if skill_field_id:
                tag.update({"type": "dimension", "dimension": ["field", skill_field_id, None],
                            "widget-type": "string/="})
            else:
                sql = sql.replace(MY_SKILLS_PICKED_FIELD, MY_SKILLS_PICKED_TEXT)
        template_tags[t] = tag
    card = c.call("POST", "/api/card", {
        "name": CARD_PREFIX + spec["name"],
        "display": spec["display"],
        "visualization_settings": spec["viz"],
        "dataset_query": {
            "database": db_id,
            "type": "native",
            "native": {"query": sql, "template-tags": template_tags},
        },
    })
    return card["id"]


def _mapping(tag: str, card_id: int, skill_field_id: int | None) -> dict:
    kind = "dimension" if tag == "my_skills" and skill_field_id else "variable"
    return {"parameter_id": tag, "card_id": card_id, "target": [kind, ["template-tag", tag]]}


def create_dashboard(c: Client, db_id: int) -> int:
    skill_field_id = find_skill_field(c, db_id)
    if not skill_field_id:
        print("  (marts.dim_skills not found in Metabase yet: 'My skills' will be a comma-separated text box)")
    dash = c.call("POST", "/api/dashboard", {
        "name": DASHBOARD_NAME,
        "description": "Tech jobs (data, software, QA, UI/UX, DevOps, security): what to learn next, where the "
                       "jobs are, what they pay, and which ones to apply to. Built by scripts/setup_metabase.py.",
    })
    tab_ids = {key: -(i + 1) for i, (key, _) in enumerate(TABS)}
    tabs = [{"id": tab_ids[key], "name": name} for key, name in TABS]
    dashcards = []
    next_id = -1
    for tab, row, height, text in TEXTS:
        dashcards.append({
            "id": next_id, "card_id": None, "dashboard_tab_id": tab_ids[tab],
            "row": row, "col": 0, "size_x": 24, "size_y": height, "parameter_mappings": [],
            "visualization_settings": {
                "virtual_card": {"name": None, "display": "text", "visualization_settings": {},
                                 "dataset_query": {}, "archived": False},
                "text": text,
            },
        })
        next_id -= 1
    for i, spec in enumerate(CARDS, start=1):
        card_id = create_card(c, db_id, spec, skill_field_id)
        row, col_, size_x, size_y = spec["pos"]
        dashcards.append({
            "id": next_id, "card_id": card_id, "dashboard_tab_id": tab_ids[spec["tab"]],
            "row": row, "col": col_, "size_x": size_x, "size_y": size_y,
            # Show the clean title on the dashboard (the saved card keeps the JMR prefix,
            # which is how re-runs find and replace their own cards).
            "visualization_settings": {"card.title": spec["name"], **click_to_filter(spec)},
            "parameter_mappings": [_mapping(t, card_id, skill_field_id) for t in spec["tags"]],
        })
        next_id -= 1
        print(f"  card {i:>2}/{len(CARDS)}: [{dict(TABS)[spec['tab']]}] {spec['name']}")

    params = build_dashboard_parameters(skills_as_field=bool(skill_field_id))
    c.call("PUT", f"/api/dashboard/{dash['id']}", {"parameters": params, "tabs": tabs, "dashcards": dashcards})
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
