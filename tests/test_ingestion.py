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
    "ETL Developer", "Data Platform Engineer", "Data Warehouse Lead", "DWH Operations Engineer",
])
def test_data_roles_are_kept(title):
    assert is_data_role(title)


@pytest.mark.parametrize("title", [
    "Frontend Engineer", "Data Entry Clerk", "Data Center Technician",
    "Account Executive", "", None, "Biology Teacher",
    "Warehouse Associate II", "Head of Warehouse Operations (f/m/x)",
    "Schichtleiter Warehouse Operations (all genders)", "Operations Manager, Warehouse",
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


def test_jobicy_keeps_industry_feed_and_dedupes(monkeypatch):
    fake = {"jobs": [{"id": 9, "jobTitle": "ML Engineer"}, {"id": 9, "jobTitle": "ML Engineer"},
                     {"id": 10, "jobTitle": "Data Analyst", "jobGeo": "Europe"}]}
    monkeypatch.setattr(sources, "_get_json", lambda url, params=None: fake)
    res = sources.extract_jobicy(pause_seconds=0)
    assert sorted(sources.jobicy_id(r) for r in res.records) == ["10", "9"]


def test_himalayas_paginates_filters_and_dedupes(monkeypatch):
    full_page = [{"guid": f"g{i}", "title": "Data Engineer"} for i in range(20)]
    last_page = [{"guid": "g0", "title": "Data Engineer"}, {"guid": "x", "title": "Nurse"}]
    calls = []

    def fake_get(url, params=None):
        calls.append((params["q"], params["page"]))
        return {"jobs": full_page if params["page"] == 1 else last_page}

    monkeypatch.setattr(sources, "_get_json", fake_get)
    res = sources.extract_himalayas(queries=["data engineer"], max_pages=5, pause_seconds=0)
    assert calls == [("data engineer", 1), ("data engineer", 2)]  # stops on short page
    assert len(res.records) == 20  # g0 deduped, nurse filtered out


def test_all_sources_registered():
    assert set(sources.SOURCES) == {"remotive", "jobicy", "himalayas", "arbeitnow", "greenhouse", "lever", "ashby"}


def test_only_remotive_is_optional():
    assert [s for s, spec in sources.SOURCES.items() if not spec.required] == ["remotive"]


def test_board_file_parses():
    for ats in ("greenhouse", "lever", "ashby"):
        tokens = sources.load_board_tokens(ats)
        assert tokens and all(t == t.strip().lower() and " " not in t for t in tokens), ats


def test_lever_falls_back_to_eu_and_filters(monkeypatch):
    import requests
    calls = []

    def fake_get(url, params=None):
        calls.append(url)
        if "api.lever.co" in url:
            raise requests.HTTPError("404")
        return [{"id": "a1", "text": "Senior Data Engineer", "workplaceType": "remote"},
                {"id": "a2", "text": "Account Executive"}]

    monkeypatch.setattr(sources, "_get_json", fake_get)
    res = sources.extract_lever(tokens=["acme"], pause_seconds=0)
    assert [sources.lever_id(r) for r in res.records] == ["acme:a1"]
    assert any("api.eu.lever.co" in u for u in calls)


def test_ashby_skips_unlisted_and_uses_job_url_as_id(monkeypatch):
    fake = {"jobs": [
        {"title": "Analytics Engineer", "jobUrl": "https://jobs.ashbyhq.com/acme/1", "isListed": True},
        {"title": "Data Engineer", "jobUrl": "https://jobs.ashbyhq.com/acme/2", "isListed": False},
        {"title": "Designer", "jobUrl": "https://jobs.ashbyhq.com/acme/3"},
    ]}
    monkeypatch.setattr(sources, "_get_json", lambda url, params=None: fake)
    res = sources.extract_ashby(tokens=["acme"], pause_seconds=0)
    assert [sources.ashby_id(r) for r in res.records] == ["acme:https://jobs.ashbyhq.com/acme/1"]


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


ECB_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <gesmes:subject>Reference rates</gesmes:subject>
  <Cube>
    <Cube time="2026-10-12"><Cube currency="USD" rate="1.0921"/><Cube currency="GBP" rate="0.8450"/></Cube>
    <Cube time="2026-10-09"><Cube currency="USD" rate="1.0900"/></Cube>
  </Cube>
</gesmes:Envelope>"""


def test_parse_ecb_xml_adds_eur_and_all_days():
    from jobradar import fx
    rows = fx.parse_ecb_xml(ECB_SAMPLE)
    assert ("2026-10-12", "USD", 1.0921) in rows
    assert ("2026-10-12", "EUR", 1.0) in rows
    assert ("2026-10-09", "EUR", 1.0) in rows
    assert len(rows) == 5
