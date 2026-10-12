"""Postgres raw schema: daily snapshots of every posting + an ingestion log.

Grain of raw.job_posting_snapshots: one row per (source, source_job_id, snapshot_date).
Seeing the same job on consecutive days is what later gives us
first_seen / last_seen / days_open in the silver layer.
"""
from __future__ import annotations

import json

DDL = """
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.job_posting_snapshots (
    source          text        NOT NULL,
    source_job_id   text        NOT NULL,
    snapshot_date   date        NOT NULL,
    fetched_at      timestamptz NOT NULL,
    s3_key          text        NOT NULL,
    payload         jsonb       NOT NULL,
    loaded_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source, source_job_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS raw.ingestion_log (
    log_id           bigserial   PRIMARY KEY,
    dag_run_id       text,
    source           text        NOT NULL,
    snapshot_date    date        NOT NULL,
    fetched_at       timestamptz NOT NULL,
    s3_key           text        NOT NULL,
    records_fetched  integer     NOT NULL,
    records_loaded   integer     NOT NULL,
    warnings         jsonb       NOT NULL DEFAULT '[]'::jsonb,
    logged_at        timestamptz NOT NULL DEFAULT now()
);
"""

UPSERT_SQL = """
INSERT INTO raw.job_posting_snapshots
    (source, source_job_id, snapshot_date, fetched_at, s3_key, payload)
VALUES (%s, %s, %s, %s, %s, %s::jsonb)
ON CONFLICT (source, source_job_id, snapshot_date) DO UPDATE
SET fetched_at = EXCLUDED.fetched_at,
    s3_key     = EXCLUDED.s3_key,
    payload    = EXCLUDED.payload,
    loaded_at  = now();
"""

LOG_SQL = """
INSERT INTO raw.ingestion_log
    (dag_run_id, source, snapshot_date, fetched_at, s3_key,
     records_fetched, records_loaded, warnings)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb);
"""


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()


def build_rows(envelope: dict, id_fn) -> list[tuple]:
    """Turn a raw envelope into upsert rows, de-duplicating within the batch."""
    rows: dict[str, tuple] = {}
    for record in envelope["records"]:
        job_id = id_fn(record)
        rows[job_id] = (
            envelope["source"],
            job_id,
            envelope["snapshot_date"],
            envelope["fetched_at"],
            envelope["s3_key"],
            json.dumps(record, ensure_ascii=False),
        )
    return list(rows.values())


def load_snapshot(conn, envelope: dict, id_fn, dag_run_id: str | None) -> int:
    rows = build_rows(envelope, id_fn)
    with conn.cursor() as cur:
        if rows:
            cur.executemany(UPSERT_SQL, rows)
        cur.execute(
            LOG_SQL,
            (
                dag_run_id,
                envelope["source"],
                envelope["snapshot_date"],
                envelope["fetched_at"],
                envelope["s3_key"],
                len(envelope["records"]),
                len(rows),
                json.dumps(envelope.get("warnings", [])),
            ),
        )
    conn.commit()
    return len(rows)
