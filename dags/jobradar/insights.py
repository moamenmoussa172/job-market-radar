"""Insight of the day: one short, true fact from today's jobs, in English and Arabic.

Each insight type below is computed from the published job list (the same data people see on the site).
A type only counts when today's numbers are big enough to say something honest; the site rotates
through the valid ones, one per day, and people can flip to the others. The same insight goes to
Telegram once a day per channel, and the site can turn it into an image to share (drawn in the browser).

Output (data/insights.json): {"date": "2026-10-28", "items": [insight, ...]}, today's first. An insight:
    {"id": "remote", "title": {"en", "ar"}, "big": "1 in 11", "big_label": {"en", "ar"},
     "bars": [{"l": {"en", "ar"}, "v": 0..1, "t": "9%"}], "note": {"en", "ar"}, "link": "#country=Egypt&remote=1"}
"""
from __future__ import annotations

import datetime as dt
from collections import Counter

GULF = ("Saudi Arabia", "United Arab Emirates", "Qatar", "Kuwait", "Bahrain", "Oman")
HOME = "Egypt"
# staffing agencies post many jobs for other companies; a "who's hiring" list should show employers
RECRUITERS = {"eram talent", "master-works", "placements24", "jobgether srl", "jobgether", "ssc hr solutions",
              "jobs-in-qatar", "nair systems llc", "hays", "michael page", "robert walters", "cooper fitch"}
JUNIOR = ("Intern / Student", "Junior")
LEAD = ("Lead / Principal", "Head / Director")


def _t(en: str, ar: str) -> dict:
    return {"en": en, "ar": ar}


def _unique(jobs: list[dict]) -> list[dict]:
    seen, out = set(), []
    for j in jobs:
        key = ((j.get("t") or "").lower(), (j.get("c") or "").lower())
        if key not in seen:
            seen.add(key)
            out.append(j)
    return out


def _pct(a: int, b: int) -> int:
    return round(100 * a / b) if b else 0


def _bar(en: str, ar: str, value: float, top: float, text: str) -> dict:
    return {"l": _t(en, ar), "v": round(value / top, 3) if top else 0, "t": text}


def _onsite_in(j: dict, places) -> bool:
    return j.get("w") != "Remote" and any(c in places for c in (j.get("co") or []))


def _open_to_home(j: dict) -> bool:
    return bool(j.get("ww")) or HOME in (j.get("co") or []) or bool({"MENA", "Worldwide"} & set(j.get("rg") or []))


# --------------------------------------------------------------------------- insight types
def remote_reality(jobs, meta, today):
    remote = [j for j in jobs if j.get("w") == "Remote"]
    if len(remote) < 300:
        return None
    region = {c["name"]: c.get("region") for c in meta.get("countries", [])}

    def scope(j):
        co, rg = set(j.get("co") or []), set(j.get("rg") or [])
        if _open_to_home(j):
            return "open"
        if co and co <= {"United States", "Canada"}:
            return "na"
        if (not co and rg == {"Europe"}) or (co and all(region.get(c) == "Europe" for c in co)):
            return "eu"
        return "other"
    c = Counter(scope(j) for j in remote)
    n, opened = len(remote), c["open"]
    if not opened:
        return None
    ratio = max(2, round(n / opened))
    top = max(c.values())
    return {
        "id": "remote", "big": f"1 / {ratio}",
        "title": _t(f"Only 1 in {ratio} remote tech jobs is open to people in Egypt",
                    f"وظيفة ريموت واحدة من كل {ratio} مفتوحة للناس اللي في مصر"),
        "big_label": _t(f"of {n:,} remote jobs today", f"من {n:,} وظيفة ريموت النهارده"),
        "bars": [_bar("Open to Egypt", "مفتوحة لمصر", opened, top, f"{_pct(opened, n)}%"),
                 _bar("US / Canada only", "أمريكا وكندا بس", c["na"], top, f"{_pct(c['na'], n)}%"),
                 _bar("Europe only", "أوروبا بس", c["eu"], top, f"{_pct(c['eu'], n)}%"),
                 _bar("Other countries", "دول تانية", c["other"], top, f"{_pct(c['other'], n)}%")],
        "note": _t("Radarak hides the jobs you can't apply to from your country.",
                   "رادارك بيخبّي الوظايف اللي متقدرش تقدّم عليها من بلدك."),
        "link": "#country=Egypt&remote=1",
    }


def who_is_hiring(jobs, meta, today):
    home = [j for j in jobs if _onsite_in(j, (HOME,))]
    c = Counter(j.get("c") for j in home if j.get("c") and j["c"].lower() not in RECRUITERS)
    top = c.most_common(5)
    if len(home) < 100 or not top or top[0][1] < 5:
        return None
    return {
        "id": "hiring", "big": f"{len(home):,}",
        "title": _t("Who's hiring tech in Egypt right now", "مين بيعيّن تك في مصر دلوقتي"),
        "big_label": _t(f"open tech jobs at {len({j.get('c') for j in home}):,} companies",
                        f"وظيفة تك مفتوحة في {len({j.get('c') for j in home}):,} شركة"),
        "bars": [_bar(name, name, n, top[0][1], str(n)) for name, n in top],
        "note": _t("Office and hybrid jobs in Egypt. Recruitment agencies left out.",
                   "وظايف من المكتب وهايبرد في مصر، من غير شركات التوظيف."),
        "link": "#country=Egypt",
    }


def same_job_different_stack(jobs, meta, today):
    skills = meta.get("skills", [])
    family = [s for s in ("Flutter", "React Native", "Kotlin", "Swift") if s in skills]
    if "Flutter" not in family:
        return None
    idx, flutter = {skills.index(s) for s in family}, skills.index("Flutter")
    markets = [("Egypt & Gulf", "مصر والخليج", lambda j: _onsite_in(j, (HOME,) + GULF)),
               ("Europe", "أوروبا", lambda j: j.get("w") != "Remote" and any(
                   r == "Europe" for r in ({c["name"]: c.get("region") for c in meta.get("countries", [])}.get(x)
                                           for x in (j.get("co") or [])))),
               ("USA", "أمريكا", lambda j: _onsite_in(j, ("United States",))),
               ("Remote", "ريموت", lambda j: j.get("w") == "Remote")]
    shares = []
    for en, ar, f in markets:
        mobile = [j for j in jobs if f(j) and idx & set(j.get("k") or [])]
        shares.append((en, ar, _pct(sum(flutter in j["k"] for j in mobile), len(mobile)), len(mobile)))
    home, us = shares[0], shares[2]
    if home[3] < 30 or us[3] < 20 or home[2] <= us[2]:
        return None
    top = max(s[2] for s in shares) or 1
    return {
        "id": "stack", "big": f"{home[2]}%",
        "title": _t(f"Flutter is in {home[2]}% of mobile jobs in Egypt & the Gulf. In the US: {us[2]}%",
                    f"Flutter في {home[2]}% من وظايف الموبايل في مصر والخليج. في أمريكا: {us[2]}%"),
        "big_label": _t("of mobile jobs here ask for Flutter", "من وظايف الموبايل هنا طالبة Flutter"),
        "bars": [_bar(en, ar, p, top, f"{p}%") for en, ar, p, _ in shares],
        "note": _t("Same job, different stack: learn what your market hires for.",
                   "نفس الشغل، أدوات مختلفة: اتعلم اللي السوق بتاعك بيطلبه."),
        "link": "#country=Egypt&role=track%3AMobile%20Development",
    }


def career_ladder(jobs, meta, today):
    skills = meta.get("skills", [])
    if "System design" not in skills:
        return None
    sd = skills.index("System design")
    levels = [("Junior", "جونيور", JUNIOR), ("Senior", "سينيور", ("Senior",)), ("Lead", "ليد", LEAD)]
    shares = []
    for en, ar, ls in levels:
        js = [j for j in jobs if j.get("s") in ls and j.get("k")]
        shares.append((en, ar, _pct(sum(sd in j["k"] for j in js), len(js)), len(js)))
    jr, lead = shares[0], shares[2]
    if jr[3] < 150 or lead[3] < 150 or not jr[2] or lead[2] < 2 * jr[2]:
        return None
    times = round(lead[2] / jr[2])
    return {
        "id": "ladder", "big": f"×{times}",
        "title": _t(f"System design: {jr[2]}% of junior jobs ask for it, {lead[2]}% of lead jobs",
                    f"الـ System design: مطلوب في {jr[2]}% من وظايف الجونيور، و{lead[2]}% من وظايف الليد"),
        "big_label": _t("more often in lead jobs than in junior jobs", "أكتر في وظايف الليد من الجونيور"),
        "bars": [_bar(en, ar, p, lead[2], f"{p}%") for en, ar, p, _ in shares],
        "note": _t("The next level isn't another language. It's a bigger picture.",
                   "المستوى الجاي مش لغة جديدة. هو صورة أكبر."),
        "link": "",
    }


def salary_transparency(jobs, meta, today):
    home = [j for j in jobs if _onsite_in(j, (HOME,) + GULF)]
    if len(home) < 300:
        return None
    paid = sum(1 for j in home if j.get("$"))
    places = [("Egypt & Gulf", "مصر والخليج", (HOME,) + GULF), ("Spain", "إسبانيا", ("Spain",)),
              ("UK", "بريطانيا", ("United Kingdom",)), ("France", "فرنسا", ("France",))]
    rows = []
    for en, ar, ps in places:
        js = [j for j in jobs if _onsite_in(j, ps)]
        if len(js) >= 100:
            rows.append((en, ar, 100 * sum(1 for j in js if j.get("$")) / len(js)))
    remote = [j for j in jobs if j.get("w") == "Remote"]
    if remote:
        rows.append(("Remote", "ريموت", 100 * sum(1 for j in remote if j.get("$")) / len(remote)))
    if len(rows) < 3 or max(r[2] for r in rows[1:]) < 10:
        return None
    top = max(r[2] for r in rows)
    fmt = lambda v: f"{v:.1f}%" if 0 < v < 1 else f"{round(v)}%"  # noqa: E731
    return {
        "id": "pay", "big": f"{paid} / {len(home):,}",
        "title": _t(f"{paid} of {len(home):,} tech jobs in Egypt & the Gulf show the salary",
                    f"{paid} بس من {len(home):,} وظيفة تك في مصر والخليج مكتوب فيها المرتب"),
        "big_label": _t("jobs here show the salary", "وظيفة هنا مكتوب فيها المرتب"),
        "bars": [_bar(en, ar, v, top, fmt(v)) for en, ar, v in rows],
        "note": _t("Ask for the range in the first call. See what roles pay where it's public on radarak.online/salaries",
                   "اسأل على الرينج من أول مكالمة. وشوف المرتبات المنشورة على radarak.online/salaries"),
        "link": "",
    }


def new_this_morning(jobs, meta, today):
    day = today.isoformat()
    new = [j for j in jobs if (j.get("fs") or j.get("p")) == day]
    if len(new) < 50:
        return None
    eg = sum(1 for j in new if _onsite_in(j, (HOME,)))
    gulf = sum(1 for j in new if _onsite_in(j, GULF))
    rem = sum(1 for j in new if j.get("w") == "Remote")
    top = max(eg, gulf, rem, 1)
    return {
        "id": "new", "big": f"{len(new):,}",
        "title": _t(f"{len(new):,} new tech jobs this morning", f"{len(new):,} وظيفة تك جديدة الصبح ده"),
        "big_label": _t("new jobs, collected at 8 AM", "وظيفة جديدة، اتجمعت الساعة 8 الصبح"),
        "bars": [_bar("Egypt", "مصر", eg, top, str(eg)), _bar("Gulf", "الخليج", gulf, top, str(gulf)),
                 _bar("Remote", "ريموت", rem, top, str(rem))],
        "note": _t("Get them every morning on Telegram.", "خليها توصلك كل صبح على تيليجرام."),
        "link": "#country=Egypt",
    }


def egypt_skills(jobs, meta, today):
    skills = meta.get("skills", [])
    home = [j for j in jobs if _onsite_in(j, (HOME,)) and j.get("tr") == "Data & Analytics" and j.get("k")]
    if len(home) < 40:
        return None
    c = Counter(skills[i] for j in home for i in j["k"] if i < len(skills)).most_common(5)
    if not c:
        return None
    top = c[0][1]
    return {
        "id": "skills", "big": f"{_pct(top, len(home))}%",
        "title": _t(f"{c[0][0]} is in {_pct(top, len(home))}% of data jobs in Egypt",
                    f"{c[0][0]} مطلوب في {_pct(top, len(home))}% من وظايف الداتا في مصر"),
        "big_label": _t(f"of {len(home)} data jobs in Egypt ask for {c[0][0]}",
                        f"من {len(home)} وظيفة داتا في مصر طالبة {c[0][0]}"),
        "bars": [_bar(s, s, n, top, f"{_pct(n, len(home))}%") for s, n in c],
        "note": _t("Upload your CV on Radarak to see which of these you're missing.",
                   "ارفع الـ CV على رادارك وشوف ناقصك أنهي مهارة."),
        "link": "#country=Egypt&role=track%3AData%20%26%20Analytics",
    }


KINDS = [remote_reality, who_is_hiring, same_job_different_stack, career_ladder, salary_transparency,
         new_this_morning, egypt_skills]


def all_insights(jobs: list[dict], meta: dict, today: dt.date | None = None) -> dict:
    """{"date", "items"}: every insight that today's data supports, today's pick first (rotates daily)."""
    today = today or dt.date.today()
    uniq = _unique(jobs)
    items = []
    for kind in KINDS:
        try:
            ins = kind(uniq, meta, today)
        except (ValueError, ZeroDivisionError, KeyError, TypeError):
            ins = None
        if ins:
            items.append(ins)
    if items:
        start = today.toordinal() % len(items)
        items = items[start:] + items[:start]
    return {"date": today.isoformat(), "items": items}


def telegram_text(ins: dict, url: str) -> str:
    """The insight as a Telegram message (HTML), English then Arabic."""
    import html
    e = html.escape
    lines = [f"📊 <b>Insight of the day · معلومة النهارده</b>", "", f"<b>{e(ins['title']['en'])}</b>",
             f"<b>{e(ins['title']['ar'])}</b>", ""]
    for b in ins.get("bars", []):
        lines.append(f"• {e(b['l']['en'])}: <b>{e(b['t'])}</b>")
    lines += ["", f"<i>{e(ins['note']['en'])}</i>"]
    if url:
        lines.append(f'🔎 <a href="{e(url + "#insight", quote=True)}">radarak.online</a>')
    return "\n".join(lines)
