/* Job Radar - static site. Data: data/meta.json + data/jobs.json (refreshed daily by the pipeline). */
(() => {
  "use strict";

  const PAGE = 40;
  const MATCH = 0.6;           // a job is a match with >= 60% of its listed skills
  const FLAG = { visa: 1, nationals: 2, arabic: 4 };

  // ------------------------------------------------------------------ text
  const T = {
    en: {
      brand: "Job Radar", code: "Source code", filters: "Filters", filtersOn: (n) => `Filters (${n} on)`, ask1: "I live in", ask2: "and I'm looking for", ask3: "jobs.",
      country: "Country", role: "Role", countLabel: "jobs you can apply to", countAll: "tech jobs",
      anyCountry: "any country", anyRole: "any tech", search: "Search", searchPh: "Search a title, company or skill",
      seniority: "Seniority", workMode: "Work mode", industry: "Industry", skill: "Must-have skill",
      arabic: "Arabic", any: "Any", arabicReq: "Required", arabicNot: "Not required",
      visa: "Visa or relocation offered", hideNationals: "Hide jobs limited to nationals", reset: "Clear filters",
      tabJobs: "Jobs", tabInsights: "What to learn & pay", tabAbout: "How it works",
      topSkills: "Skills these jobs ask for", topSkillsHint: "Share of jobs that mention each skill. Tap one to only see jobs that need it.",
      nextSkill: "The next skill to learn", nextSkillHint: "Add the skills you have. A job is a match when you have 60% or more of the skills it lists.",
      addSkill: "Add a skill you have", salaryByRole: "Pay by role", salaryHint: "Median yearly salary in US dollars, from jobs that publish pay.",
      whereJobs: "Where the jobs are", whereHint: "Office and hybrid jobs by country, plus remote jobs.",
      companies: "Companies hiring the most", roles: "Most wanted roles",
      remote: "Remote", remoteWorld: "Remote, worldwide", visaTag: "Visa / relocation", natTag: "Nationals only", arTag: "Arabic required",
      today: "today", yesterday: "yesterday", daysAgo: (n) => `${n} days ago`, updated: (d) => `Updated ${d}`,
      more: (n) => `Show ${n} more`, emptyJobs: "No jobs match these filters. Try another role, or clear a filter.",
      statJobs: "jobs", statRemote: "remote", statCompanies: "companies", statPay: "median pay (USD / year)",
      statPayNone: "no published pay yet",
      matchLine: (m, n) => `You match ${m} of ${n} jobs.`, addSkillsFirst: "Add your skills to see what to learn next.",
      noNext: "You already match most of these jobs, or they list too few skills.", extraJobs: "more jobs",
      tooFew: "Not enough data for these filters yet.", worldwide: "Worldwide",
      removeSkill: (s) => `Remove ${s}`, by: "", allOf: (x) => `${x} (all roles)`, listedOf: (a, b) => `${a} jobs listed here, out of ${b} tracked.`,
    },
    ar: {
      brand: "رادار الوظائف", code: "الكود المصدري", filters: "الفلاتر", filtersOn: (n) => `الفلاتر (${n} شغالين)`, ask1: "أنا عايش في", ask2: "وبدوّر على وظايف", ask3: "",
      country: "الدولة", role: "الوظيفة", countLabel: "وظيفة تقدر تقدّم عليها", countAll: "وظيفة تقنية",
      anyCountry: "أي دولة", anyRole: "أي مجال تقني", search: "بحث", searchPh: "ابحث باسم وظيفة أو شركة أو مهارة",
      seniority: "المستوى", workMode: "نوع العمل", industry: "المجال", skill: "مهارة لازم تكون مطلوبة",
      arabic: "العربي", any: "الكل", arabicReq: "مطلوب", arabicNot: "مش مطلوب",
      visa: "فيها فيزا أو انتقال", hideNationals: "اخفي الوظايف اللي للمواطنين بس", reset: "امسح الفلاتر",
      tabJobs: "الوظايف", tabInsights: "تتعلم إيه والمرتبات", tabAbout: "إزاي بيشتغل",
      topSkills: "المهارات المطلوبة في الوظايف دي", topSkillsHint: "نسبة الوظايف اللي بتطلب كل مهارة. اضغط على مهارة عشان تشوف وظايفها بس.",
      nextSkill: "المهارة الجاية اللي تتعلمها", nextSkillHint: "ضيف المهارات اللي عندك. الوظيفة بتناسبك لو عندك 60% أو أكتر من مهاراتها.",
      addSkill: "ضيف مهارة عندك", salaryByRole: "المرتبات حسب الوظيفة", salaryHint: "متوسط المرتب السنوي بالدولار، من الوظايف اللي بتعلن المرتب.",
      whereJobs: "الوظايف فين", whereHint: "وظايف المكتب والهايبرد حسب الدولة، بالإضافة للريموت.",
      companies: "أكتر شركات بتوظف", roles: "أكتر وظايف مطلوبة",
      remote: "ريموت", remoteWorld: "ريموت من أي مكان", visaTag: "فيزا / انتقال", natTag: "للمواطنين بس", arTag: "العربي مطلوب",
      today: "النهارده", yesterday: "امبارح", daysAgo: (n) => `من ${n} يوم`, updated: (d) => `آخر تحديث ${d}`,
      more: (n) => `اعرض ${n} كمان`, emptyJobs: "مفيش وظايف بالفلاتر دي. جرّب وظيفة تانية أو امسح فلتر.",
      statJobs: "وظيفة", statRemote: "ريموت", statCompanies: "شركة", statPay: "متوسط المرتب (دولار / سنة)",
      statPayNone: "مفيش مرتبات معلنة لسه",
      matchLine: (m, n) => `إنت مناسب لـ ${m} من ${n} وظيفة.`, addSkillsFirst: "ضيف مهاراتك عشان تعرف تتعلم إيه بعد كده.",
      noNext: "إنت مناسب لأغلب الوظايف دي، أو مهاراتها المكتوبة قليلة.", extraJobs: "وظيفة زيادة",
      tooFew: "مفيش بيانات كفاية للفلاتر دي لسه.", worldwide: "من أي مكان",
      removeSkill: (s) => `شيل ${s}`, by: "", allOf: (x) => `${x} (كل الوظايف)`, listedOf: (a, b) => `${a} وظيفة معروضة هنا، من ${b} بنتابعهم.`,
    },
  };
  const ABOUT = {
    en: `
      <h2>What this is</h2>
      <p>Job Radar collects tech job postings every day from company career pages and job APIs, and shows the ones you can actually apply to from where you live: local office and hybrid jobs, plus remote jobs that are open to your country or region.</p>
      <h2>How "jobs you can apply to" works</h2>
      <p>Many remote jobs are only open to people in certain countries. Each posting's location and eligibility text is mapped to countries and regions, so picking your country hides remote jobs you aren't allowed to take.</p>
      <h2>Tags on each job</h2>
      <ul>
        <li><b>Visa / relocation</b>: the posting says the employer sponsors visas or helps you relocate.</li>
        <li><b>Nationals only</b>: limited to citizens, for example "Saudi nationals only" or Emiratisation roles.</li>
        <li><b>Arabic required</b>: Arabic is listed as a required language.</li>
      </ul>
      <h2>Salaries</h2>
      <p>Only jobs that publish pay are counted. Salaries in any currency and period are turned into a yearly amount in US dollars.</p>
      <h2>Sources</h2>
      <p>Company career boards (Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Recruitee, Personio) and job APIs. Every job links to its original posting; apply there. Jobs from some sources are credited on each listing (for example, Jobs by Adzuna).</p>
      <p>The data is collected automatically and may miss jobs or contain mistakes. The project is open source.</p>`,
    ar: `
      <h2>ده إيه</h2>
      <p>رادار الوظائف بيجمع وظايف التك كل يوم من صفحات التوظيف بتاعة الشركات ومن مواقع الوظايف، ويوريك اللي تقدر تقدّم عليها فعلًا من البلد اللي إنت فيها: وظايف المكتب والهايبرد في بلدك، والوظايف الريموت المفتوحة لبلدك أو منطقتك.</p>
      <h2>"وظايف تقدر تقدّم عليها" معناها إيه</h2>
      <p>وظايف ريموت كتير مفتوحة لناس في دول معينة بس. بنقرا مكان كل وظيفة وشروطها ونربطها بالدول والمناطق، فلما تختار بلدك بنخفي الوظايف اللي مش مسموح لك تقدّم عليها.</p>
      <h2>العلامات على كل وظيفة</h2>
      <ul>
        <li><b>فيزا / انتقال</b>: الشركة بتقول إنها بتعمل فيزا أو بتساعد في الانتقال.</li>
        <li><b>للمواطنين بس</b>: الوظيفة لمواطني البلد بس، زي "للسعوديين فقط".</li>
        <li><b>العربي مطلوب</b>: اللغة العربية مطلوبة في الوظيفة.</li>
      </ul>
      <h2>المرتبات</h2>
      <p>بنحسب بس الوظايف اللي بتعلن المرتب، وبنحوّل أي مرتب بأي عملة لمبلغ سنوي بالدولار.</p>
      <h2>المصادر</h2>
      <p>صفحات التوظيف بتاعة الشركات (Greenhouse و Lever و Ashby و SmartRecruiters و Workable و Recruitee و Personio) ومواقع وظايف. كل وظيفة فيها لينك للإعلان الأصلي، والتقديم بيكون هناك.</p>
      <p>البيانات بتتجمع أوتوماتيك وممكن يفوتها وظايف أو يكون فيها أخطاء. المشروع مفتوح المصدر.</p>`,
  };

  // ------------------------------------------------------------------ state
  const $ = (id) => document.getElementById(id);
  const store = {
    get(k, d) { try { const v = localStorage.getItem("jr_" + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem("jr_" + k, JSON.stringify(v)); } catch { /* storage unavailable */ } },
  };
  let lang = store.get("lang", (navigator.language || "").startsWith("ar") ? "ar" : "en");
  let meta = null, jobs = [], regionOf = {}, shown = PAGE, current = [];
  let mySkills = new Set(store.get("mySkills", []));
  const t = (k) => T[lang][k] ?? T.en[k] ?? k;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (n) => Number(n).toLocaleString("en-US");

  // ------------------------------------------------------------------ setup
  function fillSelect(el, options, anyLabel) {
    const prev = el.value;
    el.innerHTML = "";
    if (anyLabel !== null) el.add(new Option(anyLabel, ""));
    for (const o of options) {
      if (o.group) {
        const g = document.createElement("optgroup");
        g.label = o.group;
        o.items.forEach((it) => g.appendChild(new Option(it.label, it.value)));
        el.appendChild(g);
      } else {
        el.add(new Option(o.label ?? o, o.value ?? o));
      }
    }
    el.value = prev;
    if (el.value !== prev) el.value = "";
  }

  function buildOptions() {
    fillSelect($("country"), meta.countries.map((c) => c.name), t("anyCountry"));
    fillSelect($("role"), meta.tracks.map((tr) => ({
      group: tr.name,
      items: [{ label: t("allOf")(tr.name), value: "track:" + tr.name },
              ...tr.roles.map((r) => ({ label: r, value: "role:" + r }))],
    })), t("anyRole"));
    fillSelect($("seniority"), meta.seniorities, t("any"));
    fillSelect($("workMode"), meta.work_modes, t("any"));
    fillSelect($("industry"), meta.industries, t("any"));
    fillSelect($("skill"), meta.skills, t("any"));
    fillSelect($("arabic"), [{ label: t("arabicReq"), value: "req" }, { label: t("arabicNot"), value: "not" }], t("any"));
    const dl = $("skillList");
    dl.innerHTML = meta.skills.map((s) => `<option value="${esc(s)}">`).join("");
  }

  // Hero dropdowns are as wide as the chosen text, so the sentence reads naturally.
  const measurer = document.createElement("canvas").getContext("2d");
  function autosize(sel) {
    const cs = getComputedStyle(sel);
    measurer.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const text = sel.selectedOptions[0] ? sel.selectedOptions[0].text : "";
    sel.style.width = Math.ceil(measurer.measureText(text).width + 10) + "px";
  }
  function sizeHero() { autosize($("country")); autosize($("role")); $("ask3").hidden = !t("ask3"); }

  function applyLanguage() {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
    const btn = $("lang");
    btn.textContent = lang === "ar" ? "English" : "العربية";
    btn.lang = lang === "ar" ? "en" : "ar";
    $("aboutText").innerHTML = ABOUT[lang];
    if (meta) {
      buildOptions();
      const d = new Date(meta.generated_at);
      $("fresh").textContent = t("updated")(d.toLocaleDateString(lang === "ar" ? "ar-EG" : "en-GB", { day: "numeric", month: "long" }));
      $("footText").textContent = t("listedOf")(num(meta.listed_jobs), num(meta.total_active_jobs)) + " " + meta.credits.join(", ") + ".";
    }
  }

  // ------------------------------------------------------------------ filters <-> URL (shareable links)
  const FIELDS = ["country", "role", "seniority", "workMode", "industry", "skill", "arabic", "q"];
  const CHECKS = ["visa", "hideNationals"];
  function readHash() {
    const h = new URLSearchParams(location.hash.slice(1));
    FIELDS.forEach((f) => { if (h.has(f)) $(f).value = h.get(f); });
    CHECKS.forEach((f) => { if (h.has(f)) $(f).checked = h.get(f) === "1"; });
    if (h.has("tab")) selectTab(h.get("tab"), false);
  }
  function writeHash() {
    const h = new URLSearchParams();
    FIELDS.forEach((f) => { if ($(f).value) h.set(f, $(f).value); });
    if ($("visa").checked) h.set("visa", "1");
    if (!$("hideNationals").checked) h.set("hideNationals", "0");
    const tab = document.querySelector('[role="tab"][aria-selected="true"]').getAttribute("aria-controls");
    if (tab !== "jobs") h.set("tab", tab);
    history.replaceState(null, "", h.toString() ? "#" + h.toString() : location.pathname);
  }

  function canApplyFrom(job, country) {
    if (!country) return true;
    if (job.co.includes(country)) return true;
    return job.w === "Remote" && (job.ww === 1 || job.rg.includes(regionOf[country]) || job.rg.includes("Worldwide"));
  }

  function filtered() {
    const country = $("country").value, role = $("role").value, sen = $("seniority").value, wm = $("workMode").value;
    const ind = $("industry").value, skill = $("skill").value, ar = $("arabic").value;
    const visa = $("visa").checked, hideNat = $("hideNationals").checked;
    const q = $("q").value.trim().toLowerCase();
    const skillIdx = skill ? meta.skills.indexOf(skill) : -1;
    return jobs.filter((j) => {
      if (role.startsWith("track:") && j.tr !== role.slice(6)) return false;
      if (role.startsWith("role:") && j.r !== role.slice(5)) return false;
      if (sen && j.s !== sen) return false;
      if (wm && j.w !== wm) return false;
      if (ind && j.i !== ind) return false;
      if (skillIdx >= 0 && !j.k.includes(skillIdx)) return false;
      const f = j.f || 0;
      if (visa && !(f & FLAG.visa)) return false;
      if (hideNat && (f & FLAG.nationals)) return false;
      if (ar === "req" && !(f & FLAG.arabic)) return false;
      if (ar === "not" && (f & FLAG.arabic)) return false;
      if (q && !j._text.includes(q)) return false;
      return canApplyFrom(j, country);
    });
  }

  // ------------------------------------------------------------------ jobs tab
  function ago(iso) {
    const days = Math.max(0, Math.round((Date.now() - new Date(iso + "T12:00:00Z")) / 864e5));
    return days === 0 ? t("today") : days === 1 ? t("yesterday") : t("daysAgo")(days);
  }
  function pay(j) { return j.$ ? (j.$[0] === j.$[1] ? `$${j.$[0]}k` : `$${j.$[0]}k – $${j.$[1]}k`) : ""; }

  function renderJobs() {
    const list = $("jobList");
    const slice = current.slice(0, shown);
    list.innerHTML = slice.map((j) => {
      const f = j.f || 0;
      const tags = [
        j.w === "Remote" ? `<span class="tag">${j.ww ? t("remoteWorld") : t("remote")}</span>` : `<span class="tag plain">${esc(j.w)}</span>`,
        f & FLAG.visa ? `<span class="tag visa">${t("visaTag")}</span>` : "",
        f & FLAG.nationals ? `<span class="tag nat">${t("natTag")}</span>` : "",
        f & FLAG.arabic ? `<span class="tag ar">${t("arTag")}</span>` : "",
        `<span class="tag plain">${esc(j.r)}</span>`,
        j.s && j.s !== "Not stated" ? `<span class="tag plain">${esc(j.s)}</span>` : "",
        j.by ? `<span class="tag plain">${esc(j.by)}</span>` : "",
      ].join("");
      return `<li class="job">
        <div>
          <h3><a href="${esc(j.u)}" target="_blank" rel="noopener nofollow">${esc(j.t)}</a></h3>
          <p class="where"><b>${esc(j.c || "")}</b> ${j.l ? "<span>" + esc(j.l) + "</span>" : ""}</p>
        </div>
        <div class="side"><span class="pay">${pay(j)}</span>${ago(j.p)}</div>
        <div class="tags">${tags}</div>
      </li>`;
    }).join("");
    $("empty").hidden = current.length > 0;
    $("empty").textContent = t("emptyJobs");
    const left = current.length - shown;
    $("more").hidden = left <= 0;
    $("more").textContent = t("more")(Math.min(PAGE, left));
  }

  // ------------------------------------------------------------------ insights tab
  function bars(el, rows, opts = {}) {
    if (!rows.length) { el.innerHTML = `<p class="none">${t("tooFew")}</p>`; return; }
    const max = Math.max(...rows.map((r) => r.v));
    el.innerHTML = rows.map((r) => {
      const tag = opts.click ? "button" : "div";
      const attrs = opts.click ? ` type="button" data-value="${esc(r.key ?? r.name)}"` : "";
      return `<${tag} class="bar"${attrs}><span class="name" title="${esc(r.name)}">${esc(r.name)}</span>
        <span class="track"><span class="fill" style="width:${Math.max(2, (100 * r.v) / max)}%"></span></span>
        <span class="val">${opts.fmt ? opts.fmt(r.v) : num(r.v)}</span></${tag}>`;
    }).join("");
    if (opts.click) el.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => opts.click(b.dataset.value)));
  }
  const countBy = (arr, keyFn) => {
    const m = new Map();
    arr.forEach((x) => { const k = keyFn(x); if (k != null && k !== "") m.set(k, (m.get(k) || 0) + 1); });
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  };
  const median = (xs) => { const s = [...xs].sort((a, b) => a - b); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

  function renderInsights() {
    const js = current, n = js.length;
    const paid = js.filter((j) => j.$).map((j) => (j.$[0] + j.$[1]) / 2);
    const remote = js.filter((j) => j.w === "Remote").length;
    const companies = new Set(js.map((j) => (j.c || "").toLowerCase()).filter(Boolean)).size;
    $("stats").innerHTML = [
      [num(n), t("statJobs")],
      [n ? Math.round((100 * remote) / n) + "%" : "–", t("statRemote")],
      [num(companies), t("statCompanies")],
      [paid.length >= 3 ? "$" + Math.round(median(paid)) + "k" : "–", paid.length >= 3 ? t("statPay") : t("statPayNone")],
    ].map(([v, l]) => `<div class="stat"><b>${v}</b><span>${esc(l)}</span></div>`).join("");

    const chosen = $("skill").value;
    const skillCounts = countBy(js.flatMap((j) => j.k), (k) => k)
      .filter(([k]) => meta.skills[k] !== chosen).slice(0, 12)
      .map(([k, c]) => ({ name: meta.skills[k], v: Math.round((100 * c) / n) }));
    bars($("skillBars"), n ? skillCounts : [], { fmt: (v) => v + "%", click: (s) => { $("skill").value = s; update(); } });

    // next skill to learn
    const mine = new Set([...mySkills].map((s) => meta.skills.indexOf(s)).filter((i) => i >= 0));
    $("mySkills").innerHTML = [...mySkills].map((s) =>
      `<button type="button" class="chip" data-skill="${esc(s)}" aria-label="${esc(t("removeSkill")(s))}">${esc(s)} ✕</button>`).join("");
    $("mySkills").querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => {
      mySkills.delete(b.dataset.skill); store.set("mySkills", [...mySkills]); renderInsights();
    }));
    const withSkills = js.filter((j) => j.k.length);
    if (!mine.size) {
      $("matchLine").textContent = t("addSkillsFirst");
      $("nextBars").innerHTML = "";
    } else {
      let matched = 0;
      const gain = new Map();
      withSkills.forEach((j) => {
        const known = j.k.filter((k) => mine.has(k)).length, total = j.k.length;
        if (known / total >= MATCH) { matched++; return; }
        if ((known + 1) / total >= MATCH) j.k.forEach((k) => { if (!mine.has(k)) gain.set(k, (gain.get(k) || 0) + 1); });
      });
      $("matchLine").textContent = t("matchLine")(num(matched), num(withSkills.length));
      const rows = [...gain.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8).map(([k, v]) => ({ name: meta.skills[k], v }));
      if (rows.length) bars($("nextBars"), rows, { fmt: (v) => "+" + num(v) });
      else $("nextBars").innerHTML = `<p class="none">${t("noNext")}</p>`;
    }

    // pay by role
    const byRole = new Map();
    js.filter((j) => j.$).forEach((j) => { const a = byRole.get(j.r) || []; a.push((j.$[0] + j.$[1]) / 2); byRole.set(j.r, a); });
    bars($("salaryBars"), [...byRole.entries()].filter(([, v]) => v.length >= 3)
      .map(([r, v]) => ({ name: r, v: Math.round(median(v)) })).sort((a, b) => b.v - a.v).slice(0, 10),
      { fmt: (v) => "$" + v + "k", click: (r) => { $("role").value = "role:" + r; update(); } });

    // where
    const places = countBy(js.filter((j) => j.w !== "Remote"), (j) => j.co[0]).slice(0, 8).map(([k, v]) => ({ name: k, v }));
    const rem = js.filter((j) => j.w === "Remote").length;
    if (rem) places.push({ name: t("remote"), v: rem });
    bars($("placeBars"), places.sort((a, b) => b.v - a.v));

    $("companyList").innerHTML = countBy(js, (j) => j.c).slice(0, 10)
      .map(([c, v]) => `<li>${esc(c)} <span>(${num(v)})</span></li>`).join("") || `<p class="none">${t("tooFew")}</p>`;
    bars($("roleBars"), countBy(js, (j) => j.r).slice(0, 10).map(([k, v]) => ({ name: k, v })),
      { click: (r) => { $("role").value = "role:" + r; update(); } });
  }

  // ------------------------------------------------------------------ wiring
  function update(keepPage) {
    current = filtered();
    sizeHero();
    const on = ["seniority", "workMode", "industry", "skill", "arabic", "q"].filter((f) => $(f).value).length + ($("visa").checked ? 1 : 0);
    $("filterSummary").textContent = on ? t("filtersOn")(on) : t("filters");
    if (!keepPage) shown = PAGE;
    const country = $("country").value;
    $("count").textContent = num(current.length);
    $("countLabel").textContent = country ? t("countLabel") : t("countAll");
    renderJobs();
    if (!$("insights").hidden) renderInsights();
    writeHash();
  }

  function selectTab(id, write = true) {
    document.querySelectorAll('[role="tab"]').forEach((b) => {
      const on = b.getAttribute("aria-controls") === id;
      b.setAttribute("aria-selected", String(on));
      $(b.getAttribute("aria-controls")).hidden = !on;
    });
    if (id === "insights" && meta) renderInsights();
    if (write) writeHash();
  }

  function bind() {
    [...FIELDS, ...CHECKS].forEach((f) => $(f).addEventListener(f === "q" ? "input" : "change", () => update()));
    $("more").addEventListener("click", () => { shown += PAGE; renderJobs(); });
    $("reset").addEventListener("click", () => {
      FIELDS.filter((f) => f !== "country").forEach((f) => { $(f).value = ""; });
      $("visa").checked = false; $("hideNationals").checked = true; update();
    });
    document.querySelectorAll('[role="tab"]').forEach((b) => b.addEventListener("click", () => selectTab(b.getAttribute("aria-controls"))));
    $("lang").addEventListener("click", () => {
      lang = lang === "ar" ? "en" : "ar"; store.set("lang", lang); applyLanguage(); readHash(); update(true);
    });
    $("country").addEventListener("change", () => store.set("country", $("country").value));
    $("mySkillInput").addEventListener("change", (e) => {
      const v = e.target.value.trim();
      const hit = meta.skills.find((s) => s.toLowerCase() === v.toLowerCase());
      if (hit) { mySkills.add(hit); store.set("mySkills", [...mySkills]); e.target.value = ""; renderInsights(); }
    });
  }

  async function start() {
    if (window.matchMedia("(max-width: 720px)").matches) $("filterBox").open = false;
    applyLanguage();
    try {
      const [m, j] = await Promise.all([fetch("data/meta.json").then((r) => r.json()), fetch("data/jobs.json").then((r) => r.json())]);
      meta = m; jobs = j;
    } catch (err) {
      $("count").textContent = "–";
      $("empty").hidden = false;
      $("empty").textContent = "The job data could not be loaded. Refresh the page to try again.";
      return;
    }
    meta.countries.forEach((c) => { regionOf[c.name] = c.region; });
    jobs.forEach((j) => { j._text = [j.t, j.c, j.r, ...j.k.map((k) => meta.skills[k])].join(" ").toLowerCase(); });
    applyLanguage();
    const saved = store.get("country", "");
    if (saved && !location.hash) $("country").value = saved;
    readHash();
    bind();
    window.addEventListener("hashchange", () => { readHash(); update(); });
    if (document.fonts) document.fonts.ready.then(sizeHero);
    window.addEventListener("resize", sizeHero);
    update(true);
  }

  start();
})();
