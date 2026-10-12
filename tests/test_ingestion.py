"""Unit tests for the ingestion package (no network, no Docker needed).

Run from the project root:  pip install -r tests/requirements.txt && pytest
"""
from datetime import datetime, timezone

import pytest

from jobradar import sources, storage, warehouse
from jobradar.filters import is_data_role


@pytest.mark.parametrize("title", [
    "Senior Data Engineer", "Analytics Engineer (dbt)", "BI Developer",
    "Business Intelligence Analyst", "Junior Data Analyst - Remote",
    "Dateningenieur (m/w/d)", "Ingénieur Données", "Ingeniero de Datos",
    "ETL Developer", "Data Platform Engineer",
])
def test_data_roles_are_kept(title):
    assert is_data_role(title)


@pytest.mark.parametrize("title", [
    "Frontend Engineer", "Data Entry Clerk", "Data Center Technician",
    "Account Executive", "", None, "Biology Teacher",
])
def test_non_data_roles_are_dropped(title):
    assert not is_data_role(title)


def test_remotive_filter_and_id(monkeypatch):
    fake = {"jobs": [
        {"id": 1, "title": "Data Engineer", "category": "Software Development"},
        {"id": 2, "title": "Product Designer", "category": "Design"},
        {"id": 3, "title": "Insights Lead", "category": "Data Analysis"},
    ]}
    monkeypatch.setattr(sources, "_get_json", lambda url, params=None: fake)
    res = sources.extract_remotive()
    assert [sources.remotive_id(r) for r in res.records] == ["1", "3"]


def test_arbeitnow_paginates_until_no_next(monkeypatch):
    pages = {
        1: {"data": [{"slug": "a", "title": "Data Analyst"}, {"slug": "b", "title": "Chef"}],
            "links": {"next": "?page=2"}},
        2: {"data": [{"slug": "c", "title": "BI Engineer"}], "links": {"next": None}},
    }
    calls = []

    def fake_get(url, params=None):
        calls.append(params["page"])
        return pages[params["page"]]

    monkeypatch.setattr(sources, "_get_json", fake_get)
    res = sources.extract_arbeitnow(max_pages=10, pause_seconds=0)
    assert calls == [1, 2]
    assert [sources.arbeitnow_id(r) for r in res.records] == ["a", "c"]


def test_greenhouse_skips_failed_boards(monkeypatch):
    import requests

    def fake_get(url, params=None):
        if "/badco/" in url:
            raise requests.HTTPError("404")
        return {"jobs": [{"id": 7, "title": "Data Engineer"}, {"id": 8, "title": "Recruiter"}]}

    monkeypatch.setattr(sources, "_get_json", fake_get)
    res = sources.extract_greenhouse(tokens=["goodco", "badco"], pause_seconds=0)
    assert [sources.greenhouse_id(r) for r in res.records] == ["goodco:7"]
    assert len(res.warnings) == 1


def test_greenhouse_all_boards_failing_raises(monkeypatch):
    import requests

    def fake_get(url, params=None):
        raise requests.HTTPError("404")

    monkeypatch.setattr(sources, "_get_json", fake_get)
    with pytest.raises(RuntimeError):
        sources.extract_greenhouse(tokens=["x"], pause_seconds=0)


def test_board_file_parses():
    tokens = sources.load_board_tokens()
    assert tokens and all(t == t.strip().lower() and " " not in t for t in tokens)


def test_raw_key_layout():
    ts = datetime(2026, 10, 12, 5, 0, 7, tzinfo=timezone.utc)
    assert storage.raw_key("remotive", ts) == \
        "source=remotive/snapshot_date=2026-10-12/20261012T050007Z.json.gz"


def test_build_rows_dedupes_within_batch():
    env = {"source": "remotive", "snapshot_date": "2026-10-12",
           "fetched_at": "2026-10-12T05:00:00+00:00", "s3_key": "k",
           "records": [{"id": 1, "v": "old"}, {"id": 1, "v": "new"}, {"id": 2}]}
    rows = warehouse.build_rows(env, sources.remotive_id)
    assert len(rows) == 2
    assert '"new"' in [r for r in rows if r[1] == "1"][0][5]
