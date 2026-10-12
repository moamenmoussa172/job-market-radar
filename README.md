# Job Market Radar

Data jobs you can actually get from where you live.

A daily pipeline that collects data engineering, analytics and BI job
postings (remote worldwide, plus onsite in Europe and beyond) and turns them
into decisions: **what to learn next** and **where to apply**.

## Architecture

```
job sources ──► raw layer (S3, immutable JSON) ──► Postgres raw snapshots
                                                       │
                     (next) dbt silver: dedup, skills, seniority, remote scope, salary
                     (next) dbt gold: star schema ──► Metabase dashboard
```

| Service | What it does | URL on your PC |
|---|---|---|
| Airflow 3.3 (LocalExecutor) | Orchestration | http://localhost:8080 |
| Postgres 16 | Airflow metadata, `jobradar` warehouse, Metabase app DB | `localhost:5433` |
| SeaweedFS | S3-compatible raw layer (bucket `jobradar-raw`) | S3 API `http://localhost:8333` |
| Metabase | Dashboards | http://localhost:3000 |

> Why SeaweedFS and not MinIO? MinIO stopped publishing free Docker images in
> October 2025, so `minio/minio` no longer pulls. SeaweedFS speaks the same
> S3 API, so code written here works unchanged against AWS S3 later.

## Sources (phase 1)

| Source | Covers | Notes |
|---|---|---|
| Remotive | Remote jobs, with `candidate_required_location` | Max ~4 calls/day. Keep job links and credit Remotive. |
| Arbeitnow | Europe (onsite + remote), visa sponsorship flag | Newest-first pages; first 10 pages per run |
| Greenhouse boards | Company career pages (full descriptions) | Edit `dags/jobradar/greenhouse_boards.txt` |

Only data-related titles are landed (see `dags/jobradar/filters.py`,
which also matches German, French, Spanish and Dutch titles).

## Run it on Windows

Prerequisites: Docker Desktop running (WSL2 backend), about 6 GB free RAM for Docker.

```powershell
cd job-market-radar
Copy-Item .env.example .env
# Edit .env and change the passwords.
# If you change S3_ACCESS_KEY / S3_SECRET_KEY, change them in infra/seaweedfs/s3.json too.

docker compose up -d --build     # first build takes a few minutes
docker compose ps                # wait until airflow-* show "healthy"
```

Then:

1. Open http://localhost:8080 and log in with `AIRFLOW_ADMIN_USER` / `AIRFLOW_ADMIN_PASSWORD`.
2. Unpause the DAG `job_radar_ingest` and click **Trigger**.
3. When it's green, check the data:

```powershell
docker compose exec postgres psql -U jobradar -d jobradar -c "select source, count(*) from raw.job_posting_snapshots group by 1;"
docker compose exec postgres psql -U jobradar -d jobradar -c "select * from raw.ingestion_log order by log_id desc limit 10;"
```

To connect from DBeaver or VS Code: host `localhost`, port `5433`,
database `jobradar`, user and password from `.env`.

### Common issues

- **Port already in use** (8080, 3000, 5433, 8333, 9333): change the left-hand
  port in `docker-compose.yml`, e.g. `"8081:8080"`.
- **Init script did not create `jobradar`**: Postgres init scripts only run on
  an empty volume. Run `docker compose down -v` (deletes data) and start again.
- **Scripts fail with `\r` errors**: the files must keep Linux line endings.
  `.gitattributes` enforces this for git; don't re-save files with CRLF.

## The DAG

```
setup ──► extract[remotive|arbeitnow|greenhouse] ──► load[...] ──► check
```

- `extract` calls the API and writes an untouched gzip JSON envelope to
  `s3://jobradar-raw/source=<s>/snapshot_date=<date>/<timestamp>.json.gz`.
  Only metadata goes through XCom.
- `load` reads the object back from S3 and upserts into
  `raw.job_posting_snapshots` (grain: source × job × day). This makes loads
  replayable from the raw layer and idempotent within a day.
- `check` fails the run if any source loaded zero postings. Every load is
  recorded in `raw.ingestion_log`.

Seeing the same job on consecutive days is what gives `first_seen`,
`last_seen` and `days_open` later.

## Tests

```powershell
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r tests/requirements.txt
pytest
```

## Roadmap

- [x] Phase 1a: stack, raw layer, daily snapshots, ingestion log
- [ ] Phase 1b: dbt silver (dedup, role, seniority, remote scope, skills taxonomy seed)
- [ ] Phase 1c: dbt gold star schema + first Metabase dashboard
- [ ] Phase 2: Lever, Ashby, Adzuna; salary normalization (USD/EUR); next-best-skill
- [ ] Phase 3: Iceberg + PySpark for the silver layer, public dashboard, weekly report
