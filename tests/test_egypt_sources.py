"""Egypt employers: Vodafone/_VOIS (SuccessFactors), Orange (Phenom), and company-name searches."""
import datetime as dt

import pytest

from jobradar import sources


class _Resp:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def _phenom_answer(jobs, total):
    return {"refineSearch": {"status": 200, "totalHits": total, "data": {"jobs": jobs}}}


def test_phenom_reads_egypt_jobs_and_builds_links(monkeypatch):
    bodies = []
    page1 = [{"jobId": "OR-1", "title": "Data Engineer", "location": "Cairo, Cairo, Egypt", "country": "Egypt"},
             {"jobId": "OR-2", "title": "Retail Agent", "location": "Giza, Egypt", "country": "Egypt"},
             {"jobId": "OR-3", "title": "DevOps Engineer", "location": "Smart Village, Egypt", "country": "Egypt"}]

    def post(url, json=None, **kw):
        bodies.append((url, json))
        return _Resp(_phenom_answer(page1 if json["from"] == 0 else [], 3))
    monkeypatch.setattr(sources.requests, "post", post)
    jobs = sources._fetch_phenom("orange.jobs/gb/en?Egypt")
    assert [j["jobId"] for j in jobs] == ["OR-1", "OR-3"]                       # tech roles only
    assert jobs[0]["job_url"] == "https://orange.jobs/gb/en/job/OR-1"
    url, body = bodies[0]
    assert url == "https://orange.jobs/widgets" and body["ddoKey"] == "refineSearch"
    assert body["lang"] == "en_gb" and body["selected_fields"] == {"country": ["Egypt"]}
    assert sources.phenom_id({**jobs[0], "board_token": "orange.jobs/gb/en?Egypt"}) == "orange.jobs/gb/en?Egypt:OR-1"


def test_phenom_falls_back_to_whole_site_when_country_filter_finds_nothing(monkeypatch):
    calls = []

    def post(url, json=None, **kw):
        calls.append(json["selected_fields"])
        if json["selected_fields"]:
            return _Resp(_phenom_answer([], 0))
        jobs = [{"jobId": "X1", "title": "Software Engineer", "location": "Cairo, Egypt"}] if json["from"] == 0 else []
        return _Resp(_phenom_answer(jobs, 1))
    monkeypatch.setattr(sources.requests, "post", post)
    assert [j["jobId"] for j in sources._fetch_phenom("orange.jobs/gb/en?Egypt")] == ["X1"]
    assert calls[0] == {"country": ["Egypt"]} and calls[1] == {}


def test_phenom_pages_until_total_and_stops_on_repeats(monkeypatch):
    def post(url, json=None, **kw):
        n = json["from"]
        jobs = [{"jobId": f"J{n + i}", "title": "Data Analyst"} for i in range(sources.PHENOM_PAGE)] if n < 250 else []
        return _Resp(_phenom_answer(jobs, 250))
    monkeypatch.setattr(sources.requests, "post", post)
    assert len(sources._fetch_phenom("careers.example.com/us/en")) == 300   # 3 pages (offset passes 250)


def test_phenom_rejects_non_job_answers(monkeypatch):
    monkeypatch.setattr(sources.requests, "post", lambda *a, **k: _Resp({"other": 1}))
    with pytest.raises(ValueError):
        sources._fetch_phenom("orange.jobs/gb/en")


def test_board_ids():
    assert sources.normalize_board_token("phenom", "https://orange.jobs/gb/en/") == "orange.jobs/gb/en"
    assert sources.normalize_board_token("phenom", "orange.jobs/gb/en?Egypt") == "orange.jobs/gb/en?Egypt"
    assert sources.normalize_board_token("phenom", "not a board") == ""
    assert "opportunities.vodafone.com" in sources.load_board_tokens("successfactors")
    assert "orange.jobs/gb/en?Egypt" in sources.load_board_tokens("phenom")


def test_company_name_searches_share_the_daily_budget():
    day = dt.date(2026, 10, 23)
    js = sources.jsearch_today(day)
    assert len(js) == sources.JSEARCH_PER_DAY
    companies = {c for _, _, c in sources.EMPLOYER_SEARCHES}
    assert sum(1 for q, _, _ in js if q in companies) == sources.JSEARCH_EMPLOYER_PER_DAY
    jo = sources.jooble_today(day)
    assert len(jo) == sources.JOOBLE_PER_DAY and sum(1 for q, _ in jo if q in companies) == 1
    seen = {next(q for q, _, _ in sources.jsearch_today(day + dt.timedelta(d)) if q in companies) for d in range(20)}
    assert {"AMAN Holding", "Raya", "e& Egypt", "Telecom Egypt", "_VOIS"} <= seen    # every company within 20 days


# --------------------------------------------------------------------------- Oracle Recruiting Cloud
def _oracle_answer(reqs, total):
    return {"items": [{"TotalJobsCount": total, "requisitionList": reqs}], "count": 1}


def test_oracle_reads_jobs_pages_and_builds_links(monkeypatch):
    calls = []

    def get(url, params=None, headers=None):
        calls.append((url, params))
        offset = int(params["finder"].split("offset=")[1].split(",")[0])
        reqs = [{"Id": str(offset + i), "Title": "Data Engineer" if i % 2 == 0 else "Teller",
                 "PrimaryLocation": "Abu Dhabi, United Arab Emirates", "PrimaryLocationCountry": "AE",
                 "PostedDate": "2026-10-20"} for i in range(sources.ORACLE_PAGE)] if offset < 150 else []
        return _oracle_answer(reqs, 150)
    monkeypatch.setattr(sources, "_get_json", get)
    jobs = sources._fetch_oracle("ehjd.fa.em2.oraclecloud.com/fabCareers")
    assert len(jobs) == 100                                          # 200 read, tech roles kept
    assert jobs[0]["job_url"] == "https://ehjd.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/fabCareers/job/0"
    url, params = calls[0]
    assert url == "https://ehjd.fa.em2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    assert "siteNumber=fabCareers" in params["finder"] and "offset=0" in params["finder"]
    assert sources.oracle_id({**jobs[0], "board_token": "x/CX_1"}) == "x/CX_1:0"


def test_oracle_rejects_non_job_answers(monkeypatch):
    monkeypatch.setattr(sources, "_get_json", lambda *a, **k: {"error": "no"})
    with pytest.raises(ValueError):
        sources._fetch_oracle("example.oraclecloud.com/CX_1")


def test_oracle_board_ids():
    n = sources.normalize_board_token
    assert n("oracle", "https://ehjd.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/fabCareers") == \
        "ehjd.fa.em2.oraclecloud.com/fabCareers"
    assert n("oracle", "emhm.fa.em2.oraclecloud.com/hcmUI/CandidateExperience") == "emhm.fa.em2.oraclecloud.com/CX_1"
    assert len(sources.load_board_tokens("oracle")) >= 14
    assert "jobs.adnoc.ae/us/en" in sources.load_board_tokens("phenom")


# --------------------------------------------------------------------------- "too many requests" (429)
def _http_error(code, retry_after=None):
    import requests
    r = requests.Response()
    r.status_code = code
    if retry_after is not None:
        r.headers["Retry-After"] = str(retry_after)
    return requests.HTTPError(f"{code}", response=r)


def test_rate_limited_platform_warns_instead_of_failing_the_run(monkeypatch):
    calls = []

    def get(url, params=None):
        calls.append(url)
        raise _http_error(429, 0)
    monkeypatch.setattr(sources, "_get_json", get)
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    res = sources.extract_workable(tokens=[f"co{i}" for i in range(20)], pause_seconds=0)
    assert res.records == []
    assert len(calls) == sources.RATE_LIMIT_STOP                       # stops asking after 3 refusals
    assert any("too many requests" in w for w in res.warnings)


def test_rate_limit_streak_resets_after_a_good_board(monkeypatch):
    answers = iter([_http_error(429, 0), _http_error(429, 0), {"name": "A", "jobs": []},
                    _http_error(429, 0), _http_error(429, 0), {"name": "B", "jobs": []}])

    def get(url, params=None):
        a = next(answers)
        if isinstance(a, Exception):
            raise a
        return a
    monkeypatch.setattr(sources, "_get_json", get)
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    res = sources.extract_workable(tokens=[f"co{i}" for i in range(6)], pause_seconds=0)
    assert sum(v is not None for v in res.board_status.values()) == 2


def test_probing_stops_on_a_platform_that_says_too_many_requests(monkeypatch):
    from jobradar import boards
    asked = []

    def fake_probe(ats, token, country):
        asked.append((ats, token))
        return ("retry", "HTTP 429") if ats == "workable" else ("dead", "not found")
    monkeypatch.setattr(boards, "probe_board", fake_probe)
    monkeypatch.setattr(boards.time, "sleep", lambda s: None)
    todo = [("workable", "a", "Egypt", "A"), ("lever", "a", "Egypt", "A"), ("workable", "b", "Egypt", "B"),
            ("workable", "c", "Egypt", "C"), ("greenhouse", "c", "Egypt", "C")]

    class Cur:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, *a): pass
        def fetchall(self): return todo

    class Conn:
        def cursor(self): return Cur()
        def commit(self): pass
    counts = boards.validate_probes(Conn())
    assert [a for a, _ in asked].count("workable") == 1 and counts["rate_limited"] == 2
