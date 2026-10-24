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
`JSEARCH_EXTRA_PER_DAY` / `JOOBLE_EXTRA_PER_DAY` (default 1) take that many of the daily searches for
`EXTRA_SEARCH_COUNTRIES` in sources.py (North Africa, Iraq, Levant, East Africa, South/Central Asia,
Caucasus, Balkans), so the total stays inside the free plans.

## Adding a country

1. `dbt/seeds/geo_patterns.csv`: a row `"\m(country|capital|city)\M",Country,Region` (plus an Arabic row
   for Arab countries). Watch for clashes (e.g. Georgia the US state: use Tbilisi/Batumi only).
2. `dbt/seeds/country_codes.csv`: its ISO code.
3. Arabic name in `seo_pages.AR_PLACES` (needed for its page) and `site/report.js`.
4. Optional: add it to `EXTRA_SEARCH_COUNTRIES` so JSearch/Jooble look for jobs there.
5. `pytest tests/test_countries.py`, then trigger the DAG (dbt reloads the seeds).

## Adding companies by hand (head-hunting)

To add a company you know is hiring, open one of its job links and add a line to
`dags/jobradar/company_boards.csv` as `ats,token,company,country`:

| Job link looks like | Line to add |
|---|---|
| `apply.workable.com/mrsool-3/j/...` | `workable,mrsool-3,Mrsool,Saudi Arabia` |
| `jobs.lever.co/Bosta/...` | `lever,bosta,Bosta,Egypt` |
| `job-boards.greenhouse.io/tamara/...` or `job-boards.eu.greenhouse.io/tamara/...` | `greenhouse,tamara,Tamara,Saudi Arabia` |
| `jobs.ashbyhq.com/qlub/...` | `ashby,qlub,qlub,United Arab Emirates` |
| `jobs.smartrecruiters.com/AlMosafer/...` | `smartrecruiters,AlMosafer,Almosafer,Saudi Arabia` |
| `anghami.breezy.hr/p/...` | `breezy,anghami,Anghami,United Arab Emirates` |
| `spidersilk.teamtailor.com/jobs/...` | `teamtailor,spidersilk,spiderSilk,Jordan` |
| `xyz.recruitee.com/o/...` / `xyz.jobs.personio.de/...` | `recruitee,xyz,...` / `personio,xyz,...` |

The next run checks each new line with one request and starts collecting from it. Listed boards that fail
are checked again every 3 days. A quick way to find more: search the web for e.g.
`site:apply.workable.com Riyadh developer` or `site:jobs.lever.co Cairo engineer`.

## Enterprise career sites (Workday, SuccessFactors)

Big employers in the Gulf and multinationals with offices in Egypt mostly use Workday or SAP SuccessFactors.
Add one as a line in `dags/jobradar/company_boards.csv` (`ats,token,company`):

* **Workday**: open any of their jobs, e.g. `https://aramco.wd3.myworkdayjobs.com/en-US/Aramco_Careers/job/...`,
  and write `workday,aramco.wd3/Aramco_Careers,Aramco` (tenant.wdN/Site; the Site part is case-sensitive).
  Only jobs in the countries of `WORKDAY_REGIONS` (default `mena,europe`) are requested, at most
  `WORKDAY_MAX_PAGES` x 20 per region, with full details for `WORKDAY_MAX_DETAILS` per board. Sites without a
  country filter are read newest-first and kept by location text (country and big-city names).
  Workday links in other sources' apply links are also picked up automatically (status *candidate*, then
  validated with one request).
* **SuccessFactors**: the career site host, e.g. `successfactors,careers.sap.com,SAP` (read from its RSS feed
  `https://<host>/services/rss/job/`, all jobs via `rows`). Sites with the feed switched off are marked dead.

Check a board quickly from your PC:

```powershell
docker compose exec airflow-scheduler python -c "from jobradar import sources; print(len(sources.ATS_FETCHERS['workday']('ag.wd3/Airbus')))"
```

See which boards work: `select ats, token, status, company_name, data_jobs_last_run from raw.company_boards where ats in ('workday','successfactors') order by status;`

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
The site is pushed with `git push --force` from inside the Airflow container (git is installed in
`airflow/Dockerfile`; the token goes in an HTTP header, never in the URL or logs). Without git it falls back to
the GitHub API, which times out once the site has a few thousand files.
Edit the site in `site/` (index.html, style.css, app.js); changes go live with the next publish.
If the token expires, the run still succeeds and logs "website not published".

### Custom domain (e.g. radarak.com)

1. At the domain registrar, DNS: four `A` records for `@` -> `185.199.108.153`, `185.199.109.153`,
   `185.199.110.153`, `185.199.111.153`, and a `CNAME` for `www` -> `moamenmoussa172.github.io`.
2. Put `SITE_DOMAIN=radarak.com` in `.env`, `docker compose up -d`, and publish once. Every publish now
   includes the `CNAME` file; without it GitHub would drop the domain when the branch is replaced.
3. GitHub: **Settings -> Pages -> Custom domain** -> `radarak.com` -> Save; when the DNS check is green,
   tick **Enforce HTTPS**. The old github.io address redirects to the new one.

### Google (Search Console)

After the first publish with the search pages, open search.google.com/search-console -> property `radarak.online`
-> **Sitemaps** -> enter `sitemap.xml` -> Submit. The sitemap is regenerated every day; no need to resubmit.
**Pages** shows what is indexed, **Performance** what people searched for.

### Radarak Weekly (newsletter)

1. Sign up free at buttondown.com (free up to 100 subscribers). Pick a username, e.g. `radarak`.
2. Buttondown -> Settings -> API -> copy the key. In `.env`: `BUTTONDOWN_API_KEY=...`, `BUTTONDOWN_USERNAME=radarak`,
   `BUTTONDOWN_STATUS=draft`, then `docker compose up -d` and publish (the subscribe box appears on the site).
3. Every Sunday's run creates the email. With `draft` it waits in Buttondown -> Emails for you to read and press
   Send; switch to `about_to_send` once you trust it. One email per week (`raw.newsletter_log`).

### Reported jobs

GoatCounter -> filter `report-closed` shows jobs visitors reported as closed or wrong (`report-closed/<id>/<company>`).
Many reports for one company usually mean its board needs a look in `raw.company_boards`.

### Trends and the weekly report

The **Trends** tab and `report.html` read `data/trends.json` (from `mart_weekly_new_jobs`,
`mart_skill_trends`, `mart_time_to_close`). They need about two weeks of history before they show numbers;
until then they say so. Each Monday (or any day), open
`https://<user>.github.io/job-market-radar/report.html`, pick a place (All, Egypt, Saudi Arabia, ...)
and a language, **Download image** and **Copy text**, and post both. The image covers the last complete week.

### Telegram channels (optional)

After each run, `post_telegram` posts the day's new jobs to Telegram channels, grouped by track, each linking
to the original posting, plus a link back to the website. A job is posted to a channel once
(`raw.telegram_posts`); a Telegram error never fails the run.

1. In Telegram, open **@BotFather**, send `/newbot`, pick a name (e.g. *Radarak Jobs*) and a username ending in
   `bot`. Copy the token it gives you.
2. Create a public channel per audience (e.g. `@radarak_egypt`, `@radarak_gulf`, `@radarak_remote`).
   In each channel: *Administrators > Add admin >* your bot, with *Post messages* allowed.
3. In `.env`:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC...
   TELEGRAM_CHANNELS=@radarak_egypt=Egypt;@radarak_gulf=Saudi Arabia|United Arab Emirates|Qatar|Kuwait|Bahrain|Oman;@radarak_remote=Remote
   ```
   A country channel gets office/hybrid jobs there plus remote jobs open to that country or region;
   `Remote` gets remote jobs open worldwide. Nationals-only jobs and Remotive/Himalayas listings are never posted.
4. `docker compose up -d` (reloads `.env`), then trigger the DAG. Check what was posted:
   `select chat, count(*), max(posted_at) from raw.telegram_posts group by 1;`

### Job pages for Google's job search

Every job from a company career site (Greenhouse, Lever, Workday, SuccessFactors, Phenom, Oracle, ...)
that has a real description (400+ characters) gets its own page, `job/<title>-at-<company>-<id>/`, with
`JobPosting` structured data, so it can appear in the job box Google shows for searches like
"data engineer jobs Cairo". Jobs from other job boards (Adzuna, Jooble, JSearch, Remote OK, ...) don't
get a page: they are those boards' listings. The pages are listed in `sitemap-jobs.xml` (linked from
`robots.txt`), and the job titles on the country / role pages link to them.

* `JOB_PAGES_MAX` (default 12000, `0` = off) limits how many; remote and Middle East / Africa jobs first.
* A page only changes when its job changes, so the daily push stays small. When a job closes, its page
  is gone the next morning (404) and Google drops it, as its guidelines ask.
* One-time: in Google Search Console -> Sitemaps, add `sitemap-jobs.xml`. Then check
  Search Console -> "Job postings" (under Enhancements) after a few days for errors and warnings.
* Test one page: https://search.google.com/test/rich-results with a job page URL.

### Getting new jobs without coming back: Telegram and RSS

* The app shows "New Egypt jobs every morning on Telegram · Join" above the job list for the visitor's
  country (or the Remote channel), and all channels in the footer. Every public `@channel` in
  `TELEGRAM_CHANNELS` is shown, but only when `TELEGRAM_BOT_TOKEN` is set (so the site never links to a
  channel nothing posts to). Visitors can hide the row. Clicks count in GoatCounter as `telegram-join/<channel>`.
* Every country and track page has an RSS feed (`feeds/egypt.xml`, `feeds/egypt/data-and-analytics.xml`,
  `feeds/remote.xml`, the 40 newest jobs) and the same Telegram button.

### Visitor analytics (optional)

The site can count visits and clicks anonymously with [GoatCounter](https://www.goatcounter.com)
(free for non-commercial sites, no cookies, so no consent banner). Sign up, choose a site code
(e.g. `radarak` -> `radarak.goatcounter.com`), put it in `.env` as `GOATCOUNTER_CODE=radarak`,
restart the scheduler and publish. The tag is added to `index.html` only at publish time.

Besides page views, the site sends these events (no personal data): `cv-read`, `cv-show-role`,
`job-open/<track>`, `save-job`, `share`, `country/<country>`, `track/<track>`, `language-<en|ar>`.
They appear under "Events" / the paths list in the GoatCounter dashboard.

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

## Testing the website (every feature, in a real browser)

`tests/e2e/test_website.py` opens the site in Chromium and checks every feature: filters and counts
(compared with counts computed from `data/jobs.json`), search, quick toggles, sorting, job panel and deep
links, save / applied / Saved tab, report-closed, WhatsApp and copy link, My skills, CV paste and PDF/Word
upload, "learn next", "new since your last visit", Arabic, all tabs, newsletter, app install files, the
data-load error message, phone layout and filter sheet, every country page (EN/AR), the filters on the
country / companies / juniors / salaries pages, the weekly report page, links, sitemap, SEO tags, asset
versions and the Remote OK followed links. It is skipped in the normal test run.

```powershell
pip install pytest playwright reportlab python-docx
python -m playwright install chromium
$env:SITE_URL="https://radarak.online"; python -m pytest tests/e2e -v
```
