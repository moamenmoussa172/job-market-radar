"""Telegram daily posts (Telegram API mocked)."""
import datetime as dt

from jobradar import telegram


def job(i, title="Data Engineer", company="Acme", track="Data & Analytics", work_mode="Hybrid",
        loc="Cairo, Egypt", sal=(None, None), visa=False, arabic=False, source="greenhouse"):
    return (f"id{i}", title, company, track, work_mode, loc, f"https://jobs.example.com/{i}?a=1&b=2",
            sal[0], sal[1], visa, arabic, "Mid", source)


def test_channels_are_parsed_from_env_text():
    chans = telegram.parse_channels("@eg=Egypt; @gulf=Saudi Arabia|United Arab Emirates ;@rem=Remote;broken")
    assert [(c.chat, c.places) for c in chans] == [
        ("@eg", ["Egypt"]), ("@gulf", ["Saudi Arabia", "United Arab Emirates"]), ("@rem", ["Remote"])]
    assert chans[2].remote and not chans[0].remote
    assert chans[1].flags == "🇸🇦🇦🇪" and chans[1].label_ar == "السعودية، الإمارات"
    assert telegram.parse_channels(None) == []


def test_digest_groups_by_track_escapes_html_and_links_back():
    ch = telegram.Channel("@eg", ["Egypt"])
    jobs = [job(1, title="Data <Engineer> & BI", sal=(30, 45), visa=True),
            job(2, title="iOS Developer", track="Mobile Development", work_mode="Onsite", arabic=True),
            job(3, title="Data Analyst", source="adzuna")]
    [msg] = telegram.format_messages(ch, jobs, "https://u.github.io/job-market-radar/", dt.date(2026, 10, 17))
    assert msg.startswith("🇪🇬 <b>3 new tech jobs · Egypt</b> · 17 Oct")
    assert "٣ وظيفة تك جديدة · مصر" in msg
    assert "Data &lt;Engineer&gt; &amp; BI" in msg and 'href="https://jobs.example.com/1?a=1&amp;b=2"' in msg
    assert msg.index("Data &amp; Analytics</b> (2)") < msg.index("Mobile Development</b> (1)")   # biggest track first
    assert "💰 $30k–45k" in msg and "🛂 visa" in msg and "🗣 Arabic" in msg
    assert "<i>(Jobs by Adzuna)</i>" in msg                                                    # source credit kept
    assert 'href="https://u.github.io/job-market-radar/#country=Egypt"' in msg
    assert telegram.format_messages(ch, [], "x") == []


def test_long_digests_are_split_under_the_telegram_limit():
    ch = telegram.Channel("@rem", ["Remote"])
    jobs = [job(i, title=f"Senior Platform Engineer {i} " + "x" * 120, work_mode="Remote",
                track=["Software Engineering", "DevOps & Cloud"][i % 2]) for i in range(80)]
    msgs = telegram.format_messages(ch, jobs, "https://s/")
    assert len(msgs) > 1 and all(len(m) <= 4096 for m in msgs)
    assert sum(m.count("• <a") for m in msgs) == 80                 # nothing lost
    assert "Radarak" in msgs[-1] and "🌍" in msgs[0]


def test_send_waits_on_flood_control(monkeypatch):
    calls = []

    class R:
        def __init__(self, code, body):
            self.status_code, self._b, self.text = code, body, str(body)

        def json(self):
            return self._b
    answers = [R(429, {"parameters": {"retry_after": 0}}), R(200, {"ok": True})]
    monkeypatch.setattr(telegram.requests, "post", lambda url, **kw: calls.append((url, kw["json"])) or answers.pop(0))
    monkeypatch.setattr(telegram.time, "sleep", lambda s: None)
    telegram.send_message("TOKEN", "@eg", "hi")
    assert len(calls) == 2 and calls[0][0] == "https://api.telegram.org/botTOKEN/sendMessage"
    assert calls[1][1] == {"chat_id": "@eg", "text": "hi", "parse_mode": "HTML", "disable_web_page_preview": True}


def test_post_from_env_records_posts_and_one_bad_channel_does_not_stop_others(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "T")
    monkeypatch.setenv("TELEGRAM_CHANNELS", "@bad=Egypt;@ok=Remote")
    monkeypatch.setenv("SITE_REPO", "MoamenMoussa172/job-market-radar")
    recorded, sent = [], []
    monkeypatch.setattr(telegram, "ensure_schema", lambda conn: None)
    monkeypatch.setattr(telegram, "select_jobs", lambda conn, ch, limit: [job(1, work_mode="Remote")])
    monkeypatch.setattr(telegram, "record_posted", lambda conn, chat, ids: recorded.append((chat, ids)))
    monkeypatch.setattr(telegram.time, "sleep", lambda s: None)

    def send(token, chat, text):
        if chat == "@bad":
            raise RuntimeError("bot is not an admin")
        sent.append(text)
    monkeypatch.setattr(telegram, "send_message", send)

    class Conn:
        def rollback(self):
            pass
    assert telegram.post_from_env(Conn()) == {"@bad": -1, "@ok": 1}
    assert recorded == [("@ok", ["id1"])]                          # failed channel: not marked as posted
    assert "https://moamenmoussa172.github.io/job-market-radar/" in sent[0]


def test_nothing_happens_without_configuration(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert telegram.post_from_env(object()) == {}


def test_links_use_the_custom_domain_when_set(monkeypatch):
    monkeypatch.delenv("SITE_URL", raising=False)
    monkeypatch.setenv("SITE_DOMAIN", "radarak.com")
    assert telegram.site_url() == "https://radarak.com/"
