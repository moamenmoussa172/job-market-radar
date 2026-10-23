"""The site's job list is split in two files: remote + Middle East/Africa first, the rest on demand."""
import json

from jobradar import site_export

REGION = {"Egypt": "MENA", "Kenya": "Africa", "Germany": "Europe", "United States": "North America"}


def job(i, w="Onsite", co=(), rg=()):
    return {"id": str(i), "w": w, "co": list(co), "rg": list(rg)}


def test_core_is_remote_plus_middle_east_and_africa():
    jobs = [job(1, co=["Egypt"]), job(2, co=["Germany"]), job(3, w="Remote", rg=["North America"]),
            job(4, co=["Kenya"]), job(5, co=["Germany", "Egypt"]), job(6, rg=["MENA"]), job(7, co=["United States"])]
    core, more = site_export.split_jobs(jobs, REGION)
    assert [j["id"] for j in core] == ["1", "3", "4", "5", "6"]
    assert [j["id"] for j in more] == ["2", "7"]


def test_every_job_lands_in_exactly_one_file():
    jobs = [job(i, co=[c]) for i, c in enumerate(["Egypt", "Germany", "Kenya", "United States"] * 5)]
    core, more = site_export.split_jobs(jobs, REGION)
    assert sorted(j["id"] for j in core + more) == sorted(j["id"] for j in jobs)


def test_all_jobs_joins_both_files_and_handles_old_exports():
    data = {"data/jobs.json": json.dumps([job(1)]).encode(), "data/jobs-more.json": json.dumps([job(2)]).encode()}
    assert [j["id"] for j in site_export.all_jobs(data)] == ["1", "2"]
    assert [j["id"] for j in site_export.all_jobs({"data/jobs.json": b"[]"})] == []


def test_listing_limit_covers_everything_by_default():
    assert site_export.MAX_PUBLIC_JOBS >= 30000


def test_export_writes_both_files_and_counts_the_rest():
    import datetime as dt
    from test_site import _FakeConn

    def row(jid, mode, loc, countries):
        return (jid * 4, "Data Engineer", "Acme " + jid, "Data & Analytics", "Data Engineer", "Mid", mode,
                "Software", loc, countries, [], False, None, None, dt.date(2026, 10, 1), False,
                "https://jobs.example.com/" + jid, ["SQL"], False, False, False, "greenhouse", dt.date(2026, 10, 1))
    rows = [row("a", "Onsite", "Cairo", ["Egypt"]), row("b", "Onsite", "Berlin", ["Germany"]),
            row("c", "Remote", "Anywhere", [])]
    conn = _FakeConn({"with jobs as": rows, "seeds.geo_patterns": [("Egypt", "MENA"), ("Germany", "Europe")],
                      "seeds.role_tracks": [], "count(*) from marts.fct_job_postings": [(3,)], "seeds.skills": [],
                      "mart_weekly_new_jobs": [], "mart_skill_trends": [], "mart_time_to_close": [],
                      "max(first_seen_date) - min(first_seen_date)": [(0,)]})
    data = site_export.export_site_data(conn)
    core = json.loads(data["data/jobs.json"])
    more = json.loads(data["data/jobs-more.json"])
    meta = json.loads(data["data/meta.json"])
    assert [j["l"] for j in core] == ["Cairo", "Anywhere"] and [j["l"] for j in more] == ["Berlin"]
    assert meta["listed_jobs"] == 3 and meta["more_jobs"] == 1 and meta["core_regions"] == ["MENA", "Africa"]
