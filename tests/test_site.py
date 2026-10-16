"""Public website: static files + publishing to GitHub Pages (GitHub API mocked)."""
import json

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
