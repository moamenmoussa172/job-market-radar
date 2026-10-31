"""More static pages built from the same daily export: company pages, the juniors corner and the
salary guide (English and Arabic). Rendering helpers are shared with seo_pages.

* /companies/<company>/ : open roles, countries, skills, pay and jobs for one company (3+ open jobs)
* /juniors/             : intern and junior jobs, where they are, what they ask for, who hires juniors
* /salaries/ and /salaries/<place>/ : median pay by role, only where enough jobs publish pay
"""
from __future__ import annotations

import datetime as dt
import statistics
from collections import Counter
from urllib.parse import quote

from jobradar.seo_pages import (REMOTE, T, _date, _e, _median_pay, _num, _shell, _top_skills, _unique, job_list,
                                place_name, slug)

MIN_COMPANY_JOBS = 3
COMPANIES_LISTED = 400
JUNIOR_LEVELS = ("Intern / Student", "Junior")
MIN_SALARY_JOBS = 5        # a role needs this many jobs with published pay in a place
MIN_SALARY_PLACE = 15      # a place needs this many jobs with published pay for its own page
JOBS_LISTED = 25
COMPANY_CAP = 300          # jobs on one company page
JUNIORS_CAP = 1000         # junior jobs on the juniors page (all of them, in practice)

E = {
    "en": {
        "c_h": "{c}: tech jobs", "c_title": "{c} tech jobs ({n} open) | Radarak",
        "c_desc": "{n} open tech jobs at {c}{where}, updated {d}.{sk} See roles, skills and pay. Free, no sign-up.",
        "c_where": " in {places}", "c_sub": "{n} open {jobs} · updated {d}",
        "c_places": "Hiring in", "c_roles": "Open roles", "c_cta": "See all {c} jobs in Radarak",
        "s_places": "countries", "s_visa": "offer visa / relocation",
        "c_idx_title": "Companies hiring tech talent | Radarak", "c_idx_h": "Companies hiring tech talent",
        "c_idx_sub": "{k} companies with 3 or more open tech jobs · updated {d}", "industry": "Industry",
        "j_title": "Junior & intern tech jobs ({n} open) | Radarak", "j_h": "Juniors corner: tech jobs for 0–2 years",
        "j_desc": "{n} open intern and junior tech jobs at {c} companies, updated {d}.{sk} Free, no sign-up.",
        "j_sub": "{n} intern and junior jobs at {c} companies · updated {d}",
        "j_intro": ("Starting out? These are the jobs that ask for little or no experience: internships, graduate "
                    "programmes and junior roles. The skills below are the ones junior jobs mention most, so they are "
                    "the best place to start learning."),
        "j_where": "Where juniors get hired", "j_roles": "Junior roles", "j_comp": "Companies hiring juniors",
        "j_cta": "Show junior jobs in Radarak",
        "sal_title": "Tech salaries{inp} by role (USD / year) | Radarak", "sal_h": "Tech salaries{inp}",
        "sal_desc": "Median yearly pay for tech roles{inp}, from {n} job posts that publish salary. Updated {d}.",
        "sal_sub": "From {n} jobs that publish pay · yearly, in US dollars · updated {d}",
        "sal_note": ("Only jobs that publish a salary count, and every salary is converted to a yearly amount in US "
                     "dollars. Many companies (especially in Egypt and the Gulf) don't publish pay, so treat these "
                     "numbers as a guide. A role is shown only when at least 5 jobs publish pay."),
        "sal_role": "Role", "sal_med": "Median", "sal_range": "Middle half", "sal_n": "Jobs",
        "sal_places": "Salaries by place", "sal_none": "Not enough jobs publish pay here yet.",
        "inp": " in {p}", "remote_inp": " for remote jobs", "all": "All places",
        "nav_companies": "Companies", "nav_juniors": "Juniors", "nav_salaries": "Salaries",
        "ci_search": "Search companies", "ci_count": "{n} of {t} companies", "ci_track": "Hiring for",
        "ci_remote": "Hires remote", "ci_visa": "Offers visa / relocation", "sort_most": "Most open jobs", "sort_az": "A–Z",
        "ci_empty": "No companies match these filters.", "ci_jobs": "{n} open jobs",
        "sal_search": "Search a role", "sal_track": "Track", "sal_place": "Place", "sal_count": "{n} of {t} roles",
        "sal_empty": "No roles match.",
        "est_h": "Typical monthly pay in Egypt & the Gulf", "est_h_place": "Typical monthly pay{inp}",
        "est_note": ("Salary estimates from Glassdoor, in local currency per month: total pay (base salary + bonus). "
                     "They are not from the jobs above. A row is shown only when at least 10 salaries stand behind it, "
                     "and old data shows its date, so you can judge it."),
        "est_med": "Median / month", "est_range": "Usual range", "est_n": "Salaries", "est_up": "Updated",
        "rate": "{r} / 5 on Glassdoor", "rate_n": "from {n} employee reviews",
    },
    "ar": {
        "c_h": "وظايف التك في {c}", "c_title": "وظايف التك في {c} ({n} متاحة) | رادارك",
        "c_desc": "{n} وظيفة تك متاحة في {c}{where}، آخر تحديث {d}.{sk} شوف الوظايف والمهارات والمرتبات. مجاني ومن غير تسجيل.",
        "c_where": " في {places}", "c_sub": "{n} {jobs} متاحة · آخر تحديث {d}",
        "c_places": "بتوظّف في", "c_roles": "الوظايف المتاحة", "c_cta": "شوف كل وظايف {c} في رادارك",
        "s_places": "دولة", "s_visa": "بتوفر فيزا / انتقال",
        "c_idx_title": "شركات بتوظف في التك | رادارك", "c_idx_h": "شركات بتوظف في التك",
        "c_idx_sub": "{k} شركة عندها 3 وظايف تك أو أكتر · آخر تحديث {d}", "industry": "المجال",
        "j_title": "وظايف تك للجونيور والتدريب ({n} متاحة) | رادارك", "j_h": "ركن الجونيور: وظايف تك من 0 لـ 2 سنة",
        "j_desc": "{n} وظيفة تدريب وجونيور في {c} شركة، آخر تحديث {d}.{sk} مجاني ومن غير تسجيل.",
        "j_sub": "{n} وظيفة تدريب وجونيور في {c} شركة · آخر تحديث {d}",
        "j_intro": ("لسه بادئ؟ دي الوظايف اللي مش طالبة خبرة أو طالبة خبرة قليلة: تدريب، برامج خريجين، ووظايف جونيور. "
                    "المهارات تحت هي الأكتر طلبًا في وظايف الجونيور، فهي أحسن حاجة تبدأ تتعلمها."),
        "j_where": "الجونيور بيتوظفوا فين", "j_roles": "وظايف الجونيور", "j_comp": "شركات بتوظف جونيور",
        "j_cta": "اعرض وظايف الجونيور في رادارك",
        "sal_title": "مرتبات التك{inp} حسب الوظيفة (دولار / سنة) | رادارك", "sal_h": "مرتبات التك{inp}",
        "sal_desc": "متوسط المرتب السنوي لوظايف التك{inp}، من {n} إعلان بيعلن المرتب. آخر تحديث {d}.",
        "sal_sub": "من {n} وظيفة بتعلن المرتب · سنوي بالدولار · آخر تحديث {d}",
        "sal_note": ("بنحسب بس الوظايف اللي بتعلن المرتب، وكل مرتب بيتحوّل لمبلغ سنوي بالدولار. شركات كتير (خصوصًا في مصر "
                     "والخليج) مش بتعلن المرتب، فاعتبر الأرقام دي مؤشر. الوظيفة بتظهر بس لو فيه 5 إعلانات على الأقل بمرتب."),
        "sal_role": "الوظيفة", "sal_med": "المتوسط", "sal_range": "النص اللي في النص", "sal_n": "وظايف",
        "sal_places": "المرتبات حسب المكان", "sal_none": "لسه مفيش وظايف كفاية بتعلن المرتب هنا.",
        "inp": " في {p}", "remote_inp": " للوظايف الريموت", "all": "كل الأماكن",
        "nav_companies": "الشركات", "nav_juniors": "الجونيور", "nav_salaries": "المرتبات",
        "ci_search": "دوّر على شركة", "ci_count": "{n} من {t} شركة", "ci_track": "بتوظف في",
        "ci_remote": "بتوظف ريموت", "ci_visa": "بتوفر فيزا / انتقال", "sort_most": "الأكتر وظايف", "sort_az": "أبجدي",
        "ci_empty": "مفيش شركات بالفلاتر دي.", "ci_jobs": "{n} وظيفة متاحة",
        "sal_search": "دوّر على وظيفة", "sal_track": "المجال", "sal_place": "المكان", "sal_count": "{n} من {t} وظيفة",
        "sal_empty": "مفيش وظايف بالبحث ده.",
        "est_h": "المرتب الشهري المعتاد في مصر والخليج", "est_h_place": "المرتب الشهري المعتاد{inp}",
        "est_note": ("تقديرات مرتبات من Glassdoor، بالعملة المحلية في الشهر: إجمالي المرتب (الأساسي + البونص). "
                     "مش من الوظايف اللي فوق. الصف بيظهر بس لو وراه 10 مرتبات على الأقل، والبيانات القديمة مكتوب "
                     "تاريخها عشان تحكم عليها بنفسك."),
        "est_med": "المتوسط / شهر", "est_range": "المدى المعتاد", "est_n": "مرتبات", "est_up": "آخر تحديث",
        "rate": "{r} من 5 على Glassdoor", "rate_n": "من {n} تقييم من الموظفين",
    },
}

CITY_AR = {"Cairo": "القاهرة", "Alexandria": "الإسكندرية", "Riyadh": "الرياض", "Jeddah": "جدة", "Dubai": "دبي",
           "Abu Dhabi": "أبوظبي", "Doha": "الدوحة", "Kuwait City": "مدينة الكويت", "Manama": "المنامة", "Muscat": "مسقط"}

CSS = """
.saltable{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--line);border-radius:var(--r-l);overflow:hidden;font-size:15px}
.saltable th,.saltable td{padding:12px 16px;text-align:start;border-bottom:1px solid var(--line)}
.saltable th{font-size:13px;color:var(--muted);font-weight:600;background:var(--paper)}
.saltable td.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.saltable td b{font:800 17px/1 var(--display)}
.saltable .bar{display:block;height:6px;border-radius:3px;background:var(--line);margin-top:6px;position:relative;min-width:120px}
.saltable .bar i{position:absolute;top:0;bottom:0;border-radius:3px;background:var(--mint)}
.note{font-size:14px;color:var(--muted);max-width:860px}
.estcity{margin:22px 0 8px;font:700 18px/1.2 var(--display)}
.estgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(340px,100%),1fr));gap:12px 20px}
.saltable td small{display:block;color:var(--muted);font-size:12px;margin-top:2px}
.rating{display:inline-flex;align-items:center;gap:8px;margin:4px 0 0;font-size:15px}
.rating b{font:800 18px/1 var(--display)}
.clist{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px}
.clist li{display:flex;align-items:center;justify-content:space-between;gap:10px;background:var(--surface);border:1px solid var(--line);border-radius:var(--r-m);padding:12px 14px}
.clist li a{display:flex;flex-direction:column;gap:2px;min-width:0;color:var(--ink);text-decoration:none}
.clist li a:hover b{color:var(--violet-ink);text-decoration:underline}
.clist li b{font-size:15px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.clist .m{font-size:13px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.clist .cnt{font:700 13px/1 var(--font);color:var(--violet-ink);background:var(--violet-soft);border-radius:99px;padding:6px 9px;white-space:nowrap}
.intro{font-size:16px;line-height:1.7;max-width:860px}
.seonav{display:flex;gap:4px 14px;flex-wrap:wrap;align-items:center}
.seonav a.navlink{color:var(--ink-2);text-decoration:none;font-weight:500;font-size:14px}
.seonav a.navlink:hover{color:var(--ink);text-decoration:none}
@media (max-width:600px){.seonav a.navlink{display:none}.saltable th,.saltable td{padding:10px}.saltable .bar{min-width:70px}}
"""


def _rel(path: str) -> str:
    return "../" * path.count("/")


def _alt(path: str, base: str) -> tuple[str, str]:
    en = path[3:] if path.startswith("ar/") else path
    url = en[: -len("index.html")]
    return base + url, base + "ar/" + url


def _page(lang: str, path: str, base: str, title: str, desc: str, body: str, crumbs: list[tuple[str, str | None]]) -> str:
    rel = _rel(path)
    url_en, url_ar = _alt(path, base)
    canonical = url_ar if lang == "ar" else url_en
    other = rel + (path[3:] if lang == "ar" else "ar/" + path)[: -len("index.html")]
    crumb_html = " › ".join(f'<a href="{_e(rel + h)}">{_e(x)}</a>' if h is not None else f"<span>{_e(x)}</span>"
                            for x, h in crumbs)
    jsonld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": x, "item": (base + h) if h is not None else canonical}
        for i, (x, h) in enumerate(crumbs)]}
    body = f'  <main class="seo">\n    <nav class="crumbs" aria-label="Breadcrumb">{crumb_html}</nav>\n{body}\n  </main>'
    return _shell(lang, rel, title, desc, canonical, url_en, url_ar, other, body, jsonld, base + "og.png")


def _stats(items: list[tuple[str, str]]) -> str:
    return '<div class="stats">' + "".join(f'<div class="stat"><b>{v}</b><span>{_e(l)}</span></div>' for v, l in items) + "</div>"


def _chips(items: list[tuple[str, str | None, int]]) -> str:
    return '<div class="links">' + "".join(
        (f'<a href="{_e(h)}">{_e(x)}<span>{_num(n)}</span></a>' if h else f'<a>{_e(x)}<span>{_num(n)}</span></a>')
        for x, h, n in items) + "</div>"


def _skills_panel(title: str, top: list[tuple[str, int]]) -> str:
    if not top:
        return ""
    mx = max(v for _, v in top) or 1
    rows = "".join(f'<li><span>{_e(s)}</span><span><i style="width:{max(3, round(100 * v / mx))}%"></i></span><b>{v}%</b></li>'
                   for s, v in top)
    return f'<div class="panel"><h2>{_e(title)}</h2><ol class="skb">{rows}</ol></div>'


def company_slugs(jobs: list[dict]) -> dict[str, str]:
    """Company name -> page slug, for companies with enough open jobs (unique slugs)."""
    counts = Counter(j.get("c") for j in _unique(jobs) if j.get("c"))
    out, used = {}, set()
    for name, n in counts.most_common(COMPANIES_LISTED):
        if n < MIN_COMPANY_JOBS:
            break
        s = slug(name) or "company"
        base_s, k = s, 2
        while s in used:
            s, k = f"{base_s}-{k}", k + 1
        used.add(s)
        out[name] = s
    return out


# ------------------------------------------------------------------------------------------ companies
def _company_page(name: str, cslug: str, jobs: list[dict], lang: str, meta: dict, base: str, today: dt.date,
                  place_pages: dict[str, str]) -> tuple[str, str]:
    t, x = T[lang], E[lang]
    path = ("ar/" if lang == "ar" else "") + f"companies/{cslug}/index.html"
    rel = _rel(path)
    uj = _unique(jobs)
    n = len(uj)
    places = Counter(c for j in uj for c in (j.get("co") or []))
    remote = sum(1 for j in uj if j.get("w") == "Remote")
    visa = sum(1 for j in uj if (j.get("f") or 0) & 1)
    pay = _median_pay(uj)
    top = _top_skills(uj, meta.get("skills", []), 8)
    d = _date(today, lang)
    names = [place_name(p, lang) for p, _ in places.most_common(3)]
    sep = "، " if lang == "ar" else ", "
    desc = x["c_desc"].format(n=_num(n), c=name, where=x["c_where"].format(places=sep.join(names)) if names else "", d=d,
                              sk=t["desc_sk"].format(skills=sep.join(s for s, _ in top[:3])) if top else "")
    stats = [(_num(n), t["s_open"])]
    if places:
        stats.append((_num(len(places)), x["s_places"]))
    if remote:
        stats.append((f"{round(100 * remote / n)}%", t["s_remote"]))
    if visa:
        stats.append((f"{round(100 * visa / n)}%", x["s_visa"]))
    if pay:
        stats.append((f"${pay}k", t["s_pay"]))
    industry = next((j.get("i") for j in uj if j.get("i") and j.get("i") != "Not identified"), None)
    place_chips = [(place_name(p, lang), (rel + place_pages[p]) if p in place_pages else None, k)
                   for p, k in places.most_common(12)]
    if remote:
        place_chips.append((t["remote"], (rel + place_pages[REMOTE]) if REMOTE in place_pages else None, remote))
    roles = Counter(j.get("r") for j in uj if j.get("r"))
    app = rel + "#q=" + quote(name)
    rate = (meta.get("_ratings") or {}).get(name)
    rate_html = (f'<p class="rating">⭐ <b>{_e(x["rate"].format(r=rate["rating"]))}</b>'
                 f'<a href="{_e(rate["link"])}" target="_blank" rel="noopener nofollow">{_e(x["rate_n"].format(n=_num(rate["reviews"])))}</a></p>'
                 if rate and rate.get("link") else "")
    body = f"""    <h1>{_e(x['c_h'].format(c=name))}</h1>
    <p class="lead">{_e(x['c_sub'].format(n=_num(n), jobs=t['job1'] if n == 1 else t['jobsN'], d=d))}{f' · {_e(x["industry"])}: {_e(industry)}' if industry else ''}</p>
    {rate_html}
    <div class="ctarow"><a class="primary" href="{_e(app)}">{_e(x['c_cta'].format(c=name))} →</a><span>{_e(t['cta_hint'])}</span></div>
    {_stats(stats)}
    <div class="cols">
      <section style="margin-top:0"><h2>{_e(t['list'])}</h2>
      {job_list(uj, rel, lang, today, meta.get('skills', []), cap=COMPANY_CAP, app=app, total=n)}</section>
      <aside class="side">
        {_skills_panel(t['skills'], top)}
        <div class="panel"><h2>{_e(x['c_roles'])}</h2>{_chips([(r, None, k) for r, k in roles.most_common(12)])}</div>
      </aside>
    </div>
    {f'<section><h2>{_e(x["c_places"])}</h2>{_chips(place_chips)}</section>' if place_chips else ''}"""
    crumbs = [(t["home"], ""), (E[lang]["nav_companies"], ("ar/" if lang == "ar" else "") + "companies/"), (name, None)]
    return path, _page(lang, path, base, x["c_title"].format(c=name, n=_num(n)), desc, body, crumbs)


def _companies_index(lang: str, slugs: dict[str, str], by_company: dict[str, list[dict]], base: str, today: dt.date) -> tuple[str, str]:
    t, x = T[lang], E[lang]
    path = ("ar/" if lang == "ar" else "") + "companies/index.html"
    rel = _rel(path)
    items = sorted(slugs.items(), key=lambda kv: (-len(_unique(by_company[kv[0]])), kv[0].lower()))
    all_places, all_tracks = Counter(), Counter()
    rows = []
    for name, s in items:
        uj = _unique(by_company[name])
        places = Counter(c for j in uj for c in (j.get("co") or []))
        tracks = Counter(j.get("tr") for j in uj if j.get("tr"))
        all_places.update(places.keys())
        all_tracks.update(tracks.keys())
        remote = any(j.get("w") == "Remote" for j in uj)
        visa = any((j.get("f") or 0) & 1 for j in uj)
        where = ", ".join(place_name(p, lang) for p, _ in places.most_common(3)) + (f" · {t['remote']}" if remote else "")
        rows.append(
            f'<li data-name="{_e(name.lower())}" data-t="{_e(name.lower())}" data-co="{_e("|".join(places))}" '
            f'data-tr="{_e("|".join(tracks))}" data-rem="{1 if remote else 0}" data-v="{1 if visa else 0}" data-n="{len(uj)}">'
            f'<a href="{_e(rel + ("ar/" if lang == "ar" else "") + f"companies/{s}/")}"><b>{_e(name)}</b>'
            f'<span class="m">{_e(where)}</span></a><span class="cnt">{_e(x["ci_jobs"].format(n=_num(len(uj))))}</span></li>')

    def select(f: str, label: str, options: list[tuple[str, str]]) -> str:
        opts = "".join(f'<option value="{_e(v)}">{_e(lbl)}</option>' for v, lbl in options)
        return (f'<label class="fsel"><span>{_e(label)}</span><select data-f="{f}" data-mode="has">'
                f'<option value="">{_e(t["f_any"])}</option>{opts}</select></label>')
    bar = (f'<label class="fsearch"><span class="sr">{_e(x["ci_search"])}</span><input type="search" data-f="t" data-mode="text" '
           f'placeholder="{_e(x["ci_search"])}" autocomplete="off"></label>'
           f'<button type="button" class="ftoggle" data-ftoggle aria-expanded="false">{_e(t["f_toggle"])}</button>'
           + select("co", t["f_place"], [(p, place_name(p, lang)) for p, _ in all_places.most_common(40)])
           + select("tr", x["ci_track"], [(tr, tr) for tr, _ in all_tracks.most_common()])
           + f'<label class="fchk"><input type="checkbox" data-f="rem" data-mode="flag"><span>{_e(x["ci_remote"])}</span></label>'
           + f'<label class="fchk"><input type="checkbox" data-f="v" data-mode="flag"><span>{_e(x["ci_visa"])}</span></label>'
           + f'<label class="fsel"><span>{_e(t["f_sort"])}</span><select data-sort><option value="n:num">{_e(x["sort_most"])}</option>'
             f'<option value="name:asc">{_e(x["sort_az"])}</option></select></label>')
    d = _date(today, lang)
    body = f"""    <h1>{_e(x['c_idx_h'])}</h1>
    <p class="lead">{_e(x['c_idx_sub'].format(k=_num(len(slugs)), d=d))}</p>
    <div class="fblock" data-filters data-page="60">
      <div class="fbar">{bar}</div>
      <div class="fmeta"><span data-count data-tpl="{_e(x['ci_count'])}">{_num(len(rows))}</span>
        <button type="button" class="linkbtn" data-clear hidden>{_e(t['f_clear'])}</button></div>
      <ol class="clist" data-list>{''.join(rows)}</ol>
      <p class="note fempty" data-empty hidden>{_e(x['ci_empty'])}</p>
      <button type="button" class="more fmore" data-more data-tpl="{_e(t['f_more'])}" hidden></button>
    </div>"""
    crumbs = [(t["home"], ""), (x["nav_companies"], None)]
    return path, _page(lang, path, base, x["c_idx_title"], x["c_idx_sub"].format(k=_num(len(slugs)), d=d), body, crumbs)


# ------------------------------------------------------------------------------------------ juniors
def _juniors_page(jobs: list[dict], lang: str, meta: dict, base: str, today: dt.date, slugs: dict[str, str],
                  place_pages: dict[str, str]) -> tuple[str, str]:
    t, x = T[lang], E[lang]
    path = ("ar/" if lang == "ar" else "") + "juniors/index.html"
    rel = _rel(path)
    uj = _unique([j for j in jobs if j.get("s") in JUNIOR_LEVELS])
    n = len(uj)
    comps = Counter(j.get("c") for j in uj if j.get("c"))
    places = Counter(c for j in uj for c in (j.get("co") or []))
    remote = sum(1 for j in uj if j.get("w") == "Remote")
    top = _top_skills(uj, meta.get("skills", []), 10)
    d = _date(today, lang)
    sep = "، " if lang == "ar" else ", "
    desc = x["j_desc"].format(n=_num(n), c=_num(len(comps)), d=d,
                              sk=t["desc_sk"].format(skills=sep.join(s for s, _ in top[:3])) if top else "")
    stats = [(_num(n), t["s_open"]), (_num(len(comps)), t["s_comp"])]
    if n and remote:
        stats.append((f"{round(100 * remote / n)}%", t["s_remote"]))
    place_chips = [(place_name(p, lang), rel + "#junior=1&country=" + quote(p), k) for p, k in places.most_common(14)]
    if remote:
        place_chips.append((t["remote"], rel + "#junior=1&remote=1", remote))
    comp_chips = [(c, (rel + ("ar/" if lang == "ar" else "") + f"companies/{slugs[c]}/") if c in slugs else None, k)
                  for c, k in comps.most_common(16)]
    roles = Counter(j.get("r") for j in uj if j.get("r"))
    body = f"""    <h1>{_e(x['j_h'])}</h1>
    <p class="lead">{_e(x['j_sub'].format(n=_num(n), c=_num(len(comps)), d=d))}</p>
    <div class="ctarow"><a class="primary" href="{rel}#junior=1">{_e(x['j_cta'])} →</a><span>{_e(t['cta_hint'])}</span></div>
    {_stats(stats)}
    <p class="intro">{_e(x['j_intro'])}</p>
    <div class="cols">
      <section style="margin-top:0"><h2>{_e(t['list'])}</h2>
      {job_list(uj, rel, lang, today, meta.get('skills', []), show_role=True, cap=JUNIORS_CAP, app=rel + "#junior=1", total=n)}</section>
      <aside class="side">{_skills_panel(t['skills'], top)}
        <div class="panel"><h2>{_e(x['j_roles'])}</h2>{_chips([(r, None, k) for r, k in roles.most_common(12)])}</div></aside>
    </div>
    <section><h2>{_e(x['j_where'])}</h2>{_chips(place_chips)}</section>
    <section><h2>{_e(x['j_comp'])}</h2>{_chips(comp_chips)}</section>"""
    crumbs = [(t["home"], ""), (x["nav_juniors"], None)]
    return path, _page(lang, path, base, x["j_title"].format(n=_num(n)), desc, body, crumbs)


# ------------------------------------------------------------------------------------------ salaries
def estimates_block(estimates: list[dict], lang: str, place: str | None = None) -> str:
    """Glassdoor estimates (meta["pay_est"]) per city: role, monthly median and range, local currency."""
    x = E[lang]
    rows = [e for e in estimates or [] if place is None or e.get("co") == place]
    if not rows:
        return ""
    cities: dict[str, list[dict]] = {}
    for e in rows:
        cities.setdefault(e["city"], []).append(e)
    tables = []
    for city, es in sorted(cities.items(), key=lambda kv: -sum(e["n"] for e in kv[1])):
        es = sorted(es, key=lambda e: -e["md"])
        label = CITY_AR.get(city, city) if lang == "ar" else city
        body = "".join(
            f'<tr><td>{_e(e["q"])}<small>{_e(x["est_up"])}: {_e(e.get("up") or "")}</small></td>'
            f'<td class="num"><b>{_num(e["md"])}</b> {_e(e["cur"])}</td>'
            f'<td class="num">{_num(e["lo"])} – {_num(e["hi"])}</td><td class="num">{_num(e["n"])}</td></tr>' for e in es)
        tables.append(f'<div><h3 class="estcity">{_e(label)}</h3><table class="saltable"><thead><tr><th>{_e(x["sal_role"])}</th>'
                      f'<th>{_e(x["est_med"])}</th><th>{_e(x["est_range"])}</th><th>{_e(x["est_n"])}</th></tr></thead>'
                      f'<tbody>{body}</tbody></table></div>')
    inp = x["inp"].format(p=place_name(place, lang)) if place else ""
    head = x["est_h_place"].format(inp=inp) if place else x["est_h"]
    return (f'<section id="typical"><h2>{_e(head)}</h2><p class="note">{_e(x["est_note"])}</p>'
            f'<div class="estgrid">{"".join(tables)}</div></section>')


def _role_tracks(jobs: list[dict]) -> dict[str, str]:
    return {j.get("r"): j.get("tr") for j in jobs if j.get("r") and j.get("tr")}


def _pay_rows(jobs: list[dict]) -> list[tuple[str, int, int, int, int]]:
    """(role, median, p25, p75, jobs) for roles with enough published salaries, highest median first."""
    by_role: dict[str, list[float]] = {}
    for j in _unique([j for j in jobs if j.get("$")]):
        by_role.setdefault(j.get("r"), []).append((j["$"][0] + j["$"][1]) / 2)
    rows = []
    for role, vals in by_role.items():
        if role and role != "Other tech role" and len(vals) >= MIN_SALARY_JOBS:
            q = statistics.quantiles(vals, n=4) if len(vals) >= 2 else [vals[0]] * 3
            rows.append((role, round(statistics.median(vals)), round(q[0]), round(q[2]), len(vals)))
    return sorted(rows, key=lambda r: -r[1])


def _salary_page(place: str | None, jobs: list[dict], lang: str, base: str, today: dt.date,
                 others: list[tuple[str, str, int]], all_places: list[tuple[str, str]] | None = None,
                 role_track: dict[str, str] | None = None, estimates: list[dict] | None = None) -> tuple[str, str] | None:
    t, x = T[lang], E[lang]
    sub = "" if place is None else ("remote" if place == REMOTE else slug(place)) + "/"
    path = ("ar/" if lang == "ar" else "") + "salaries/" + sub + "index.html"
    rel = _rel(path)
    rows = _pay_rows(jobs)
    paid = len(_unique([j for j in jobs if j.get("$")]))
    inp = "" if place is None else x["remote_inp"] if place == REMOTE else x["inp"].format(p=place_name(place, lang))
    d = _date(today, lang)
    mx = max([r[3] for r in rows] or [1])
    table = ("<table class=\"saltable\"><thead><tr>"
             f"<th>{_e(x['sal_role'])}</th><th>{_e(x['sal_med'])}</th><th>{_e(x['sal_range'])}</th><th>{_e(x['sal_n'])}</th>"
             "</tr></thead><tbody>"
             + "".join(f'<tr data-t="{_e(r.lower())}" data-tr="{_e((role_track or {}).get(r, ""))}" data-m="{m}" data-name="{_e(r.lower())}">'
                       f'<td>{_e(r)}</td><td class="num"><b>${m}k</b></td><td class="num">${lo}k – ${hi}k'
                       f'<span class="bar"><i style="inset-inline-start:{round(100 * lo / mx)}%;width:{max(2, round(100 * (hi - lo) / mx))}%"></i></span></td>'
                       f'<td class="num">{k}</td></tr>' for r, m, lo, hi, k in rows)
             + "</tbody></table>") if rows else f'<p class="note">{_e(x["sal_none"])}</p>'
    place_links = _chips([(lbl, rel + ("ar/" if lang == "ar" else "") + href, k) for lbl, href, k in others]) if others else ""
    pre = rel + ("ar/" if lang == "ar" else "")
    here = "salaries/" + sub
    switch = ""
    if all_places and len(all_places) > 1:
        opts = "".join(f'<option value="{_e(pre + href)}"{" selected" if href == here else ""}>{_e(lbl)}</option>'
                       for href, lbl in all_places)
        switch = f'<label class="fsel"><span>{_e(x["sal_place"])}</span><select data-goto>{opts}</select></label>'
    tracks = sorted({tr for tr in (role_track or {}).values() if tr and any((role_track or {}).get(r[0]) == tr for r in rows)})
    track_sel = (f'<label class="fsel"><span>{_e(x["sal_track"])}</span><select data-f="tr"><option value="">{_e(t["f_any"])}</option>'
                 + "".join(f'<option value="{_e(tr)}">{_e(tr)}</option>' for tr in tracks) + "</select></label>") if len(tracks) > 1 else ""
    if rows:
        table = f"""<div class="fblock" data-filters>
      <div class="fbar">{switch}<label class="fsearch"><span class="sr">{_e(x["sal_search"])}</span><input type="search" data-f="t"
        data-mode="text" placeholder="{_e(x["sal_search"])}" autocomplete="off"></label>{track_sel}
        <label class="fsel"><span>{_e(t["f_sort"])}</span><select data-sort><option value="m:num">{_e(x["sal_med"])}</option>
        <option value="name:asc">{_e(x["sort_az"])}</option></select></label></div>
      <div class="fmeta"><span data-count data-tpl="{_e(x['sal_count'])}">{len(rows)}</span>
        <button type="button" class="linkbtn" data-clear hidden>{_e(t['f_clear'])}</button></div>
      {table.replace("<tbody>", "<tbody data-list>", 1)}
      <p class="note fempty" data-empty hidden>{_e(x['sal_empty'])}</p></div>"""
    elif switch:
        table = f'<div class="fbar">{switch}</div>' + table
    body = f"""    <h1>{_e(x['sal_h'].format(inp=inp))}</h1>
    <p class="lead">{_e(x['sal_sub'].format(n=_num(paid), d=d))}</p>
    {table}
    <p class="note">{_e(x['sal_note'])}</p>
    {estimates_block(estimates or [], lang, None if place in (None, REMOTE) else place) if place != REMOTE else ""}
    {f'<section><h2>{_e(x["sal_places"])}</h2>{place_links}</section>' if place_links else ''}"""
    crumbs = [(t["home"], ""), (x["nav_salaries"], None if place is None else ("ar/" if lang == "ar" else "") + "salaries/")]
    if place is not None:
        crumbs.append((place_name(place, lang), None))
    return path, _page(lang, path, base, x["sal_title"].format(inp=inp), x["sal_desc"].format(inp=inp, n=_num(paid), d=d),
                       body, crumbs)


# ------------------------------------------------------------------------------------------ all of it
def extra_files(jobs: list[dict], meta: dict, base: str, today: dt.date,
                place_pages: dict[str, str]) -> tuple[dict[str, bytes], list[tuple[str, str]]]:
    """Pages + their sitemap entries. place_pages: place -> 'jobs/<place>/' (pages that exist)."""
    out: dict[str, bytes] = {"extra.css": CSS.strip().encode()}
    urls: list[tuple[str, str]] = []
    slugs = company_slugs(jobs)
    by_company: dict[str, list[dict]] = {}
    for j in jobs:
        if j.get("c") in slugs:
            by_company.setdefault(j["c"], []).append(j)
    paid_by_place: Counter = Counter()
    for j in _unique([j for j in jobs if j.get("$")]):
        for c in (j.get("co") or []):
            paid_by_place[c] += 1
        if j.get("w") == "Remote":
            paid_by_place[REMOTE] += 1
    sal_places = [p for p, k in paid_by_place.most_common() if k >= MIN_SALARY_PLACE]

    for lang in ("en", "ar"):
        for name, s in slugs.items():
            path, html = _company_page(name, s, by_company[name], lang, meta, base, today, place_pages)
            out[path] = html.encode()
        path, html = _companies_index(lang, slugs, by_company, base, today)
        out[path] = html.encode()
        path, html = _juniors_page(jobs, lang, meta, base, today, slugs, place_pages)
        out[path] = html.encode()
        others = [(place_name(p, lang) if p != REMOTE else T[lang]["remote"],
                   "salaries/" + ("remote" if p == REMOTE else slug(p)) + "/", paid_by_place[p]) for p in sal_places]
        all_places = [("salaries/", E[lang]["all"])] + [(href, lbl) for lbl, href, _ in others]
        role_track = _role_tracks(jobs)
        path, html = _salary_page(None, jobs, lang, base, today, others, all_places, role_track, meta.get("pay_est"))
        out[path] = html.encode()
        for p in sal_places:
            pj = [j for j in jobs if (j.get("w") == "Remote" if p == REMOTE else p in (j.get("co") or []))]
            path, html = _salary_page(p, pj, lang, base, today, [o for o in others if not o[1].endswith(
                ("remote" if p == REMOTE else slug(p)) + "/")], all_places, role_track, meta.get("pay_est"))
            out[path] = html.encode()
    for path in out:
        if path.endswith("index.html") and not path.startswith("ar/"):
            url = path[: -len("index.html")]
            prio = "0.7" if url.count("/") <= 1 else "0.5"
            urls += [(base + url, prio), (base + "ar/" + url, prio)]
    return out, urls
