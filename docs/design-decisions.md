# Design decisions

Short records of the choices that shaped the pipeline: the context, the decision, and its cost.

## 1. Land raw responses in object storage before parsing

**Context.** Five of the seven sources return loosely structured JSON whose fields differ per
source and drift over time (one source's free API shrank from hundreds of jobs to a 15-job sample
during development).

**Decision.** `extract` writes each response untouched (gzip JSON, partitioned by source and
snapshot date) to S3-compatible storage; `load` reads it back. All parsing happens in dbt.

**Consequence.** Parsing bugs are fixed by changing SQL and rebuilding, never by re-fetching.
Costs a little storage (~1,000 data jobs/day compress to a few MB).

## 2. Snapshot grain: source × job × day

**Context.** Sources only describe the present. Questions like "how long do jobs stay open?" and
"is demand for a skill rising?" need history.

**Decision.** `raw.job_posting_snapshots` stores one row per job per source per day (idempotent
upsert). dbt derives `first_seen_date`, `last_seen_date`, `days_listed`, `is_active`, and daily
skill trends.

**Consequence.** Activity is judged against each source's own latest snapshot, so a failed run of
one source can't mark its jobs closed. The table grows linearly; partitioning or an
Iceberg table becomes worthwhile at larger scale.

## 3. One staging shape for every source

**Decision.** Each `stg_<source>` model outputs exactly the same 23 columns (title, company,
location text, explicit workplace type, remote eligibility text, salary min/max/currency/period,
...). Everything downstream is source-agnostic; adding a source means one extractor and one
staging model.

## 4. Deduplicate jobs, but merge their attributes

**Context.** The same job is often listed on a company board (best description) and on remote
boards (structured eligibility, salary).

**Decision.** `job_id` = hash of normalized company (legal suffixes removed) + normalized title
(gender markers like "(m/w/d)" removed) + work mode + primary country. The richest source is the
survivor; lifecycle dates are merged across listings; salary comes from the best listing *that
has one* (this was a bug found by a test: the survivor often had no salary).

**Trade-off.** Two genuinely different openings with identical company/title/country collapse
into one. Acceptable for market-level analysis.

## 5. Remote eligibility as data, not a flag

**Context.** For someone outside the US/EU, "remote" is mostly not remote for them: in the data,
only a small minority of remote data jobs are open worldwide.

**Decision.** Eligibility text is mapped to countries and regions with an editable regex seed;
region terms map to several regions (EMEA → Europe, MENA, Africa); an empty restriction list on
Himalayas means worldwide. Dashboard queries answer "remote jobs open to *my* country".

## 6. Rules in seeds, with monitoring views

**Decision.** Skills, locations, salary periods and country codes are CSV seeds; role and
seniority rules are one ordered `CASE` in SQL. Two monitoring views list what the rules missed.

**Consequence.** Tuning is data-driven and reviewable. Examples from real data: the verb
"excel" was counted as the tool Excel; "culture of experimentation" counted as A/B testing;
physical warehouse jobs matched "warehouse"; ~24% of titles were unclassified until four new
role families were added.

## 7. Salary normalization with dated FX rates

**Decision.** Period labels map to a yearly multiplier (seed); currencies convert to EUR with the
ECB reference rate of the day the job was first seen (nearest earlier date, else nearest), then to
USD with the same day's rate. Values outside $5K–$1.5M/year are flagged, not deleted.

**Caveat.** Posted salaries come mostly from US employers (pay-transparency laws) and skew toward
high-paying companies; the dashboard says so and shows sample sizes.

## 8. Explicit failure policy

| Situation | Behaviour |
|---|---|
| Required source returns 0 jobs | Run fails (`check`) |
| Optional source returns little | Warning in `raw.ingestion_log` |
| One company board 404s | Warning; other boards continue; all failing → task fails |
| ECB unreachable | Warning; last known rates used |
| Any dbt test fails | `dbt_build` fails, visible in Airflow |

## 9. Dashboard as code

**Decision.** `scripts/setup_metabase.py` creates the admin user, database connection, 17 native
SQL questions and the dashboard (layout, filters, mappings) through Metabase's REST API, and
archives the previous version on re-run. Every chart's SQL is tested with and without each
optional filter.

## 10. Local-first stack

**Decision.** Docker Compose with Airflow (LocalExecutor, no Celery/Redis), Postgres, SeaweedFS
and Metabase fits a 16 GB laptop. The S3 layer and dbt project are portable to AWS S3 and a cloud
warehouse without code changes beyond connection settings.
