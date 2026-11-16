"""Referral offers from the owner's published Google Sheet tab."""
import datetime as dt

from jobradar import referrals

TRACKS = ["Data & Analytics", "Software Engineering", "AI & Machine Learning"]
HEAD = "Timestamp,Name,Company,Title,LinkedIn,Areas,Levels,Location,Job link,Note\n"
TODAY = dt.date(2026, 11, 16)


def row(**kw):
    base = {"when": "11/15/2026 10:00:00", "name": "Sara Ahmed", "company": "Valeo Egypt LLC", "title": "Senior Data Engineer",
            "li": "https://www.linkedin.com/in/sara-ahmed/", "areas": "Data & Analytics, Cooking", "levels": "Intern & junior, Mid",
            "place": "Cairo", "job": "", "note": "Happy to help"}
    base.update(kw)
    return ",".join(f'"{v}"' for v in base.values()) + "\n"


def test_parse_cleans_and_maps_fields():
    offers = referrals.parse(HEAD + row(), TRACKS, TODAY)
    assert len(offers) == 1
    o = offers[0]
    assert o["ck"] == "valeo" and o["c"] == "Valeo Egypt LLC"
    assert o["tr"] == ["Data & Analytics"]                       # unknown areas dropped
    assert o["lv"] == ["Intern / Student", "Junior", "Mid"]
    assert o["li"] == "https://www.linkedin.com/in/sara-ahmed/" and o["d"] == "2026-11-15"


def test_parse_drops_bad_or_risky_offers():
    rows = (row(li="https://evil.example/in/x") + row(name="Ali", li="https://linkedin.com/in/ali", note="Referral fee 500 EGP")
            + row(name="Old", li="https://linkedin.com/in/old", when="01/01/2026 10:00:00")
            + row(name="Mona", li="https://linkedin.com/in/mona", note="DM me on WhatsApp")
            + row(name="Omar", li="https://linkedin.com/in/omar", job="javascript:alert(1)", note="see https://x.y/z ok"))
    offers = referrals.parse(HEAD + rows, TRACKS, TODAY)
    assert [o["n"] for o in offers] == ["Omar"]
    assert offers[0]["job"] == "" and "http" not in offers[0]["note"]


def test_same_person_same_company_once():
    offers = referrals.parse(HEAD + row() + row(when="11/10/2026 10:00:00", company="valeo"), TRACKS, TODAY)
    assert len(offers) == 1


def test_offers_from_env_never_raises(monkeypatch):
    monkeypatch.delenv("REFERRALS_CSV_URL", raising=False)
    assert referrals.offers_from_env(TRACKS) == []
    monkeypatch.setenv("REFERRALS_CSV_URL", "https://docs.google.com/x.csv")

    class Down:
        def get(self, *a, **k):
            raise OSError("offline")
    assert referrals.offers_from_env(TRACKS, session=Down()) == []
