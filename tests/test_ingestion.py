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
    # tech-wide scope: the product designer is kept; "Insights Lead" is not a tech title
    assert [sources.remotive_id(r) for r in res.records] == ["1", "2"]


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
    res = sources.extract_jobicy(pause_seconds=0, tags=[])
    assert sorted(sources.jobicy_id(r) for r in res.records) == ["10", "9"]


def test_jobicy_tag_search_keeps_only_data_titles(monkeypatch):
    def fake_get(url, params=None):
        if "industry" in params:
            return {"jobs": [{"id": 1, "jobTitle": "ML Engineer"}]}
        return {"jobs": [{"id": 2, "jobTitle": "Senior Data Engineer"}, {"id": 3, "jobTitle": "Sales Manager"},
                         {"id": 1, "jobTitle": "ML Engineer"}]}

    monkeypatch.setattr(sources, "_get_json", fake_get)
    res = sources.extract_jobicy(pause_seconds=0, tags=["data engineer"])
    assert sorted(sources.jobicy_id(r) for r in res.records) == ["1", "2"]


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
    assert set(sources.SOURCES) == {"remotive", "jobicy", "himalayas", "arbeitnow", "greenhouse", "lever",
                                    "ashby", "jsearch", "jooble", "smartrecruiters", "workable",
                                    "recruitee", "personio", "adzuna"}


def test_optional_sources():
    assert {s for s, spec in sources.SOURCES.items() if not spec.required} == {
        "remotive", "jsearch", "jooble", "smartrecruiters", "workable", "recruitee", "personio", "adzuna"}


def test_daily_slice_rotates_through_every_pair():
    import datetime as dt
    pairs = list(range(28))
    seen = set()
    for d in range(5):
        today = sources.daily_slice(pairs, 6, dt.date(2026, 10, 13) + dt.timedelta(days=d))
        assert len(today) == 6 and len(set(today)) == 6
        seen.update(today)
    assert seen == set(pairs)
    assert sources.daily_slice([], 6) == []


def test_keyless_sources_skip_without_calling(monkeypatch):
    monkeypatch.delenv("JSEARCH_API_KEY", raising=False)
    monkeypatch.delenv("JOOBLE_API_KEY", raising=False)
    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.setenv("ADZUNA_APP_KEY", "only-the-key")
    monkeypatch.setattr(sources, "_get_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    for fn in (sources.extract_jsearch, sources.extract_jooble, sources.extract_adzuna):
        res = fn()
        assert res.records == [] and "not set" in res.warnings[0]


def test_jsearch_filters_dedupes_and_sends_key(monkeypatch):
    monkeypatch.setenv("JSEARCH_API_KEY", "k123")
    calls = []

    def fake_get(url, params=None, headers=None):
        calls.append((params, headers))
        return {"status": "OK", "data": [
            {"job_id": "j1", "job_title": "Data Engineer", "job_publisher": "LinkedIn"},
            {"job_id": "j1", "job_title": "Data Engineer", "job_publisher": "LinkedIn"},
            {"job_id": "j2", "job_title": "Nurse"},
        ]}

    monkeypatch.setattr(sources, "_get_json", fake_get)
    res = sources.extract_jsearch(pairs=[("data engineer", "eg", "Egypt")], pause_seconds=0)
    assert [sources.jsearch_id(r) for r in res.records] == ["j1"]
    assert calls[0][1] == {"x-api-key": "k123"}
    assert calls[0][0] == {"query": "data engineer jobs in Egypt", "country": "eg"}


def test_jsearch_stops_on_quota(monkeypatch):
    import requests
    monkeypatch.setenv("JSEARCH_API_KEY", "k")
    calls = []

    def fake_get(url, params=None, headers=None):
        calls.append(1)
        resp = requests.Response(); resp.status_code = 429
        raise requests.HTTPError("429", response=resp)

    monkeypatch.setattr(sources, "_get_json", fake_get)
    res = sources.extract_jsearch(pairs=[("a", "eg", "Egypt"), ("b", "ae", "UAE")], pause_seconds=0)
    assert len(calls) == 1 and res.records == [] and len(res.warnings) == 1


def test_jooble_posts_and_filters(monkeypatch):
    monkeypatch.setenv("JOOBLE_API_KEY", "jk")
    seen = {}

    def fake_post(url, body):
        seen["url"], seen["body"] = url, body
        return {"totalCount": 2, "jobs": [
            {"id": 11, "title": "Senior Data Analyst", "location": "Cairo", "link": "l1"},
            {"id": 12, "title": "Driver", "location": "Cairo", "link": "l2"}]}

    monkeypatch.setattr(sources, "_post_json", fake_post)
    res = sources.extract_jooble(pairs=[("data analyst", "Egypt")], pause_seconds=0)
    assert [sources.jooble_id(r) for r in res.records] == ["11"]
    assert seen["url"].endswith("/api/jk") and seen["body"]["location"] == "Egypt"


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


# ---------------------------------------------------------------- company board registry
def test_tokens_harvested_from_apply_links():
    from jobradar import boards
    text = ('{"applicationLink": "https://boards.greenhouse.io/Acme/jobs/123", '
            '"x": "https://job-boards.eu.greenhouse.io/embed/job_board?for=zeta-labs", '
            '"y": "https://jobs.lever.co/plaid-inc/abc-123", "z": "https://jobs.eu.lever.co/mistral/1", '
            '"w": "https://jobs.ashbyhq.com/posthog/9f8e", "bad": "https://boards.greenhouse.io/embed/x", '
            '"sr": "https://jobs.smartrecruiters.com/BoschGroup/7440000-data-engineer", '
            '"wk": "https://apply.workable.com/acme-data/j/ABC123/", "wk2": "https://apply.workable.com/j/XYZ"}')
    assert boards.tokens_in_text(text) == {
        ("greenhouse", "acme"), ("greenhouse", "zeta-labs"),
        ("lever", "plaid-inc"), ("lever", "mistral"), ("ashby", "posthog"),
        ("smartrecruiters", "BoschGroup"), ("workable", "acme-data"),
    }


def test_validate_board_outcomes(monkeypatch):
    import requests
    from jobradar import boards

    def resp(code):
        r = requests.Response(); r.status_code = code
        return requests.HTTPError(str(code), response=r)

    outcomes = {"ok": [{"title": "Data Engineer"}], "gone": resp(404), "flaky": resp(503)}

    def fake_fetch(token):
        o = outcomes[token]
        if isinstance(o, Exception):
            raise o
        return o

    monkeypatch.setitem(sources.ATS_FETCHERS, "greenhouse", fake_fetch)
    assert boards.validate_board("greenhouse", "ok") == ("active", 1)
    assert boards.validate_board("greenhouse", "gone") == ("dead", None)
    assert boards.validate_board("greenhouse", "flaky") == ("retry", None)


def test_board_extract_reports_status_per_board(monkeypatch):
    import requests

    def fake_get(url, params=None):
        if "/bad/" in url:
            raise requests.HTTPError("404")
        return {"jobs": [{"id": 1, "title": "Data Analyst"}, {"id": 2, "title": "Chef"}]}

    monkeypatch.setattr(sources, "_get_json", fake_get)
    res = sources.extract_greenhouse(tokens=["good", "bad"], pause_seconds=0)
    assert res.board_status == {"good": 1, "bad": None}


def test_smartrecruiters_lists_then_fetches_details_for_data_roles(monkeypatch):
    calls = []

    def fake_get(url, params=None):
        calls.append(url)
        if url.endswith("/postings"):
            return {"totalFound": 2, "content": [{"id": "1", "name": "Senior Data Engineer"},
                                                 {"id": "2", "name": "Store Manager"}]}
        return {"id": "1", "name": "Senior Data Engineer", "jobAd": {"sections": {}}}

    monkeypatch.setattr(sources, "_get_json", fake_get)
    res = sources.extract_smartrecruiters(tokens=["BoschGroup"], pause_seconds=0)
    assert [sources.smartrecruiters_id(r) for r in res.records] == ["BoschGroup:1"]
    assert calls[-1].endswith("/companies/BoschGroup/postings/1")  # case kept, details fetched


def test_workable_filters_and_rejects_non_boards(monkeypatch):
    from jobradar import boards
    pages = {"good": {"name": "Acme", "jobs": [{"title": "Data Analyst", "shortcode": "A1"},
                                               {"title": "Chef", "shortcode": "B2"}]},
             "notaboard": {"error": "not found"}}
    monkeypatch.setattr(sources, "_get_json", lambda url, params=None: pages[url.rsplit("/", 1)[1]])
    res = sources.extract_workable(tokens=["good"], pause_seconds=0)
    assert [sources.workable_id(r) for r in res.records] == ["good:A1"]
    assert boards.validate_board("workable", "notaboard") == ("dead", None)


def test_csv_rows_are_valid():
    rows = sources.load_board_rows()
    assert len(rows) > 40 and all(a in sources.BOARD_ATS for a, _ in rows)


# ---------------------------------------------------------------- update 17
PERSONIO_XML = """<?xml version="1.0" encoding="UTF-8"?>
<workzag-jobs>
  <position>
    <id>111</id><subcompany>Acme GmbH</subcompany><office>Berlin</office>
    <additionalOffices><office>Munich</office></additionalOffices>
    <department>Tech</department><name>Senior Data Engineer (m/w/d)</name>
    <jobDescriptions><jobDescription><name>Your tasks</name><value><![CDATA[<p>Spark &amp; dbt</p>]]></value></jobDescription></jobDescriptions>
    <employmentType>permanent</employmentType><seniority>experienced</seniority>
    <createdAt>2026-10-01T10:00:00+00:00</createdAt>
  </position>
  <position><id>222</id><office>Berlin</office><name>Office Manager</name></position>
</workzag-jobs>"""


def test_personio_parses_xml_filters_and_builds_url(monkeypatch):
    monkeypatch.setattr(sources, "_get_text", lambda url, params=None: PERSONIO_XML)
    res = sources.extract_personio(tokens=["acme"], pause_seconds=0,
                                   meta={"acme": {"company": "Acme", "country": "Germany"}})
    assert [sources.personio_id(r) for r in res.records] == ["acme:111"]
    rec = res.records[0]
    assert rec["additionalOffices"] == ["Munich"]
    assert rec["jobDescriptions"][0]["value"] == "<p>Spark &amp; dbt</p>"
    assert rec["job_url"] == "https://acme.jobs.personio.de/job/111"
    assert rec["board_company"] == "Acme" and rec["board_country"] == "Germany"


def test_personio_non_feed_is_not_a_board(monkeypatch):
    from jobradar import boards
    monkeypatch.setattr(sources, "_get_text", lambda url, params=None: "<html><body>hi</body></html>")
    assert boards.validate_board("personio", "nothere") == ("dead", None)


def test_recruitee_filters_offers(monkeypatch):
    fake = {"offers": [{"id": 1, "title": "Backend Engineer", "country_code": "EG"},
                       {"id": 2, "title": "Accountant"}]}
    monkeypatch.setattr(sources, "_get_json", lambda url, params=None: fake)
    res = sources.extract_recruitee(tokens=["acme"], pause_seconds=0)
    assert [sources.recruitee_id(r) for r in res.records] == ["acme:1"]


def test_adzuna_sends_both_keys_filters_and_stops_on_quota(monkeypatch):
    import requests
    monkeypatch.setenv("ADZUNA_APP_ID", "id1")
    monkeypatch.setenv("ADZUNA_APP_KEY", "key1")
    calls = []

    def fake_get(url, params=None, headers=None):
        calls.append((url, params))
        if len(calls) == 2:
            r = requests.Response(); r.status_code = 429
            raise requests.HTTPError("quota", response=r)
        return {"results": [{"id": 9, "title": "<strong>Data</strong> Engineer"}, {"id": 8, "title": "Nurse"}]}
    monkeypatch.setattr(sources, "_get_json", fake_get)
    res = sources.extract_adzuna(pairs=[("data engineer", "de"), ("qa engineer", "gb"), ("x", "nl")],
                                 pause_seconds=0)
    assert len(calls) == 2  # stopped after the 429
    assert calls[0][0].endswith("/jobs/de/search/1")
    assert calls[0][1]["app_id"] == "id1" and calls[0][1]["app_key"] == "key1"
    assert [r["id"] for r in res.records] == [9] and "429" in res.warnings[0]


def test_new_ats_tokens_harvested():
    from jobradar import boards
    text = "apply at https://acme.recruitee.com/o/data-engineer or https://beta-co.jobs.personio.de/job/1"
    assert {("recruitee", "acme"), ("personio", "beta-co")} <= boards.tokens_in_text(text)
    assert not boards.tokens_in_text("https://www.recruitee.com/")


def test_probe_tokens_cover_every_platform():
    from jobradar import boards
    pairs = boards.probe_tokens("Delivery Hero")
    assert ("greenhouse", "deliveryhero") in pairs and ("lever", "delivery-hero") in pairs
    assert ("smartrecruiters", "DeliveryHero") in pairs
    assert {a for a, _ in pairs} == set(sources.BOARD_ATS)
    assert boards.probe_tokens("Bosch", "BoschGroup") == [(a, "BoschGroup" if a == "smartrecruiters" else "boschgroup")
                                                          for a in sources.BOARD_ATS]


def test_probe_checks_the_country(monkeypatch):
    from jobradar import boards
    jobs = {"egy": [{"title": "Data Engineer", "location": {"name": "Cairo, Egypt"}}],
            "other": [{"title": "Data Engineer", "location": {"name": "Austin, TX"}}],
            "empty": []}
    monkeypatch.setitem(sources.ATS_FETCHERS, "greenhouse", lambda token: jobs[token])
    assert boards.probe_board("greenhouse", "egy", "Egypt") == ("active", None)
    assert boards.probe_board("greenhouse", "other", "Egypt")[0] == "dead"
    assert boards.probe_board("greenhouse", "empty", "Egypt")[0] == "candidate"
    # "uae" must be a whole word, not part of another word
    assert not boards.matches_country([{"t": "Guaeco"}], "United Arab Emirates")
    assert boards.matches_country([{"t": "Remote - MENA"}], "Saudi Arabia")


def test_company_list_is_valid():
    from jobradar import boards
    rows = boards.load_companies()
    assert len(rows) > 200
    countries = {r["country"] for r in rows}
    assert {"Egypt", "United Arab Emirates", "Saudi Arabia", "Qatar"} <= countries
    assert countries <= set(boards.COUNTRY_KEYWORDS) | {"Global"}
    assert all(r["industry"] for r in rows)
