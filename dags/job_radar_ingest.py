"""Daily pipeline: job sources -> raw object storage -> Postgres -> dbt models.

    setup ─► sync_boards ─► extract[source] ─► load[source] ─► check ─┬─► dbt_build
                        └─► probe_companies (find each listed company's hiring platform)
             (mapped over SOURCES, one task per source)              │
    setup ─► fx_rates (ECB rates, for salary conversion) ────────────┘
                                                        load ─► discover_boards

extract: calls the source API, writes an untouched gzip JSON envelope to S3.
load:    reads that object back from S3 and upserts the daily snapshot into
         Postgres, so loads can always be replayed from the raw layer.
check:   fails the run if a source returned nothing (pipeline health check).
fx_rates: last 90 days of ECB reference rates -> S3 + raw.fx_rates. It never
          fails the run: if ECB is unreachable, dbt uses the last known rates.
dbt_build: seeds + staging/intermediate/marts models + all dbt tests.
sync_boards / discover_boards / probe_companies: the self-expanding company
          board registry (see jobradar/boards.py). None of them ever fails the run.
"""
from __future__ import annotations

import logging
from datetime import timedelta

import pendulum
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, get_current_context, task

from jobradar import boards, fx, storage, warehouse
from jobradar.sources import SOURCES, load_board_rows

log = logging.getLogger(__name__)
WAREHOUSE_CONN_ID = "jobradar_wh"


@dag(
    dag_id="job_radar_ingest",
    schedule="0 5 * * *",  # daily, 05:00 UTC
    start_date=pendulum.datetime(2026, 10, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["job-market-radar", "ingestion", "dbt"],
)
def job_radar_ingest():

    @task
    def setup() -> None:
        storage.ensure_bucket()
        conn = PostgresHook(postgres_conn_id=WAREHOUSE_CONN_ID).get_conn()
        try:
            warehouse.ensure_schema(conn)
            fx.load_rates(conn, [])  # creates raw.fx_rates even if ECB is unreachable today
            boards.ensure_schema(conn)
        finally:
            conn.close()

    @task
    def sync_boards() -> dict:
        """Add new CSV seeds, then validate a capped number of candidate boards."""
        conn = PostgresHook(postgres_conn_id=WAREHOUSE_CONN_ID).get_conn()
        try:
            seeded = boards.seed(conn, load_board_rows())
            counts = boards.validate_candidates(conn)
        except Exception as exc:  # noqa: BLE001 - extraction falls back to the CSV list
            log.warning("board sync failed (%s) - extract will use the CSV list", exc)
            return {}
        finally:
            conn.close()
        log.info("boards: %s new seeds; validation %s", seeded, counts)
        return {"seeded": seeded, **counts}

    @task
    def probe_companies() -> dict:
        """Find which hiring platform each company in dbt/seeds/companies.csv uses."""
        conn = PostgresHook(postgres_conn_id=WAREHOUSE_CONN_ID).get_conn()
        try:
            boards.seed_probes(conn, boards.load_companies())
            return boards.validate_probes(conn)
        except Exception as exc:  # noqa: BLE001 - probing is best-effort
            log.warning("company probing failed: %s", exc)
            return {}
        finally:
            conn.close()

    @task
    def discover_boards(_loaded: list[dict]) -> int:
        """Harvest board links from today's (and recent) raw payloads -> new candidates."""
        conn = PostgresHook(postgres_conn_id=WAREHOUSE_CONN_ID).get_conn()
        try:
            return boards.harvest(conn)
        except Exception as exc:  # noqa: BLE001 - discovery is best-effort
            log.warning("board discovery failed: %s", exc)
            return 0
        finally:
            conn.close()

    @task
    def extract(source: str) -> dict:
        fetched_at = pendulum.now("UTC")
        spec = SOURCES[source]
        if spec.board_ats:
            conn = PostgresHook(postgres_conn_id=WAREHOUSE_CONN_ID).get_conn()
            tokens = boards.active_tokens(conn, spec.board_ats)
            log.info("%s: %s active boards in registry", source, len(tokens))
            # empty registry (first run, or sync failed): use the CSV list
            result = spec.extract(tokens=tokens or None, meta=boards.board_meta(conn, spec.board_ats))
            if tokens:
                boards.record_extraction(conn, spec.board_ats, result.board_status)
            conn.close()
        else:
            result = spec.extract()
        key = storage.raw_key(source, fetched_at)
        envelope = {
            "source": source,
            "fetched_at": fetched_at.isoformat(),
            "snapshot_date": fetched_at.to_date_string(),
            "s3_key": key,
            "warnings": result.warnings,
            "records": result.records,
        }
        storage.put_envelope(key, envelope)
        for w in result.warnings:
            log.warning(w)
        # Only metadata goes through XCom - the data itself stays in S3.
        return {"source": source, "s3_key": key, "records": len(result.records)}

    @task
    def load(meta: dict) -> dict:
        id_fn = SOURCES[meta["source"]].job_id
        envelope = storage.get_envelope(meta["s3_key"])
        run_id = get_current_context()["run_id"]
        conn = PostgresHook(postgres_conn_id=WAREHOUSE_CONN_ID).get_conn()
        try:
            loaded = warehouse.load_snapshot(conn, envelope, id_fn, run_id)
        finally:
            conn.close()
        log.info("%s: loaded %s postings from %s", meta["source"], loaded, meta["s3_key"])
        return {**meta, "loaded": loaded}

    @task
    def check(results: list[dict]) -> None:
        for r in results:
            log.info("%-12s fetched=%-6s loaded=%s", r["source"], r["records"], r["loaded"])
        empty = [r["source"] for r in results if r["loaded"] == 0]
        failing = [s for s in empty if SOURCES[s].required]
        for s in set(empty) - set(failing):
            log.warning("%s loaded 0 postings (optional source, not failing the run)", s)
        if failing:
            raise ValueError(f"No postings loaded for required sources: {failing}")

    @task
    def fx_rates() -> int:
        fetched_at = pendulum.now("UTC")
        try:
            xml_text = fx.fetch_ecb_xml()
            rows = fx.parse_ecb_xml(xml_text)
        except Exception as exc:  # noqa: BLE001 - salary conversion falls back to last known rates
            log.warning("ECB rates not fetched (%s) - keeping existing rates", exc)
            return 0
        key = storage.raw_key("ecb_fx", fetched_at)
        storage.put_envelope(key, {"source": "ecb_fx", "fetched_at": fetched_at.isoformat(),
                                   "s3_key": key, "xml": xml_text})
        conn = PostgresHook(postgres_conn_id=WAREHOUSE_CONN_ID).get_conn()
        try:
            loaded = fx.load_rates(conn, rows)
        finally:
            conn.close()
        log.info("fx: loaded %s rate rows (%s days)", loaded, len({r[0] for r in rows}))
        return loaded

    dbt_build = BashOperator(
        task_id="dbt_build",
        # Paths and credentials come from env vars set in docker-compose.yml / .env
        bash_command="dbt build --project-dir $DBT_PROJECT_DIR --profiles-dir $DBT_PROFILES_DIR",
        retries=0,
    )

    s = setup()
    synced = sync_boards()
    s >> synced
    extracted = extract.expand(source=list(SOURCES))
    synced >> extracted
    # runs next to the extracts; boards it finds are collected from the next run on
    synced >> probe_companies()
    rates = fx_rates()
    s >> rates
    loaded = load.expand(meta=extracted)
    [check(loaded), rates] >> dbt_build
    discover_boards(loaded)


job_radar_ingest()
