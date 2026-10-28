"""Static pages search engines can read: one page per country, per track in a country and per role
in a country (English and Arabic), plus /jobs/ indexes, sitemap.xml and robots.txt.

The app (index.html) builds everything in the browser from data/jobs.json, so Google sees an almost
empty page. These pages are plain HTML generated every day from the same export, each with that
day's jobs, the skills they ask for, who is hiring and pay, and links into the app.

Thin pages are not generated: a role page needs MIN_ROLE_JOBS jobs, a track page MIN_TRACK_JOBS.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import statistics
from collections import Counter
from urllib.parse import quote

MIN_COUNTRY_JOBS = 5
MIN_TRACK_JOBS = 5
MIN_ROLE_JOBS = 5
JOBS_LISTED = 25          # shown at first; "Show more" pages through the rest
LIST_CAP = 150            # jobs put on a page (the filters work on these); the app has them all
LEVELS = ["Intern / Student", "Junior", "Mid", "Senior", "Lead / Principal", "Head / Director"]
REMOTE = "Remote"

AR_PLACES = {
    "Remote": "ريموت", "Egypt": "مصر", "Saudi Arabia": "السعودية", "United Arab Emirates": "الإمارات", "Qatar": "قطر",
    "Kuwait": "الكويت", "Bahrain": "البحرين", "Oman": "عُمان", "Jordan": "الأردن", "Palestine": "فلسطين",
    "Lebanon": "لبنان", "Morocco": "المغرب", "Tunisia": "تونس", "Turkey": "تركيا", "Germany": "ألمانيا",
    "United Kingdom": "بريطانيا", "Netherlands": "هولندا", "France": "فرنسا", "Spain": "إسبانيا", "Ireland": "أيرلندا",
    "Poland": "بولندا", "Italy": "إيطاليا", "Portugal": "البرتغال", "Belgium": "بلجيكا", "Austria": "النمسا",
    "Switzerland": "سويسرا", "Sweden": "السويد", "Denmark": "الدنمارك", "Norway": "النرويج", "Finland": "فنلندا",
    "Estonia": "إستونيا", "Latvia": "لاتفيا", "Lithuania": "ليتوانيا", "Czechia": "التشيك", "Hungary": "المجر",
    "Romania": "رومانيا", "Bulgaria": "بلغاريا", "Greece": "اليونان", "Cyprus": "قبرص", "Malta": "مالطا",
    "Luxembourg": "لوكسمبورج", "Croatia": "كرواتيا", "Serbia": "صربيا", "Ukraine": "أوكرانيا",
    "United States": "أمريكا", "Canada": "كندا", "Mexico": "المكسيك", "Brazil": "البرازيل", "Argentina": "الأرجنتين",
    "India": "الهند", "Pakistan": "باكستان", "Singapore": "سنغافورة", "Malaysia": "ماليزيا", "Indonesia": "إندونيسيا",
    "Philippines": "الفلبين", "Vietnam": "فيتنام", "Thailand": "تايلاند", "Japan": "اليابان", "South Korea": "كوريا الجنوبية",
    "China": "الصين", "Hong Kong": "هونج كونج", "Taiwan": "تايوان", "Australia": "أستراليا", "New Zealand": "نيوزيلندا",
    "Nigeria": "نيجيريا", "Kenya": "كينيا", "South Africa": "جنوب أفريقيا", "Ghana": "غانا",
    "Algeria": "الجزائر",
    "Iraq": "العراق",
    "Libya": "ليبيا",
    "Sudan": "السودان",
    "Syria": "سوريا",
    "Yemen": "اليمن",
    "Mauritania": "موريتانيا",
    "Ethiopia": "إثيوبيا",
    "Uganda": "أوغندا",
    "Tanzania": "تنزانيا",
    "Rwanda": "رواندا",
    "Senegal": "السنغال",
    "Ivory Coast": "ساحل العاج",
    "Cameroon": "الكاميرون",
    "Zimbabwe": "زيمبابوي",
    "Zambia": "زامبيا",
    "Madagascar": "مدغشقر",
    "Mauritius": "موريشيوس",
    "Botswana": "بوتسوانا",
    "Angola": "أنغولا",
    "Mozambique": "موزمبيق",
    "Namibia": "ناميبيا",
    "Malawi": "ملاوي",
    "Benin": "بنين",
    "Togo": "توغو",
    "Somalia": "الصومال",
    "Bangladesh": "بنجلاديش",
    "Sri Lanka": "سريلانكا",
    "Nepal": "نيبال",
    "Kazakhstan": "كازاخستان",
    "Uzbekistan": "أوزبكستان",
    "Kyrgyzstan": "قيرغيزستان",
    "Mongolia": "منغوليا",
    "Cambodia": "كمبوديا",
    "Myanmar": "ميانمار",
    "Afghanistan": "أفغانستان",
    "Slovakia": "سلوفاكيا",
    "Slovenia": "سلوفينيا",
    "Albania": "ألبانيا",
    "Bosnia and Herzegovina": "البوسنة والهرسك",
    "North Macedonia": "مقدونيا الشمالية",
    "Montenegro": "الجبل الأسود",
    "Moldova": "مولدوفا",
    "Kosovo": "كوسوفو",
    "Iceland": "آيسلندا",
    "Georgia": "جورجيا",
    "Armenia": "أرمينيا",
    "Azerbaijan": "أذربيجان",
    "Belarus": "بيلاروسيا",
    "Russia": "روسيا",
    "Antigua and Barbuda": "أنتيغوا وباربودا",
    "Bahamas": "جزر البهاما",
    "Barbados": "باربادوس",
    "Belize": "بليز",
    "Bermuda": "برمودا",
    "Bolivia": "بوليفيا",
    "Cayman Islands": "جزر كايمان",
    "Chile": "تشيلي",
    "Colombia": "كولومبيا",
    "Costa Rica": "كوستاريكا",
    "Dominican Republic": "جمهورية الدومينيكان",
    "Ecuador": "الإكوادور",
    "El Salvador": "السلفادور",
    "Guatemala": "غواتيمالا",
    "Honduras": "هندوراس",
    "Jamaica": "جامايكا",
    "Nicaragua": "نيكاراغوا",
    "Panama": "بنما",
    "Paraguay": "باراغواي",
    "Peru": "بيرو",
    "Puerto Rico": "بورتوريكو",
    "Trinidad and Tobago": "ترينيداد وتوباغو",
    "Uruguay": "الأوروغواي",
    "Venezuela": "فنزويلا",
}

T = {
    "en": {
        "dir": "ltr", "home": "Radarak", "jobs": "Jobs", "other": "العربية",
        "h_country": "Tech jobs in {p}", "h_remote": "Remote tech jobs",
        "h_job": "{x} jobs in {p}", "h_job_remote": "Remote {x} jobs",
        "title": "{h} ({n} open) | Radarak",
        "sub": "{n} open {jobs} at {c} {companies} · updated {d}",
        "job1": "job", "jobsN": "jobs", "company1": "company", "companiesN": "companies",
        "cta": "Open in Radarak", "cta_hint": "Filter more, match your CV and save jobs in the app.",
        "cta_remote": "Plus {n} remote jobs open to people in {p}: see them in the app.",
        "s_open": "open jobs", "s_comp": "companies hiring", "s_remote": "remote", "s_pay": "median pay (USD / year)",
        "skills": "Skills these jobs ask for", "list": "Newest jobs", "list_more": "Showing the {k} newest of {n}. See them all in the app →",
        "companies_h": "Companies hiring", "roles_h": "Roles in {p}", "tracks_h": "Tracks in {p}",
        "elsewhere": "{x} jobs in other places", "countries_h": "Browse by country",
        "apply": "Apply", "remote": "Remote", "visa": "Visa / relocation",
        "about": ("Radarak collects tech jobs every morning from company career pages and job boards, and shows "
                  "the ones you can apply to from where you live. Free, no sign-up, Arabic and English."),
        "summary": "Radarak found {n} open {what} in {p} today, posted by {c} {companies}{eg}.",
        "summary_remote": "Radarak found {n} open {what} today that can be done remotely, posted by {c} {companies}{eg}.",
        "eg": " such as {names}", "sk": " The skills they ask for most are {skills}.",
        "rem": " {r}% of them are remote.", "pay": " Jobs that publish pay offer about ${m}k a year (median).",
        "what_country": "tech jobs", "what_x": "{x} jobs",
        "idx_title": "Tech jobs by country | Radarak", "idx_h": "Tech jobs by country",
        "idx_sub": "{n} open tech jobs in {k} places · updated {d}",
        "desc": "{n} open {what}{inp} at {c} companies, updated {d}.{sk} Free, no sign-up.",
        "desc_sk": " Top skills: {skills}.", "inp": " in {p}", "and": "and",
        "credits": "Each job links to the original posting; apply there.",
        "nav_companies": "Companies", "nav_juniors": "Juniors", "nav_salaries": "Salaries", "nav_jobs": "Jobs by country",
        "f_search": "Search title, company or skill", "f_place": "Country", "f_role": "Role", "f_level": "Level",
        "f_mode": "Work mode", "f_any": "Any", "f_visa": "Visa / relocation", "f_pay": "Shows salary",
        "f_toggle": "Filters", "f_sort": "Sort", "sort_new": "Newest", "sort_pay": "Highest pay", "f_clear": "Clear filters",
        "f_count": "{n} of {t} jobs", "f_more": "Show {n} more", "f_empty": "No jobs match these filters.",
        "modes": {"Remote": "Remote", "Hybrid": "Hybrid", "Onsite": "Onsite"},
        "cap_note": "This page lists the {k} newest of {n} jobs. Open the app to filter all of them →",
    },
    "ar": {
        "dir": "rtl", "home": "رادارك", "jobs": "الوظايف", "other": "English",
        "h_country": "وظايف التك في {p}", "h_remote": "وظايف تك ريموت",
        "h_job": "وظايف {x} في {p}", "h_job_remote": "وظايف {x} ريموت",
        "title": "{h} ({n} متاحة) | رادارك",
        "sub": "{n} {jobs} متاحة في {c} {companies} · آخر تحديث {d}",
        "job1": "وظيفة", "jobsN": "وظيفة", "company1": "شركة", "companiesN": "شركة",
        "cta": "افتح في رادارك", "cta_hint": "فلتر أكتر، طابق الـ CV بتاعك، واحفظ الوظايف في التطبيق.",
        "cta_remote": "وكمان {n} وظيفة ريموت متاحة للي في {p}: شوفها في التطبيق.",
        "s_open": "وظيفة متاحة", "s_comp": "شركة بتوظف", "s_remote": "ريموت", "s_pay": "متوسط المرتب (دولار / سنة)",
        "skills": "المهارات المطلوبة في الوظايف دي", "list": "أحدث الوظايف", "list_more": "دي أحدث {k} من {n}. شوفهم كلهم في التطبيق ←",
        "companies_h": "شركات بتوظف", "roles_h": "وظايف في {p}", "tracks_h": "مجالات في {p}",
        "elsewhere": "وظايف {x} في أماكن تانية", "countries_h": "تصفّح حسب البلد",
        "apply": "قدّم", "remote": "ريموت", "visa": "فيزا / انتقال",
        "about": ("رادارك بيجمع وظايف التك كل يوم الصبح من صفحات توظيف الشركات ومواقع الوظايف، وبيعرضلك "
                  "اللي تقدر تقدّم عليها من البلد اللي إنت فيها. مجاني ومن غير تسجيل، عربي وإنجليزي."),
        "summary": "رادارك لقى النهارده {n} {what} متاحة في {p}، في {c} {companies}{eg}.",
        "summary_remote": "رادارك لقى النهارده {n} {what} متاحة ريموت، في {c} {companies}{eg}.",
        "eg": " زي {names}", "sk": " أكتر مهارات مطلوبة: {skills}.",
        "rem": " {r}% منها ريموت.", "pay": " الوظايف اللي بتعلن المرتب بتدفع حوالي {m} ألف دولار في السنة (المتوسط).",
        "what_country": "وظيفة تك", "what_x": "وظيفة {x}",
        "idx_title": "وظايف التك حسب البلد | رادارك", "idx_h": "وظايف التك حسب البلد",
        "idx_sub": "{n} وظيفة تك متاحة في {k} مكان · آخر تحديث {d}",
        "desc": "{n} {what} متاحة{inp} في {c} شركة، آخر تحديث {d}.{sk} مجاني ومن غير تسجيل.",
        "desc_sk": " أهم المهارات: {skills}.", "inp": " في {p}", "and": "و",
        "credits": "كل وظيفة ليها لينك للإعلان الأصلي، والتقديم بيكون هناك.",
        "nav_companies": "الشركات", "nav_juniors": "الجونيور", "nav_salaries": "المرتبات", "nav_jobs": "الوظايف حسب البلد",
        "f_search": "دوّر بالوظيفة أو الشركة أو المهارة", "f_place": "الدولة", "f_role": "الوظيفة", "f_level": "المستوى",
        "f_mode": "نوع الشغل", "f_any": "الكل", "f_visa": "فيزا / انتقال", "f_pay": "فيها مرتب",
        "f_toggle": "الفلاتر", "f_sort": "رتّب", "sort_new": "الأحدث", "sort_pay": "الأعلى مرتب", "f_clear": "امسح الفلاتر",
        "f_count": "{n} من {t} وظيفة", "f_more": "اعرض {n} كمان", "f_empty": "مفيش وظايف بالفلاتر دي.",
        "modes": {"Remote": "ريموت", "Hybrid": "هايبرد", "Onsite": "من المكتب"},
        "cap_note": "الصفحة دي فيها أحدث {k} من {n} وظيفة. افتح التطبيق عشان تفلتر كلهم ←",
    },
}


def slug(text: str) -> str:
    s = text.lower().replace("&", " and ").replace("c#", "csharp").replace(".net", "dotnet").replace("+", "plus")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def place_name(place: str, lang: str) -> str:
    return AR_PLACES.get(place, place) if lang == "ar" else place


def _e(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def _num(n: int) -> str:
    return f"{n:,}"


def _date(d: dt.date, lang: str) -> str:
    months_ar = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
    return f"{d.day} {months_ar[d.month - 1]} {d.year}" if lang == "ar" else d.strftime("%-d %B %Y")


def _list_words(items: list[str], lang: str) -> str:
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    sep = "، " if lang == "ar" else ", "
    return sep.join(items[:-1]) + f" {T[lang]['and']} " + items[-1] if lang == "en" else sep.join(items[:-1]) + " و" + items[-1]


class _Page:
    def __init__(self, kind: str, place: str, label: str | None, jobs: list[dict], parent_label: str | None = None):
        self.kind, self.place, self.label, self.jobs, self.parent_label = kind, place, label, jobs, parent_label
        self.place_slug = "remote" if place == REMOTE else slug(place)
        self.x_slug = None

    def path(self, lang: str) -> str:
        parts = (["ar"] if lang == "ar" else []) + ["jobs", self.place_slug] + ([self.x_slug] if self.x_slug else [])
        return "/".join(parts) + "/index.html"

    def url_path(self, lang: str) -> str:
        return self.path(lang)[: -len("index.html")]


def _jobs_in(jobs: list[dict], place: str) -> list[dict]:
    if place == REMOTE:
        return [j for j in jobs if j.get("w") == "Remote"]
    return [j for j in jobs if place in (j.get("co") or [])]


def build_pages(jobs: list[dict], meta: dict) -> list[_Page]:
    tracks = [t["name"] for t in meta.get("tracks", [])]
    counts = Counter(c for j in jobs for c in (j.get("co") or []))
    places = [p for p, n in counts.most_common() if n >= MIN_COUNTRY_JOBS and p in AR_PLACES or n >= MIN_COUNTRY_JOBS * 4]
    if sum(1 for j in jobs if j.get("w") == "Remote") >= MIN_COUNTRY_JOBS:
        places.insert(min(1, len(places)), REMOTE)
    pages: list[_Page] = []
    for place in places:
        pj = _jobs_in(jobs, place)
        pages.append(_Page("country", place, None, pj))
        used = set()
        for tr in tracks:
            tj = [j for j in pj if j.get("tr") == tr]
            if len(tj) >= MIN_TRACK_JOBS:
                p = _Page("track", place, tr, tj)
                p.x_slug = slug(tr)
                used.add(p.x_slug)
                pages.append(p)
        role_counts = Counter(j.get("r") for j in pj if j.get("r"))
        for role, n in role_counts.most_common():
            if n < MIN_ROLE_JOBS or role == "Other tech role":
                continue
            p = _Page("role", place, role, [j for j in pj if j.get("r") == role],
                      parent_label=next((j.get("tr") for j in pj if j.get("r") == role), None))
            p.x_slug = slug(role) if slug(role) not in used else slug(role) + "-role"
            used.add(p.x_slug)
            pages.append(p)
    return pages


# ------------------------------------------------------------------------------------------- rendering
CSS = """
.seo{max-width:var(--wrap);margin-inline:auto;padding:0 20px 48px}
.crumbs{font-size:14px;color:var(--muted);margin:22px 0 6px;display:flex;flex-wrap:wrap;gap:6px}
.crumbs a{color:var(--violet-ink);text-decoration:none}.crumbs a:hover{text-decoration:underline}
.seo h1{font:800 clamp(28px,4.4vw,44px)/1.1 var(--display);letter-spacing:-.02em;margin:6px 0 8px}
.seo .lead{font-size:16px;color:var(--ink-2);margin:0 0 18px}
.seo .ctarow{display:flex;flex-wrap:wrap;align-items:center;gap:10px 16px;margin:0 0 22px}
.seo .ctarow .primary{text-decoration:none;display:inline-flex;padding:13px 18px}
.seo .ctarow span{font-size:14px;color:var(--muted)}
.seo .stats{margin:0 0 22px;display:flex;flex-wrap:wrap}.seo .stat{flex:1 1 170px}
.seo .summary{font-size:16px;line-height:1.7;margin:0 0 24px;max-width:860px}
.seo .cols{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:22px;align-items:start}
.seo .panel h2,.seo section h2{font:800 20px/1.2 var(--display);margin:0 0 12px}
.slist{list-style:none;margin:0;padding:0;border:1px solid var(--line);border-radius:var(--r-l);background:var(--surface);overflow:hidden}
.slist li{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 14px;padding:14px 18px;align-items:center}
.slist li+li{border-top:1px solid var(--line)}
.slist h3{margin:0;font-size:16px;line-height:1.3}.slist h3 a{color:var(--ink);text-decoration:none}.slist h3 a:hover{color:var(--violet-ink);text-decoration:underline}
.slist p{margin:2px 0 0;font-size:14px;color:var(--ink-2)}.slist .m{color:var(--muted);font-size:13px}
.slist .go{font:600 14px/1 var(--font);color:#fff;background:var(--violet);border-radius:99px;padding:9px 14px;text-decoration:none;white-space:nowrap}
.slist .sk{display:flex;flex-wrap:wrap;gap:4px 10px;margin-top:4px;font-size:13px;color:var(--muted)}
.more2{display:inline-block;margin-top:12px;font-weight:600;color:var(--violet-ink)}
.fbar{display:flex;flex-wrap:wrap;gap:8px 10px;align-items:end;padding:12px;margin:0 0 10px;background:var(--surface);border:1px solid var(--line);border-radius:var(--r-m)}
.fbar label{display:flex;flex-direction:column;gap:3px;font-size:12px;color:var(--muted)}
.fbar .fsearch{flex:1 1 240px}
.fbar input[type=search],.fbar select{font:500 14px/1.2 var(--font);color:var(--ink);background:var(--paper);border:1px solid var(--line-strong);border-radius:var(--r-s);padding:9px 10px;min-width:0}
.fbar select{max-width:220px}
.fbar input[type=search],.fbar select{height:40px;box-sizing:border-box}
.fbar .fchk{flex-direction:row;align-items:center;gap:6px;font-size:14px;color:var(--ink-2);padding:9px 2px;cursor:pointer}
.fbar .fchk input{width:16px;height:16px;accent-color:var(--violet)}
.fmeta{display:flex;align-items:center;gap:12px;margin:0 0 10px;font-size:14px;color:var(--muted)}
.fmore{margin-top:12px}
.fempty{padding:16px 0}
.ftoggle{display:none;font:600 14px/1 var(--font);color:var(--ink-2);background:var(--paper);border:1px solid var(--line-strong);border-radius:var(--r-s);padding:10px 12px;cursor:pointer}
.ftoggle.on{border-color:var(--violet);color:var(--violet-ink)}
@media (max-width:600px){.fbar .fsel{flex:1 1 45%}.fbar select{max-width:none;width:100%}
  .fbar .fsearch{flex:1 1 0}.ftoggle{display:block}
  .fbar:not(.open) .fsel,.fbar:not(.open) .fchk{display:none}}
.side{display:flex;flex-direction:column;gap:18px}
.side .panel{padding:16px 18px}
.skb{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.skb li{display:grid;grid-template-columns:110px 1fr 40px;align-items:center;gap:8px;font-size:14px}
.skb i{display:block;height:8px;border-radius:4px;background:var(--violet)}
.skb b{font-weight:600;font-variant-numeric:tabular-nums;text-align:end}
.links{display:flex;flex-wrap:wrap;gap:8px}
.links a{font:500 14px/1 var(--font);color:var(--ink-2);background:var(--surface);border:1px solid var(--line-strong);border-radius:99px;padding:9px 12px;text-decoration:none}
.links a:hover{border-color:var(--violet);color:var(--violet-ink)}
.links a span{color:var(--muted);margin-inline-start:4px}
.seo section{margin-top:28px}
.complist{margin:0;padding-inline-start:20px;font-size:15px}.complist li{margin:4px 0}
.seofoot{max-width:var(--wrap);margin:0 auto;padding:22px 20px 40px;color:var(--muted);font-size:14px;border-top:1px solid var(--line)}
.alerts{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px;margin:0 0 22px;padding:12px 14px;border-radius:var(--r-m);background:var(--surface);border:1px solid var(--line)}
.alerts p{margin:0;flex:1 1 220px;font-size:15px;color:var(--ink-2)}
.alerts .primary{text-decoration:none;display:inline-flex;padding:10px 16px}
.alerts .tg{background:#229ED9}.alerts .rss{font-weight:600;font-size:14px;color:var(--violet-ink)}
.jobpage .m{color:var(--muted);font-size:15px;margin:0 0 12px}
.jobpage .sk{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 18px}
.jobpage .sk span{font-size:13px;background:var(--surface);border:1px solid var(--line);border-radius:99px;padding:5px 10px}
.jobpage .ghostbtn{text-decoration:none}
.jobpage .jd{max-width:820px;font-size:16px;line-height:1.7;margin-top:8px}
.jobpage .jd ul{padding-inline-start:22px}.jobpage .jd li{margin:4px 0}
.jobpage .note{color:var(--muted);font-size:14px;max-width:820px}
@media (max-width:860px){.seo .cols{grid-template-columns:1fr}}
@media (max-width:600px){.slist li{grid-template-columns:1fr}.slist .go{justify-self:start}.skb li{grid-template-columns:96px 1fr 36px}}
"""

BRAND_SVG = ('<svg viewBox="0 0 32 32" aria-hidden="true"><circle class="disc" cx="16" cy="16" r="15"/><circle class="ring" '
             'cx="16" cy="16" r="8.5"/><circle cx="22.5" cy="9.5" r="3" fill="#FFB020"/><circle cx="9.5" cy="19.5" r="2.5" '
             'fill="#FF5C39"/><circle cx="19.5" cy="22.5" r="2.1" fill="#12B886"/></svg>')


def _shell(lang: str, rel: str, title: str, desc: str, canonical: str, alt_en: str, alt_ar: str, other_href: str,
           body: str, jsonld: dict | list, og_image: str, head_extra: str = "") -> str:
    """alt_en / alt_ar None: a page in one language only (no hreflang links, no language switch)."""
    t = T[lang]
    alternates = "" if alt_en is None else (
        f'<link rel="alternate" hreflang="en" href="{_e(alt_en)}">\n'
        f'  <link rel="alternate" hreflang="ar" href="{_e(alt_ar)}">\n'
        f'  <link rel="alternate" hreflang="x-default" href="{_e(alt_en)}">')
    other = "" if other_href is None else (
        f'<a class="langbtn" href="{_e(other_href)}" lang="{"en" if lang == "ar" else "ar"}">{t["other"]}</a>')
    return f"""<!doctype html>
<html lang="{lang}" dir="{t['dir']}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_e(title)}</title>
  <meta name="description" content="{_e(desc)}">
  <link rel="canonical" href="{_e(canonical)}">
  {alternates}{head_extra}
  <meta name="theme-color" content="#FFFFFF">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{_e(title)}">
  <meta property="og:description" content="{_e(desc)}">
  <meta property="og:url" content="{_e(canonical)}">
  <meta property="og:image" content="{_e(og_image)}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="{rel}icons/icon-192.png">
  <link rel="manifest" href="{rel}manifest.webmanifest">
  <link rel="stylesheet" href="{rel}style.css">
  <link rel="stylesheet" href="{rel}seo.css">
  <link rel="stylesheet" href="{rel}extra.css">
  <script src="{rel}pages.js" defer></script>
  <script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/")}</script>
</head>
<body class="seopage">
  <header class="topbar"><div class="topbar-in">
    <a class="brand" href="{rel}">{BRAND_SVG}<span>{t['home']}</span></a>
    <nav class="topnav seonav">{''.join(f'<a class="navlink" href="{rel}{"ar/" if lang == "ar" else ""}{h}/">{_e(t[k])}</a>'
                                         for h, k in (("jobs", "nav_jobs"), ("companies", "nav_companies"),
                                                      ("juniors", "nav_juniors"), ("salaries", "nav_salaries")))}
      {other}</nav>
  </div></header>
{body}
  <footer class="seofoot"><!--newsletter:{lang}--><p>{_e(t['about'])}</p><p>{_e(t['credits'])}</p></footer>
</body>
</html>
"""


def _median_pay(jobs: list[dict]) -> int | None:
    pays = [(j["$"][0] + j["$"][1]) / 2 for j in jobs if j.get("$")]
    return round(statistics.median(pays)) if len(pays) >= 3 else None


def _top_skills(jobs: list[dict], skills: list[str], k: int = 10) -> list[tuple[str, int]]:
    c = Counter(i for j in jobs for i in j.get("k", []))
    n = len(jobs) or 1
    return [(skills[i], round(100 * v / n)) for i, v in c.most_common(k) if i < len(skills)]


def _unique(jobs: list[dict]) -> list[dict]:
    """The same job is often posted once per city: list it once."""
    seen, out = set(), []
    for j in sorted(jobs, key=lambda x: x.get("p", ""), reverse=True):
        key = (j.get("t", "").lower(), (j.get("c") or "").lower())
        if key not in seen:
            seen.add(key)
            out.append(j)
    return out


def _ago(iso: str, today: dt.date, lang: str) -> str:
    try:
        days = (today - dt.date.fromisoformat(iso)).days
    except ValueError:
        return ""
    if lang == "ar":
        return "النهارده" if days <= 0 else "امبارح" if days == 1 else f"من {days} يوم"
    return "today" if days <= 0 else "yesterday" if days == 1 else f"{days} days ago"


def _app_hash(page: _Page) -> str:
    h = []
    if page.place == REMOTE:
        h.append("remote=1")
    else:
        h.append("country=" + quote(page.place))
    if page.kind == "track":
        h.append("role=" + quote("track:" + page.label))
    elif page.kind == "role":
        h.append("role=" + quote("role:" + page.label))
    return "#" + "&".join(h)


def _job_li(j: dict, rel: str, lang: str, today: dt.date, skills: list[str]) -> str:
    """One job row: title (opens it in the app), company, place, mode, age, pay, skills and Apply."""
    t = T[lang]
    meta_bits = [t["remote"] if j.get("w") == "Remote" else (j.get("w") or ""), _ago(j.get("p", ""), today, lang)]
    if j.get("$"):
        lo, hi = j["$"]
        meta_bits.append(f"${lo}k" if lo == hi else f"${lo}k–${hi}k")
    if (j.get("f") or 0) & 1:
        meta_bits.append(t["visa"])
    sk = "".join(f"<span>{_e(skills[i])}</span>" for i in j.get("k", [])[:6] if i < len(skills))
    by = f' <span class="m">· {_e(j["by"])}</span>' if j.get("by") else ""
    pay = (j["$"][0] + j["$"][1]) / 2 if j.get("$") else ""
    text = " ".join([j.get("t") or "", j.get("c") or "", j.get("r") or ""] + [skills[i] for i in j.get("k", []) if i < len(skills)])
    attrs = (f' data-co="{_e("|".join(j.get("co") or []))}" data-r="{_e(j.get("r") or "")}" data-s="{_e(j.get("s") or "")}"'
             f' data-w="{_e(j.get("w") or "")}" data-v="{1 if (j.get("f") or 0) & 1 else 0}" data-hp="{1 if pay != "" else 0}"'
             f' data-pay="{pay}" data-p="{_e(j.get("p") or "")}" data-t="{_e(text.lower())}"')
    # the title opens the job's own page when it has one (job_pages), otherwise the job in the app
    href = rel + j["pg"] if j.get("pg") else f'{rel}#job={quote(j["id"])}'
    return (f'<li{attrs}><div><h3><a href="{_e(href)}">{_e(j.get("t"))}</a></h3>'
            f'<p><b>{_e(j.get("c") or "")}</b> · {_e(j.get("l") or "")}</p>'
            f'<p class="m">{_e(" · ".join(b for b in meta_bits if b))}{by}</p>'
            + (f'<p class="sk">{sk}</p>' if sk else "")
            + f'</div><a class="go" href="{_e(j.get("u"))}" target="_blank" rel="{'noopener' if j.get('df') else 'nofollow noopener'}">{t["apply"]}</a></li>')


def job_list(jobs: list[dict], rel: str, lang: str, today: dt.date, skills: list[str], *, show_place: bool = True,
             show_role: bool = True, cap: int = LIST_CAP, app: str | None = None, total: int | None = None) -> str:
    """A job list with the main page's filters: search, country, role, level, work mode, visa, salary, sort."""
    t = T[lang]
    listed = jobs[:cap]
    total = total if total is not None else len(jobs)

    def select(f: str, label: str, options: list[tuple[str, str]]) -> str:
        if len(options) < 2:
            return ""
        opts = "".join(f'<option value="{_e(v)}">{_e(lbl)}</option>' for v, lbl in options)
        return (f'<label class="fsel"><span>{_e(label)}</span><select data-f="{f}">'
                f'<option value="">{_e(t["f_any"])}</option>{opts}</select></label>')
    places = Counter(c for j in listed for c in (j.get("co") or []))
    roles = Counter(j.get("r") for j in listed if j.get("r"))
    levels = {j.get("s") for j in listed}
    modes = {j.get("w") for j in listed}
    controls = [
        f'<label class="fsearch"><span class="sr">{_e(t["f_search"])}</span><input type="search" data-f="t" data-mode="text" '
        f'placeholder="{_e(t["f_search"])}" autocomplete="off"></label>',
        select("co", t["f_place"], [(p, place_name(p, lang)) for p, _ in places.most_common(30)]) if show_place else "",
        select("r", t["f_role"], [(r, f"{r} ({k})") for r, k in roles.most_common(40)]) if show_role else "",
        select("s", t["f_level"], [(v, v) for v in LEVELS if v in levels]),
        select("w", t["f_mode"], [(m, t["modes"].get(m, m)) for m in ("Remote", "Hybrid", "Onsite") if m in modes]),
        f'<label class="fchk"><input type="checkbox" data-f="v" data-mode="flag"><span>{_e(t["f_visa"])}</span></label>'
        if any((j.get("f") or 0) & 1 for j in listed) else "",
        f'<label class="fchk"><input type="checkbox" data-f="hp" data-mode="flag"><span>{_e(t["f_pay"])}</span></label>'
        if any(j.get("$") for j in listed) else "",
        f'<label class="fsel"><span>{_e(t["f_sort"])}</span><select data-sort><option value="p:desc">{_e(t["sort_new"])}</option>'
        f'<option value="pay:num">{_e(t["sort_pay"])}</option></select></label>',
    ]
    note = (f'<a class="more2" href="{_e(app)}">{_e(t["cap_note"].format(k=_num(len(listed)), n=_num(total)))}</a>'
            if app and total > len(listed) else "")
    return f"""<div class="fblock" data-filters data-page="{JOBS_LISTED}">
        <div class="fbar">{controls[0]}<button type="button" class="ftoggle" data-ftoggle aria-expanded="false">{_e(t['f_toggle'])}</button>{''.join(controls[1:])}</div>
        <div class="fmeta"><span data-count data-tpl="{_e(t['f_count'])}">{_num(len(listed))}</span>
          <button type="button" class="linkbtn" data-clear hidden>{_e(t['f_clear'])}</button></div>
        <ol class="slist" data-list>{''.join(_job_li(j, rel, lang, today, skills) for j in listed)}</ol>
        <p class="note fempty" data-empty hidden>{_e(t['f_empty'])}</p>
        <button type="button" class="more fmore" data-more data-tpl="{_e(t['f_more'])}" hidden></button>
        {note}
      </div>"""


def _render(page: _Page, lang: str, pages_by_place: dict, all_pages: list[_Page], meta: dict, base: str,
            today: dt.date, remote_pool: dict) -> str:
    t, skills = T[lang], meta.get("skills", [])
    depth = page.path(lang).count("/")
    rel = "../" * depth
    place = place_name(page.place, lang)
    uj = _unique(page.jobs)
    n, comps = len(uj), Counter(j.get("c") for j in uj if j.get("c"))
    c = len(comps)
    if page.kind == "country":
        h1 = t["h_remote"] if page.place == REMOTE else t["h_country"].format(p=place)
        what = t["what_country"]
    else:
        h1 = (t["h_job_remote"] if page.place == REMOTE else t["h_job"]).format(x=page.label, p=place)
        what = t["what_x"].format(x=page.label)
    top = _top_skills(uj, skills)
    pay = _median_pay(uj)
    remote_pct = round(100 * sum(1 for j in uj if j.get("w") == "Remote") / n) if n else 0
    d = _date(today, lang)
    jobsw = t["job1"] if n == 1 else t["jobsN"]
    compw = t["company1"] if c == 1 else t["companiesN"]
    title = t["title"].format(h=h1, n=_num(n))
    sk3 = _list_words([s for s, _ in top[:3]], lang)
    desc = t["desc"].format(n=_num(n), what=what, inp="" if page.place == REMOTE else t["inp"].format(p=place), c=_num(c),
                            d=d, sk=t["desc_sk"].format(skills=sk3) if top else "")
    names = _list_words([name for name, _ in comps.most_common(3)], lang)
    summary = (t["summary_remote"] if page.place == REMOTE else t["summary"]).format(
        n=_num(n), what=what, p=place, c=_num(c), companies=compw, eg=t["eg"].format(names=names) if names else "")
    if top:
        summary += t["sk"].format(skills=sk3)
    if page.place != REMOTE and remote_pct:
        summary += t["rem"].format(r=remote_pct)
    if pay:
        summary += t["pay"].format(m=pay)

    url_en, url_ar = base + page.url_path("en"), base + page.url_path("ar")
    canonical = url_ar if lang == "ar" else url_en
    other_href = rel + page.url_path("en" if lang == "ar" else "ar")
    jobs_idx = rel + ("ar/" if lang == "ar" else "") + "jobs/"
    country_page = next(p for p in pages_by_place[page.place] if p.kind == "country")

    # (label, link relative to this page, absolute URL)
    crumbs = [(t["home"], rel, base), (t["jobs"], jobs_idx, base + ("ar/" if lang == "ar" else "") + "jobs/")]
    if page.kind != "country":
        crumbs.append((place, rel + country_page.url_path(lang), base + country_page.url_path(lang)))
        crumbs.append((page.label, None, canonical))
    else:
        crumbs.append((place, None, canonical))
    crumb_html = " › ".join(f'<a href="{_e(h)}">{_e(x)}</a>' if h else f"<span>{_e(x)}</span>" for x, h, _ in crumbs)
    jsonld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": x, "item": u} for i, (x, _, u) in enumerate(crumbs)]}

    app = rel + _app_hash(page)
    from jobradar import alerts
    feed_x = page.x_slug if page.kind == "track" else None
    alerts_html = alerts.alerts_block(page.place, meta, rel, lang, feed_x)
    feed = (meta.get("feeds") or {}).get(f"{page.place}|{feed_x}" if feed_x else page.place)
    rss_head = (f'\n  <link rel="alternate" type="application/rss+xml" title="{_e(h1)}" href="{_e(base + feed)}">'
                if feed else "")
    hint = t["cta_hint"]
    if page.place != REMOTE:
        region = next((c.get("region") for c in meta.get("countries", []) if c.get("name") == page.place), None)
        pool = remote_pool.get(page.kind == "country" and "*" or page.label, [])
        extra = len(_unique([j for j in pool if page.place not in (j.get("co") or [])
                             and (j.get("ww") or "Worldwide" in (j.get("rg") or []) or (region and region in (j.get("rg") or [])))]))
        if extra:
            hint = t["cta_remote"].format(n=_num(extra), p=place)
    stats = [(_num(n), t["s_open"]), (_num(c), t["s_comp"])]
    if page.place != REMOTE and remote_pct:
        stats.append((f"{remote_pct}%", t["s_remote"]))
    if pay:
        stats.append((f"${pay}k", t["s_pay"]))
    stats_html = "".join(f'<div class="stat"><b>{v}</b><span>{_e(label)}</span></div>' for v, label in stats)

    top_max = max([v for _, v in top] or [1])
    skills_html = "".join(f'<li><span>{_e(s)}</span><span><i style="width:{max(3, round(100 * v / top_max))}%"></i></span><b>{v}%</b></li>'
                          for s, v in top)
    cslugs = meta.get("_company_slugs", {})
    comp_html = "".join((f'<li><a href="{_e(rel + ("ar/" if lang == "ar" else "") + "companies/" + cslugs[name] + "/")}">{_e(name)}</a>'
                         if name in cslugs else f"<li>{_e(name)}") + f' <span class="m">({v})</span></li>'
                        for name, v in comps.most_common(8))

    siblings = pages_by_place[page.place]
    def link(p: _Page, label: str) -> str:
        return f'<a href="{_e(rel + p.url_path(lang))}">{_e(label)}<span>{_num(len(_unique(p.jobs)))}</span></a>'
    track_links = "".join(link(p, p.label) for p in siblings if p.kind == "track" and p is not page)
    role_links = "".join(link(p, p.label) for p in sorted((p for p in siblings if p.kind == "role" and p is not page),
                                                         key=lambda p: -len(_unique(p.jobs)))[:24])
    elsewhere = ""
    if page.kind != "country":
        same = sorted((p for p in all_pages if p.kind == page.kind and p.label == page.label and p.place != page.place),
                      key=lambda p: -len(_unique(p.jobs)))[:12]
        if same:
            elsewhere = (f'<section><h2>{_e(t["elsewhere"].format(x=page.label))}</h2><div class="links">'
                         + "".join(link(p, place_name(p.place, lang)) for p in same) + "</div></section>")
    countries = ""
    if page.kind == "country":
        others = [ps[0] for pl, ps in pages_by_place.items() if pl != page.place][:30]
        countries = (f'<section><h2>{_e(t["countries_h"])}</h2><div class="links">'
                     + "".join(link(p, place_name(p.place, lang)) for p in others) + "</div></section>")

    body = f"""  <main class="seo">
    <nav class="crumbs" aria-label="Breadcrumb">{crumb_html}</nav>
    <h1>{_e(h1)}</h1>
    <p class="lead">{_e(t['sub'].format(n=_num(n), jobs=jobsw, c=_num(c), companies=compw, d=d))}</p>
    <div class="ctarow"><a class="primary" href="{_e(app)}">{_e(t['cta'])} →</a><span>{_e(hint)}</span></div>
    {alerts_html}
    <div class="stats">{stats_html}</div>
    <p class="summary">{_e(summary)}</p>
    <div class="cols">
      <section style="margin-top:0"><h2>{_e(t['list'])}</h2>
      {job_list(uj, rel, lang, today, skills, show_place=page.place == REMOTE, show_role=page.kind != "role", app=app, total=n)}</section>
      <aside class="side">
        {f'<div class="panel"><h2>{_e(t["skills"])}</h2><ol class="skb">{skills_html}</ol></div>' if top else ''}
        {f'<div class="panel"><h2>{_e(t["companies_h"])}</h2><ol class="complist">{comp_html}</ol></div>' if comp_html else ''}
      </aside>
    </div>
    {f'<section><h2>{_e(t["tracks_h"].format(p=place))}</h2><div class="links">{track_links}</div></section>' if track_links else ''}
    {f'<section><h2>{_e(t["roles_h"].format(p=place))}</h2><div class="links">{role_links}</div></section>' if role_links else ''}
    {elsewhere}{countries}
  </main>"""
    return _shell(lang, rel, title, desc, canonical, url_en, url_ar, other_href, body, jsonld, base + "og.png",
                  head_extra=rss_head)


def _render_index(lang: str, pages_by_place: dict, meta: dict, base: str, today: dt.date, total: int) -> str:
    t = T[lang]
    rel = "../" * (2 if lang == "ar" else 1)
    url_en, url_ar = base + "jobs/", base + "ar/jobs/"
    blocks = []
    for place, ps in pages_by_place.items():
        cp = ps[0]
        roles = sorted((p for p in ps if p.kind == "role"), key=lambda p: -len(_unique(p.jobs)))[:8]
        role_links = "".join(f'<a href="{_e(rel + p.url_path(lang))}">{_e(p.label)}<span>{_num(len(_unique(p.jobs)))}</span></a>'
                             for p in roles)
        name = place_name(place, lang)
        blocks.append(f'<section><h2><a href="{_e(rel + cp.url_path(lang))}">{_e(t["h_remote"] if place == REMOTE else t["h_country"].format(p=name))}</a>'
                      f' <span class="m">({_num(len(_unique(cp.jobs)))})</span></h2><div class="links">{role_links}</div></section>')
    body = f"""  <main class="seo">
    <nav class="crumbs"><a href="{rel}">{_e(t['home'])}</a> › <span>{_e(t['jobs'])}</span></nav>
    <h1>{_e(t['idx_h'])}</h1>
    <p class="lead">{_e(t['idx_sub'].format(n=_num(total), k=len(pages_by_place), d=_date(today, lang)))}</p>
    <div class="ctarow"><a class="primary" href="{rel}">{_e(t['cta'])} →</a><span>{_e(t['cta_hint'])}</span></div>
    {''.join(blocks)}
  </main>"""
    jsonld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": t["home"], "item": base},
        {"@type": "ListItem", "position": 2, "name": t["jobs"], "item": url_ar if lang == "ar" else url_en}]}
    return _shell(lang, rel, t["idx_title"], t["idx_sub"].format(n=_num(total), k=len(pages_by_place), d=_date(today, lang)),
                  url_ar if lang == "ar" else url_en, url_en, url_ar, rel + ("jobs/" if lang == "ar" else "ar/jobs/"),
                  body, jsonld, base + "og.png")


def seo_files(jobs: list[dict], meta: dict, base_url: str, today: dt.date | None = None) -> dict[str, bytes]:
    """All search-engine pages + seo.css + sitemap.xml + robots.txt, keyed by published path."""
    today = today or dt.date.today()
    base = base_url.rstrip("/") + "/"
    pages = build_pages(jobs, meta)
    from jobradar import alerts, job_pages
    feeds, meta["feeds"] = alerts.rss_files(pages, base, today, meta.get("skills", []))   # meta.json gets the list too
    from jobradar.extra_pages import company_slugs
    meta = {**meta, "_company_slugs": company_slugs(jobs)}
    by_place: dict[str, list[_Page]] = {}
    for p in pages:
        by_place.setdefault(p.place, []).append(p)
    out: dict[str, bytes] = {"seo.css": CSS.strip().encode(), **feeds}
    remote_jobs = [j for j in jobs if j.get("w") == "Remote"]
    remote_pool: dict[str, list[dict]] = {"*": remote_jobs}     # remote jobs by track / role, for "plus N remote jobs"
    for j in remote_jobs:
        remote_pool.setdefault(j.get("tr"), []).append(j)
        remote_pool.setdefault(j.get("r"), []).append(j)
    for lang in ("en", "ar"):
        for p in pages:
            out[p.path(lang)] = _render(p, lang, by_place, pages, meta, base, today, remote_pool).encode()
        out[("ar/" if lang == "ar" else "") + "jobs/index.html"] = _render_index(
            lang, by_place, meta, base, today, len(_unique(jobs))).encode()
    urls = [(base, "1.0"), (base + "jobs/", "0.9"), (base + "ar/jobs/", "0.9"), (base + "report.html", "0.5")]
    for p in pages:
        prio = "0.8" if p.kind == "country" else "0.7" if p.kind == "track" else "0.6"
        urls += [(base + p.url_path("en"), prio), (base + p.url_path("ar"), prio)]
    from jobradar import extra_pages
    place_pages = {p.place: p.url_path("en") for p in pages if p.kind == "country"}
    extra, extra_urls = extra_pages.extra_files(jobs, meta, base, today, place_pages)
    out.update(extra)
    urls += extra_urls
    lastmod = today.isoformat()
    out["sitemap.xml"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                          + "".join(f"  <url><loc>{_e(u)}</loc><lastmod>{lastmod}</lastmod><changefreq>daily</changefreq>"
                                    f"<priority>{pr}</priority></url>\n" for u, pr in urls)
                          + "</urlset>\n").encode()
    # one page per job (jobs from company career sites that have a description), for Google's job search
    place_pages: dict[str, dict[str, str]] = {}
    for p in pages:
        key = "" if p.kind == "country" else f"{p.kind}:{p.label}"
        place_pages.setdefault(p.place, {})[key] = p.url_path("en")
    jp, jp_urls = job_pages.job_page_files(jobs, meta, base, place_pages)
    out.update(jp)
    sitemaps = ["sitemap.xml"]
    if jp_urls:
        out["sitemap-jobs.xml"] = job_pages.sitemap(jp_urls)
        sitemaps.append("sitemap-jobs.xml")
    out["robots.txt"] = ("User-agent: *\nAllow: /\n\n" + "".join(f"Sitemap: {base}{s}\n" for s in sitemaps)).encode()
    return out
