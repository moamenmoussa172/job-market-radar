"""Daily ingestion: job sources -> raw object storage -> Postgres raw snapshots.

    setup ──► extract[source] ──► load[source] ──► check
              (mapped over SOURCES, one task instance per source)

extract: calls the source API, writes an untouched gzip JSON envelope to S3.
load:    reads that object back from S3 and upserts the daily snapshot into
         Postgres, so loads can always be replayed from the raw layer.
check:   fails the run if a source returned nothing (pipeline health check).
"""
from __future__ import annotations

import logging
from datetime import timedelta

import pendulum
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import dag, get_current_context, task

from jobradar import storage, warehouse
from jobradar.sources import SOURCES

log = logging.getLogger(__name__)
WAREHOUSE_CONN_ID = "jobradar_wh"


@dag(
    dag_id="job_radar_ingest",
    schedule="0 5 * * *",  # daily, 05:00 UTC
    start_date=pendulum.datetime(2026, 10, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["job-market-radar", "ingestion"],
)
def job_radar_ingest():

    @task
    def setup() -> None:
        storage.ensure_bucket()
        conn = PostgresHook(postgres_conn_id=WAREHOUSE_CONN_ID).get_conn()
        try:
            warehouse.ensure_schema(conn)
        finally:
            conn.close()

    @task
    def extract(source: str) -> dict:
        extract_fn, _ = SOURCES[source]
        fetched_at = pendulum.now("UTC")
        result = extract_fn()
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
        _, id_fn = SOURCES[meta["source"]]
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
        if empty:
            raise ValueError(f"No postings loaded for: {empty}")

    extracted = extract.expand(source=list(SOURCES))
    setup() >> extracted
    check(load.expand(meta=extracted))


job_radar_ingest()
