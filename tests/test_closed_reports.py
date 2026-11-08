"""Visitors' "this job is closed" reports: read from GoatCounter, kept, and left out of the site."""
import datetime as dt

from jobradar import closed_reports


class _Resp:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


class _Session:
    def __init__(self, pages):
        self.pages, self.calls = list(pages), []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, dict(params), headers))
        return _Resp(self.pages.pop(0))


def test_fetch_reports_reads_paths_and_pages():
    s = _Session([
        {"hits": [{"path": "closed/0123456789ab", "count": 2, "path_id": 1},
                  {"path": "report-closed/aaaaaaaaaaaa/Some-Co", "count": 1, "path_id": 2},
                  {"path": "closed/not-a-job", "count": 9, "path_id": 3}], "more": True},
        {"hits": [{"path": "/closed/0123456789ab", "count": 1, "path_id": 4}], "more": False},
    ])
    got = closed_reports.fetch_reports("radarak", "tok", dt.date(2026, 11, 8), session=s)
    assert got == {"0123456789ab": 3, "aaaaaaaaaaaa": 1}
    url, params, headers = s.calls[0]
    assert url == "https://radarak.goatcounter.com/api/v0/stats/hits"
    assert params["filter"] == "closed/" and params["start"] == "2026-09-09"
    assert headers["Authorization"] == "Bearer tok"
    assert s.calls[1][1]["exclude_paths"] == "1,2,3"


def test_sync_skips_without_token(monkeypatch):
    monkeypatch.delenv("GOATCOUNTER_API_TOKEN", raising=False)
    monkeypatch.setenv("GOATCOUNTER_CODE", "radarak")
    assert "skipped" in closed_reports.sync(object())


def test_sync_never_raises(monkeypatch):
    monkeypatch.setenv("GOATCOUNTER_CODE", "radarak")
    monkeypatch.setenv("GOATCOUNTER_API_TOKEN", "tok")

    class Broken:
        def cursor(self):
            raise RuntimeError("db down")

        def rollback(self):
            pass

    assert "error" in closed_reports.sync(Broken())


def test_closed_ids_without_table_is_empty():
    assert closed_reports.closed_ids(None) == set()
