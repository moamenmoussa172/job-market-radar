"""Big companies' own career sites: Amazon (amazon.jobs) and Eightfold sites (Microsoft, Netflix)."""
from jobradar import boards, sources


def test_amazon_searches_each_country_pages_and_keeps_tech(monkeypatch):
    monkeypatch.setattr(sources, "WORKDAY_REGIONS", ["mena"])
    monkeypatch.setattr(sources, "MENA_COUNTRY_NAMES", ("Egypt", "Saudi Arabia"))
    calls = []

    def fake(url, params=None, headers=None):
        calls.append((params["loc_query"], params["offset"]))
        if params["loc_query"] == "Egypt":
            page = [{"id_icims": f"e{params['offset'] + i}", "title": "Data Engineer", "job_path": f"/en/jobs/e{params['offset'] + i}",
                     "city": "Cairo", "posted_date": "November 14, 2026", "job_category": "Data Science"} for i in range(100)]
            return {"hits": 150, "jobs": page if params["offset"] == 0 else page[:50]}
        return {"hits": 2, "jobs": [{"id_icims": "s1", "title": "Warehouse Associate", "job_category": "Fulfillment & Operations"},
                                    {"id_icims": "e0", "title": "Data Engineer"}]}   # same job again: kept once
    monkeypatch.setattr(sources, "_get_json", fake)
    jobs = sources._fetch_amazon()
    assert calls == [("Egypt", 0), ("Egypt", 100), ("Saudi Arabia", 0)]
    assert len(jobs) == 150 and all(j["title"] == "Data Engineer" for j in jobs)
    assert jobs[0]["job_url"] == "https://www.amazon.jobs/en/jobs/e0" and jobs[0]["searched_country"] == "Egypt"
    assert sources.amazon_id({"id_icims": "e0"}) == "amazon:e0"


def test_eightfold_small_site_reads_everything(monkeypatch):
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    seen = []

    def fake(url, params=None, headers=None):
        seen.append((url, params.get("location"), params["start"]))
        assert "/api/apply/v2/jobs" in url and params["domain"] == "netflix.com" and params["num"] == 100
        page = [{"id": params["start"] + i, "name": "Senior Software Engineer", "locations": ["Remote, United States"],
                 "t_create": 1763000000, "canonicalPositionUrl": f"/careers/job/{params['start'] + i}"} for i in range(100)]
        return {"count": 120, "positions": page if params["start"] == 0 else page[:20]}
    monkeypatch.setattr(sources, "_get_json", fake)
    jobs = sources._fetch_eightfold("explore.jobs.netflix.net|netflix.com")
    assert len(jobs) == 120 and {s[1] for s in seen} == {None}
    assert [s[2] for s in seen] == [0, 100]                      # the first page is not asked twice
    assert jobs[0]["job_url"] == "https://explore.jobs.netflix.net/careers/job/0" and jobs[0]["company"] == "Netflix"


def test_eightfold_waits_on_429_and_keeps_what_it_has(monkeypatch):
    import requests
    sources._EIGHTFOLD_KIND.clear()
    sleeps, calls = [], []
    monkeypatch.setattr(sources.time, "sleep", lambda s: sleeps.append(s))

    class R:
        status_code = 429
        headers = {"Retry-After": "5"}

    def fake(url, params=None, headers=None):
        calls.append(params["start"])
        if params["start"] == 0:
            return {"count": 300, "positions": [{"id": i, "name": "Data Engineer"} for i in range(100)]}
        raise requests.HTTPError("429", response=R())
    monkeypatch.setattr(sources, "_get_json", fake)
    jobs = sources._fetch_eightfold("explore.jobs.netflix.net|netflix.com")
    assert len(jobs) == 100                                       # the first page is kept
    assert 5 in sleeps and calls.count(100) == 3                  # waited as asked, tried twice more


def test_eightfold_giant_site_goes_country_by_country_and_falls_back_to_pcsx(monkeypatch):
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    monkeypatch.setattr(sources, "WORKDAY_REGIONS", ["mena"])
    monkeypatch.setattr(sources, "MENA_COUNTRY_NAMES", ("Egypt",))
    import requests

    def fake(url, params=None, headers=None):
        if "/api/apply/v2/jobs" in url:
            raise requests.HTTPError("403 Not authorized for PCSX")
        assert params["num"] == 10
        if params.get("location") is None:
            return {"data": {"count": 9000, "positions": []}}
        return {"data": {"count": 1, "positions": [{"id": 7, "name": "Data Scientist", "locations": ["Cairo, Egypt"],
                                                    "postedTs": 1763000000, "positionUrl": "/careers/job/7"}]}}
    monkeypatch.setattr(sources, "_get_json", fake)
    jobs = sources._fetch_eightfold("apply.careers.microsoft.com|microsoft.com")
    assert [j["id"] for j in jobs] == [7] and jobs[0]["locations"] == ["Cairo, Egypt"]


def test_eightfold_remembers_which_search_a_site_answers(monkeypatch):
    sources._EIGHTFOLD_KIND.clear()
    urls = []

    def fake(url, params=None, headers=None):
        urls.append(url.split("/api/")[1])
        if "v2" in url:
            raise sources.requests.HTTPError("403")
        return {"data": {"count": 25, "positions": [{"id": params["start"] + i, "name": "Data Engineer"} for i in range(10)]}}
    monkeypatch.setattr(sources, "_get_json", fake)
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    jobs = sources._fetch_eightfold("apply.careers.microsoft.com|microsoft.com")
    assert len(jobs) == 30 and urls.count("apply/v2/jobs") == 1    # asked the old search only once


def test_big_sites_validate_with_one_request(monkeypatch):
    monkeypatch.setattr(sources, "_get_json", lambda url, params=None, headers=None:
                        {"hits": 12000, "jobs": []} if "amazon" in url else {"count": 600, "positions": []})
    assert boards.validate_board("amazon", "amazon.jobs") == ("active", 12000)
    assert boards.validate_board("eightfold", "explore.jobs.netflix.net|netflix.com") == ("active", 600)


def test_seed_rows_include_the_big_sites():
    rows = set(sources.load_board_rows())
    assert ("amazon", "amazon.jobs") in rows
    assert ("eightfold", "apply.careers.microsoft.com|microsoft.com") in rows
