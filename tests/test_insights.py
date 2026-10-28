"""Insight of the day: what it says, when it stays quiet, and Telegram posting once a day."""
import datetime as dt

from jobradar import insights, telegram

META = {"skills": ["SQL", "Python", "System design", "Flutter", "Kotlin", "React Native", "Swift"],
        "countries": [{"name": "Egypt", "region": "MENA"}, {"name": "Saudi Arabia", "region": "MENA"},
                      {"name": "United States", "region": "North America"}, {"name": "Germany", "region": "Europe"},
                      {"name": "Spain", "region": "Europe"}, {"name": "United Kingdom", "region": "Europe"},
                      {"name": "France", "region": "Europe"}]}
TODAY = dt.date(2026, 10, 28)
_n = [0]


def job(w="Onsite", co=("Egypt",), k=(), s="Mid", c=None, tr="Software Engineering", rg=(), pay=None, p="2026-10-20", **kw):
    _n[0] += 1
    j = {"id": f"j{_n[0]}", "t": f"Job {_n[0]}", "c": c or f"Co{_n[0] % 40}", "tr": tr, "r": "Software Engineer", "s": s,
         "w": w, "l": "", "co": list(co), "rg": list(rg), "p": p, "u": "https://x", "k": list(k), **kw}
    if pay:
        j["$"] = pay
    return j


def market():
    jobs = []
    # remote: 40 open to Egypt (MENA), 200 US only, 100 Europe only, 60 elsewhere
    jobs += [job(w="Remote", co=(), rg=("MENA",)) for _ in range(40)]
    jobs += [job(w="Remote", co=("United States",)) for _ in range(200)]
    jobs += [job(w="Remote", co=("Germany",)) for _ in range(100)]
    jobs += [job(w="Remote", co=(), rg=("APAC",), pay=[100, 120]) for _ in range(60)]
    # Egypt office jobs: two big employers + a recruiter that must not be listed
    jobs += [job(c="Orange") for _ in range(30)] + [job(c="Yassir") for _ in range(20)] + [job(c="Eram Talent") for _ in range(40)]
    jobs += [job() for _ in range(80)]
    jobs += [job(co=("Saudi Arabia",)) for _ in range(200)] + [job(co=("Saudi Arabia",), pay=[50, 60])]
    # mobile: Flutter popular here, rare in the US
    jobs += [job(co=("Egypt",), k=(3,)) for _ in range(25)] + [job(co=("Egypt",), k=(4,)) for _ in range(15)]
    jobs += [job(co=("United States",), k=(4,)) for _ in range(30)]
    # levels: system design grows with seniority
    jobs += [job(s="Junior", k=(0, 2) if i < 8 else (0,), co=("Germany",)) for i in range(200)]
    jobs += [job(s="Lead / Principal", k=(2,) if i < 60 else (1,), co=("Germany",)) for i in range(200)]
    # Europe pays in the open
    jobs += [job(co=("Spain",), pay=[60, 80] if i < 60 else None) for i in range(120)]
    jobs += [job(co=("United Kingdom",), pay=[70, 90] if i < 40 else None) for i in range(120)]
    # new this morning
    jobs += [job(w="Remote", co=(), rg=("Worldwide",), p=TODAY.isoformat()) for _ in range(60)]
    return jobs


def by_id(res):
    return {i["id"]: i for i in res["items"]}


def test_insights_tell_true_things_in_both_languages():
    res = insights.all_insights(market(), META, TODAY)
    got = by_id(res)
    assert set(got) == {"remote", "hiring", "stack", "ladder", "pay", "new"}
    r = got["remote"]
    assert r["title"]["en"] == "Only 1 in 5 remote tech jobs is open to people in Egypt" and r["big"] == "1 / 5"
    assert [b["t"] for b in r["bars"]] == ["22%", "43%", "22%", "13%"]          # 100 open (40 MENA + 60 worldwide) of 460
    assert "مصر" in r["title"]["ar"]
    h = got["hiring"]
    assert [b["l"]["en"] for b in h["bars"]][:2] == ["Orange", "Yassir"]
    assert "Eram Talent" not in [b["l"]["en"] for b in h["bars"]]                # agencies left out
    assert got["stack"]["big"] == "62%" and got["stack"]["bars"][2]["t"] == "0%"
    assert got["ladder"]["big"] == "×8"                                            # 4% junior -> 30% lead
    assert got["pay"]["big"].startswith("1 / ")
    assert got["new"]["big"] == "60"
    for ins in res["items"]:
        assert ins["title"]["en"] and ins["title"]["ar"] and ins["note"]["ar"]
        assert all(0 <= b["v"] <= 1 for b in ins["bars"])


def test_quiet_when_the_numbers_are_too_small():
    small = [job(w="Remote", co=(), rg=("MENA",)) for _ in range(20)] + [job() for _ in range(10)]
    assert insights.all_insights(small, META, TODAY)["items"] == []


def test_the_daily_pick_rotates():
    jobs = market()
    firsts = {insights.all_insights(jobs, META, TODAY + dt.timedelta(days=d))["items"][0]["id"] for d in range(6)}
    assert len(firsts) >= 5


def test_telegram_text_is_safe_html():
    ins = by_id(insights.all_insights(market(), META, TODAY))["hiring"]
    ins["title"]["en"] = "A <b> & C"
    text = insights.telegram_text(ins, "https://radarak.online/")
    assert "A &lt;b&gt; &amp; C" in text and 'href="https://radarak.online/#insight"' in text
    assert "• Orange: <b>30</b>" in text


def test_insight_goes_to_each_channel_once_a_day(monkeypatch):
    posted, sent = set(), []

    class Cur:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, sql, args):
            self.hit = args in posted

        def fetchone(self):
            return (1,) if self.hit else None

    class Conn:
        def cursor(self):
            return Cur()
    monkeypatch.setattr(telegram, "send_message", lambda token, chat, text: sent.append((chat, text)))
    monkeypatch.setattr(telegram, "record_posted", lambda conn, chat, ids: posted.update((chat, i) for i in ids))
    monkeypatch.setattr(telegram.time, "sleep", lambda s: None)
    ins = insights.all_insights(market(), META, TODAY)["items"][0]
    assert telegram.post_insight(Conn(), "T", "@eg", ins, "https://radarak.online/", TODAY) is True
    assert telegram.post_insight(Conn(), "T", "@eg", ins, "https://radarak.online/", TODAY) is False
    assert telegram.post_insight(Conn(), "T", "@eg", ins, "https://radarak.online/", TODAY + dt.timedelta(days=1)) is True
    assert len(sent) == 2 and ("@eg", "insight:2026-10-28") in posted
