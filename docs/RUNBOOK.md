# Runbook

Everything needed to run, operate and change the pipeline locally.
Commands are PowerShell (Windows); on macOS/Linux use `cp` instead of `Copy-Item`
and `\` instead of `` ` `` for line continuation.

## Services

| Service | What it does | URL |
|---|---|---|
| Airflow 3.3 (LocalExecutor) | Orchestration | http://localhost:8080 |
| Postgres 16 | Airflow metadata, `jobradar` warehouse, Metabase app DB | `localhost:5433` |
| SeaweedFS | S3-compatible raw layer (bucket `jobradar-raw`) | S3 API http://localhost:8333 |
| Metabase | Dashboard | http://localhost:3000 |

Why SeaweedFS and not MinIO: MinIO stopped publishing free Docker images in October 2025.
SeaweedFS speaks the same S3 API, so the code works unchanged against AWS S3.

## First start

```powershell
Copy-Item .env.example .env
# Edit .env and change the passwords.
# If you change S3_ACCESS_KEY / S3_SECRET_KEY, change them in infra/seaweedfs/s3.json too.
docker compose up -d --build     # first build takes a few minutes
docker compose ps                # wait until the airflow-* services show "healthy"
```

1. Open http://localhost:8080 (user/password from `AIRFLOW_ADMIN_USER` / `AIRFLOW_ADMIN_PASSWORD`).
2. Unpause `job_radar_ingest` and trigger it (or run the CLI command below).
3. Build the dashboard:

```powershell
Get-Content scripts\setup_metabase.py -Raw | docker compose exec -T `
  -e MB_ADMIN_EMAIL=you@example.com -e MB_ADMIN_PASSWORD=YourPassw0rd123 `
  airflow-scheduler python -
```

The script creates the Metabase admin on the first run and logs in on later runs. Re-running it
replaces the dashboard (old version archived), so run it again after any dashboard change.

## Company board registry

`raw.company_boards` holds every Greenhouse/Lever/Ashby/SmartRecruiters/Workable/Recruitee/Personio board the pipeline knows
(SmartRecruiters names are case-sensitive, e.g. `BoschGroup`):
`candidate` (not checked yet) -> `active` (collected daily) -> `dead` (404, or 3 failed runs in a row).
- New rows in `dags/jobradar/company_boards.csv` are picked up on the next run and validated first.
- `discover_boards` adds boards found in other sources' apply links; up to 60 are validated per run.
- Check it: `select * from monitoring.rpt_company_boards;`
- Revive a board: `update raw.company_boards set status='candidate', consecutive_failures=0 where token='...';`

## API keys (optional sources)

JSearch, Jooble and Adzuna need keys in `.env` (`JSEARCH_API_KEY`, `JOOBLE_API_KEY`,
`ADZUNA_APP_ID` + `ADZUNA_APP_KEY`). Without a key the source is skipped with a warning. Keys never
go in code or git; if a key is exposed, regenerate it. Daily budgets: `JSEARCH_REQUESTS_PER_DAY`
(default 6, fits the free 200/month), `JOOBLE_REQUESTS_PER_DAY` (default 3) and
`ADZUNA_REQUESTS_PER_DAY` (default 40). A 401/403/429 answer stops that source for the day.

## Company list and industries

`dbt/seeds/companies.csv` (company, country, industry, optional board names) does two jobs:
- **Industry** of each employer for the dashboard's Industry filter. Companies not in the list get
  an industry from keyword rules on their name (`dbt/seeds/industry_keywords.csv`), else
  "Not identified".
- **Finding each company's hiring platform.** The `probe_companies` task tries the company's likely
  board names (e.g. `mnthalan`, `mnt-halan`, or the `slugs` column) on all 7 platforms, up to
  `BOARD_PROBES_PER_RUN` requests per run. A board is kept only if its tech jobs mention the company's
  country. A company with no tech jobs today is tried again after 30 days. Rows with country
  `Global` are only used for their industry.

To add companies: add rows and run the DAG. Check what was found:
`select company_name, ats, token, status, note from raw.company_boards where origin = 'probe' and status = 'active';`

## Public website (GitHub Pages)

One-time setup:
1. Create a fine-grained token: github.com/settings/tokens?type=beta, "Only select repositories" ->
   `job-market-radar`, permission **Contents: Read and write**. Put it in `.env` as `SITE_GITHUB_TOKEN`
   (plus `SITE_REPO=moamenmoussa172/job-market-radar`, `SITE_BRANCH=gh-pages`), then `docker compose up -d`.
2. Publish once (or wait for the daily run):
   `Get-Content scripts\publish_site.py -Raw | docker compose exec -T airflow-scheduler python -`
3. On GitHub: repository **Settings -> Pages -> Build and deployment -> Deploy from a branch ->
   `gh-pages` / `(root)`**. The site appears at https://moamenmoussa172.github.io/job-market-radar/ within a minute or two.

Every successful daily run then replaces the `gh-pages` branch with one fresh commit (no growing history).
Edit the site in `site/` (index.html, style.css, app.js); changes go live with the next publish.
If the token expires, the run still succeeds and logs "website not published".

## Daily operation

- The DAG runs daily at 05:00 UTC (08:00 Cairo). The machine and Docker must be running;
  missed days are skipped (`catchup=False`), but ECB rates back-fill 90 days on the next run.
- Trigger and follow a run from the terminal:

```powershell
docker compose exec airflow-scheduler airflow dags trigger job_radar_ingest
docker compose exec airflow-scheduler airflow dags list-runs job_radar_ingest
```

- Health check after a run:

```powershell
docker compose exec postgres psql -U jobradar -d jobradar -P pager=off -c "select source, records_fetched, warnings from raw.ingestion_log where snapshot_date = current_date order by log_id desc;"
```

`warnings` lists company boards that failed (wrong token, company moved ATS) and optional
sources that returned little. Fix or remove those lines in `dags/jobradar/company_boards.csv`.

## The DAG

```
setup ──► extract[source] ──► load[source] ──► check ──┐
          (dynamic task mapping, one per source)       ├──► dbt_build
setup ──► fx_rates ────────────────────────────────────┘
```

- `extract` calls one API and writes an untouched gzip JSON envelope to
  `s3://jobradar-raw/source=<s>/snapshot_date=<date>/<timestamp>.json.gz`. Only metadata goes
  through XCom.
- `load` reads that object back and upserts `raw.job_posting_snapshots`
  (grain: source × job × day), so loads are replayable and idempotent within a day.
- `check` fails the run if a *required* source loaded nothing; optional sources only warn.
- `fx_rates` loads the last 90 days of ECB rates into `raw.fx_rates`; it never fails the run.
- `dbt_build` runs seeds, all models and all tests.

## dbt

Run by hand (same as the DAG task), e.g. after editing a seed or a model:

```powershell
docker compose exec airflow-scheduler bash -c 'dbt build --project-dir $DBT_PROJECT_DIR'
```

| Schema | Contents |
|---|---|
| `seeds` | `skills`, `geo_patterns`, `salary_periods`, `country_codes`, `companies`, `industry_keywords`, `currency_pegs`, `role_tracks` |
| `staging` | `stg_<source>`: one row per source job, identical columns for all sources |
| `intermediate` | unioned → classified (role, seniority, work mode) → geo → keyed (job_id) → deduped; `int_job_salary` |
| `marts` | `fct_job_postings`, `bridge_job_skills`, `bridge_job_regions`, `dim_skills` |
| `reporting` | small dashboard tables (skills by role, jobs by country, remote eligibility, skill pairs, trends, salary) |
| `monitoring` | `rpt_unmatched_locations`, `rpt_role_family_check` |

### Tuning the rules

| To change | Edit |
|---|---|
| Skills detected | `dbt/seeds/skills.csv` (case-insensitive Postgres regex; `\m` `\M` = word boundaries) |
| Location → country/region | `dbt/seeds/geo_patterns.csv` (check `monitoring.rpt_unmatched_locations`) |
| Role families | `dbt/models/intermediate/int_postings_classified.sql` (check `monitoring.rpt_role_family_check`) |
| Role → track grouping | `dbt/seeds/role_tracks.csv` |
| Which titles are collected | `dags/jobradar/filters.py` (`is_tech_role`) |
| Salary period labels | `dbt/seeds/salary_periods.csv` |
| Companies collected | `dags/jobradar/company_boards.csv` (known boards), `dbt/seeds/companies.csv` (platform detected automatically) |
| Industries | `dbt/seeds/companies.csv`, `dbt/seeds/industry_keywords.csv` |

## Applying code changes

1. Close the changed files in your editor, or turn **Auto Save** off: an open editor tab can write
   the old version back over an updated file.
2. Replace the files, then confirm the container sees them, e.g.
   `docker compose exec airflow-scheduler grep -c <new-word> /opt/airflow/dags/jobradar/sources.py`.
3. Python/DAG changes: `docker compose restart airflow-scheduler airflow-dag-processor`, wait a
   minute, then trigger. dbt-only changes: just run dbt (above). Dockerfile/compose changes:
   `docker compose up -d --build`.

## Troubleshooting

- **Port already in use** (8080, 3000, 5433, 8333, 9333): change the left-hand port in
  `docker-compose.yml`, e.g. `"8081:8080"`.
- **`jobradar` or `metabase` database missing**: Postgres init scripts only run on an empty volume.
  `docker compose down -v` (deletes all data) and start again.
- **Scripts fail with `\r` errors**: files must keep Linux line endings; `.gitattributes`
  enforces this for git.
- **A run used old code**: the DAG processor hadn't reloaded yet. Restart it (above) and trigger again.

## Tests

```powershell
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r tests/requirements.txt
pytest
```
