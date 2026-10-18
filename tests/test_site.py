"""Public website: static files + publishing to GitHub Pages (GitHub API mocked)."""
import json
from pathlib import Path

from jobradar import site_export


class FakeResp:
    def __init__(self, status, body=None):
        self.status_code, self._body = status, body or {}
        self.content = json.dumps(self._body).encode()
        self.text = self.content.decode()

    def json(self):
        return self._body


def fake_github(monkeypatch, ref_exists: bool):
    calls = []

    def request(method, url, json=None, timeout=None, headers=None):
        path = url.split("api.github.com")[1]
        calls.append((method, path, json))
        assert headers["Authorization"] == "Bearer tok"
        if path.endswith("/git/blobs"):
            return FakeResp(201, {"sha": f"blob{len(calls)}"})
        if path.endswith("/git/trees"):
            return FakeResp(201, {"sha": "tree1"})
        if path.endswith("/git/commits"):
            return FakeResp(201, {"sha": "commit1"})
        if method == "GET":
            return FakeResp(200, {"object": {"sha": "old"}}) if ref_exists else FakeResp(404, {"message": "Not Found"})
        return FakeResp(200 if method == "PATCH" else 201, {"ref": "refs/heads/gh-pages"})

    monkeypatch.setattr(site_export.requests, "request", request)
    return calls


def test_publish_creates_branch_with_one_parentless_commit(monkeypatch):
    calls = fake_github(monkeypatch, ref_exists=False)
    sha = site_export.publish({"index.html": b"<html>", "data/jobs.json": b"[]"}, "me/repo", "gh-pages", "tok")
    assert sha == "commit1"
    methods = [(m, p.split("/git/")[1]) for m, p, _ in calls]
    assert methods == [("POST", "blobs"), ("POST", "blobs"), ("POST", "trees"), ("POST", "commits"),
                       ("GET", "ref/heads/gh-pages"), ("POST", "refs")]
    commit_body = calls[3][2]
    assert commit_body["parents"] == [] and commit_body["tree"] == "tree1"
    assert sorted(e["path"] for e in calls[2][2]["tree"]) == ["data/jobs.json", "index.html"]


def test_publish_force_updates_existing_branch(monkeypatch):
    calls = fake_github(monkeypatch, ref_exists=True)
    site_export.publish({"index.html": b"x"}, "me/repo", "gh-pages", "tok")
    method, path, body = calls[-1]
    assert method == "PATCH" and path.endswith("/git/refs/heads/gh-pages") and body == {"sha": "commit1", "force": True}


def test_publish_skipped_without_token(monkeypatch):
    monkeypatch.delenv("SITE_GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(site_export.requests, "request", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert site_export.publish_from_env(conn=None) is None


def test_site_files_are_complete():
    files = site_export.site_files()
    assert {"index.html", "style.css", "app.js", ".nojekyll"} <= set(files)
    assert any(p.startswith("fonts/") and p.endswith(".woff2") for p in files)
    assert not any(p.startswith("data/") for p in files)  # data comes from the export
    html = files["index.html"].decode()
    assert 'src="app.js"' in html and "fonts.googleapis" not in html  # self-hosted font, no third-party calls


def test_public_list_excludes_sources_that_forbid_reposting():
    assert set(site_export.PUBLIC_LIST_EXCLUDED) == {"remotive", "himalayas"}
    assert site_export.SOURCE_CREDITS["adzuna"] == "Jobs by Adzuna"


def test_skill_patterns_are_converted_for_the_browser():
    js = site_export.pg_regex_to_js(r"\mpython\M|\mpyspark\M")
    assert "\\m" not in js and "\\M" not in js
    assert js == r"(?<!\w)(?=\w)python(?<=\w)(?!\w)|(?<!\w)(?=\w)pyspark(?<=\w)(?!\w)"


def test_cv_reader_libraries_are_self_hosted():
    files = site_export.site_files()
    assert {"vendor/pdf.min.js", "vendor/pdf.worker.min.js", "vendor/mammoth.browser.min.js"} <= set(files)
    assert "vendor/pdf.min.js" in files["app.js"].decode()       # loaded from the site itself, only when a CV is added


def test_every_track_has_a_colour():
    """site/app.js colours jobs by track; a new track in role_tracks.csv needs a colour too."""
    import csv
    import re
    root = Path(__file__).resolve().parents[1]
    with open(root / "dbt" / "seeds" / "role_tracks.csv", newline="") as f:
        tracks = {r["track"] for r in csv.DictReader(f)} - {"Not tech"}
    app = (root / "site" / "app.js").read_text(encoding="utf-8")
    block = re.search(r"const TRACK_KEY = \{(.*?)\};", app, re.S).group(1)
    coloured = set(re.findall(r'"([^"]+)":\s*"', block))
    assert tracks <= coloured, tracks - coloured
    css = (root / "site" / "style.css").read_text(encoding="utf-8")
    for key in re.findall(r':\s*"(\w+)"', block):
        assert f"--t-{key}:" in css, key
    assert "Radarak" in (root / "site" / "index.html").read_text(encoding="utf-8")


def test_analytics_tag_only_with_a_valid_code(tmp_path):
    (tmp_path / "index.html").write_text("<html><body><p>x</p></body></html>", encoding="utf-8")
    plain = site_export.site_files(tmp_path, analytics_code="")["index.html"].decode()
    assert "goatcounter" not in plain
    tagged = site_export.site_files(tmp_path, analytics_code="radarak")["index.html"].decode()
    assert 'data-goatcounter="https://radarak.goatcounter.com/count"' in tagged
    assert tagged.index("goatcounter") < tagged.index("</body>")
    # anything that isn't a plain site code is ignored (no HTML injection through the env var)
    bad = site_export.site_files(tmp_path, analytics_code='x"><script>alert(1)</script>')["index.html"].decode()
    assert "goatcounter" not in bad and "alert" not in bad


class _FakeConn:
    """Answers the trend queries by table name."""
    def __init__(self, answers):
        self.answers = answers

    def cursor(self):
        conn = self

        class Cur:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def execute(self, sql, params=None):
                self.rows = next(v for k, v in conn.answers.items() if k in sql)

            def fetchall(self):
                return self.rows
        return Cur()


def test_trends_export_aligns_weeks_and_drops_thin_places():
    import datetime as dt
    now = dt.datetime(2026, 10, 17, 6, 0, tzinfo=dt.timezone.utc)   # a Saturday
    this_monday, last_monday = dt.date(2026, 10, 12), dt.date(2026, 10, 5)
    conn = _FakeConn({
        "mart_weekly_new_jobs": [(last_monday, "All", "Data & Analytics", 30), (this_monday, "All", "Data & Analytics", 9),
                                 (last_monday, "Egypt", "Data & Analytics", 25), (last_monday, "Oman", "QA & Testing", 2),
                                 (dt.date(2020, 1, 6), "All", "Data & Analytics", 99)],   # outside the 12 weeks
        "mart_skill_trends": [("All", "Spark", 28, 40.0, 30.0, -10.0, 30), ("All", "LLMs / GenAI", 28, 10.0, 25.0, 15.0, 25),
                              ("All", "SQL", 28, 60.0, 61.0, 1.0, 61)],
        "mart_time_to_close": [("Data Engineer", "Data & Analytics", 21, 12, 30, 40)],
        "max(first_seen_date) - min(first_seen_date)": [(60,)],
    })
    t = site_export.export_trends(conn, now)
    assert len(t["weeks"]) == 12 and t["weeks"][-1] == "2026-10-12" and t["weeks"][-2] == "2026-10-05"
    assert t["weekly"]["All"]["Data & Analytics"][-2:] == [30, 9]
    assert "Egypt" in t["weekly"] and "Oman" not in t["weekly"]          # 2 jobs: too few for a trend
    moves = t["skills"]["All"]
    assert [r[0] for r in moves["rising"]] == ["LLMs / GenAI", "SQL"] and [r[0] for r in moves["falling"]] == ["Spark"]
    assert moves["top"][0][0] == "SQL" and t["window_days"] == 28 and t["history_days"] == 60
    assert t["days_open"] == [["Data Engineer", "Data & Analytics", 21, 12, 30, 40]]


def test_report_page_is_published():
    files = site_export.site_files(analytics_code="radarak")
    assert "report.html" in files and "report.js" in files
    assert b"goatcounter" in files["report.html"]      # analytics on every page


def test_site_is_an_installable_app():
    import json
    files = site_export.site_files()
    assert {"manifest.webmanifest", "sw.js"} <= set(files)
    manifest = json.loads(files["manifest.webmanifest"])
    assert manifest["display"] == "standalone" and manifest["start_url"].startswith("./")
    for icon in manifest["icons"]:
        assert icon["src"] in files, icon["src"]                       # every icon is published
    assert any(i["purpose"] == "maskable" for i in manifest["icons"])
    html = files["index.html"].decode()
    assert 'rel="manifest"' in html and 'rel="apple-touch-icon"' in html
    assert html.split('rel="apple-touch-icon" href="')[1].split('"')[0] in files
    sw = files["sw.js"].decode()
    for path in sw.split("const SHELL = [")[1].split("]")[0].replace('"', "").replace("\n", "").split(","):
        path = path.strip()
        assert path in ("./", "") or path in files, path                # the offline copy only lists real files
    assert 'register("sw.js")' in files["app.js"].decode()


def test_job_export_keeps_first_seen_day_for_new_since_last_visit():
    import datetime as dt
    row = ("abcdef1234567890", "Data Engineer", "Acme", "Data & Analytics", "Data Engineer", "Mid", "Remote",
           "Software", "Cairo, Egypt", ["Egypt"], [], False, None, None, dt.date(2026, 10, 1), False,
           "https://jobs.example.com/1", ["SQL"], False, False, False, "greenhouse", dt.date(2026, 10, 18))
    same = row[:-1] + (dt.date(2026, 10, 1),)
    conn = _FakeConn({"with jobs as": [row, same], "seeds.geo_patterns": [], "seeds.role_tracks": [],
                      "count(*) from marts.fct_job_postings": [(2,)], "seeds.skills": [],
                      "mart_weekly_new_jobs": [], "mart_skill_trends": [], "mart_time_to_close": [],
                      "max(first_seen_date) - min(first_seen_date)": [(0,)]})
    import json
    jobs = json.loads(site_export.export_site_data(conn)["data/jobs.json"])
    assert jobs[0]["p"] == "2026-10-01" and jobs[0]["fs"] == "2026-10-18"   # posted earlier, first seen yesterday
    assert "fs" not in jobs[1]                                              # same day: not repeated
