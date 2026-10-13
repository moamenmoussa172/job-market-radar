"""ECB euro reference exchange rates (free, no key, published ~16:00 CET on
working days). We pull the last-90-days file every run: it is tiny, and it
back-fills any days the pipeline missed (PC off, ECB holiday, ...).

Rates are "units of currency per 1 EUR"; EUR itself is added with rate 1.
The ECB publishes these for information purposes, which is exactly our use.
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

import requests

log = logging.getLogger(__name__)

ECB_90D_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
USER_AGENT = "job-market-radar/0.1 (personal data engineering project)"

DDL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE IF NOT EXISTS raw.fx_rates (
    rate_date      date        NOT NULL,
    currency       text        NOT NULL,
    units_per_eur  numeric     NOT NULL,
    loaded_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (rate_date, currency)
);
"""

UPSERT_SQL = """
INSERT INTO raw.fx_rates (rate_date, currency, units_per_eur)
VALUES (%s, %s, %s)
ON CONFLICT (rate_date, currency) DO UPDATE
SET units_per_eur = EXCLUDED.units_per_eur, loaded_at = now();
"""


def fetch_ecb_xml(url: str = ECB_90D_URL) -> str:
    resp = requests.get(url, timeout=60, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return resp.text


def parse_ecb_xml(xml_text: str) -> list[tuple[str, str, float]]:
    """-> [(rate_date, currency, units_per_eur)], namespace-agnostic."""
    root = ET.fromstring(xml_text)
    rows: list[tuple[str, str, float]] = []
    for day in root.iter():
        rate_date = day.attrib.get("time")
        if not rate_date:
            continue
        rows.append((rate_date, "EUR", 1.0))
        for cube in day:
            cur, rate = cube.attrib.get("currency"), cube.attrib.get("rate")
            if cur and rate:
                rows.append((rate_date, cur.upper(), float(rate)))
    return rows


def load_rates(conn, rows: list[tuple[str, str, float]]) -> int:
    with conn.cursor() as cur:
        cur.execute(DDL)
        if rows:
            cur.executemany(UPSERT_SQL, rows)
    conn.commit()
    return len(rows)
