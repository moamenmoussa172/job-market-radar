/* Radarak - static site. Data: data/meta.json + data/jobs.json (refreshed daily by the pipeline). */
(() => {
  "use strict";

  const PAGE = 30;
  const MATCH = 0.6;                                  // a job is a match with >= 60% of its listed skills
  const FLAG = { visa: 1, nationals: 2, arabic: 4, longOpen: 8 };
  const JUNIOR = new Set(["Intern / Student", "Junior"]);
  const SKILLS_SHOWN = 6;

  // ------------------------------------------------------------------ text
  const T = {
    en: {
      brand: "Radarak", code: "Source code", skip: "Skip to jobs",
      browseTracks: "Browse by track", allTracks: "All tech",
      ask1: "I live in", ask2: "and I'm looking for", ask3: "jobs.", country: "Country", role: "Role",
      anyCountry: "any country", anyRole: "any tech", allOf: (x) => `${x} (all roles)`,
      countLabel: "jobs you can apply to", countAll: "open tech jobs", share: "Share this search", copied: "Link copied",
      updated: (d) => `Updated ${d}. New jobs are added every morning.`,
      yourSkills: "Your skills", addSkill: "Add a skill you have",
      yourSkillsHint: "Upload your CV or add what you know. Jobs are ranked by how many of their skills you have, and your skills are ticked on each job.",
      suggest: "Often asked for these jobs:", removeSkill: (s) => `Remove ${s}`,
      qRemote: "Remote", qVisa: "Visa or relocation", qJunior: "Junior & intern", qPay: "Shows salary",
      qWeek: "Posted this week", qHideNat: "Hide nationals-only",
      moreFilters: "More filters", moreFiltersOn: (n) => `More filters (${n} on)`,
      search: "Search", searchPh: "A title, company or skill", seniority: "Seniority", workMode: "Work mode",
      industry: "Industry", skill: "Must-have skill", arabic: "Arabic", any: "Any", arabicReq: "Required",
      arabicNot: "Not required", reset: "Clear all filters",
      tabJobs: "Jobs", tabInsights: "Skills & pay", tabSaved: "Saved", tabAbout: "How it works",
      sortBy: "Sort by", sortNew: "Newest", sortMatch: "Best match for my skills", sortPay: "Highest pay",
      summary: (jobs, companies) => `<b>${jobs}</b> jobs at <b>${companies}</b> companies`,
      remote: "Remote", remoteWorld: "Remote, worldwide", visaTag: "Visa / relocation", natTag: "Nationals only",
      arTag: "Arabic required", longOpen: "Open for a while", today: "Today", yesterday: "Yesterday",
      daysAgo: (n) => `${n} days ago`, moreLocs: (n) => `+${n} more ${n === 1 ? "location" : "locations"}`,
      hideLocs: "Hide locations", save: "Save", saved: "Saved", youHave: (a, b) => `You have ${a} of ${b} skills`,
      more: (n) => `Show ${n} more`,
      emptyJobs: "No jobs match all of these filters.", emptyFix: "Clear the extra filters",
      emptyCountry: "Few jobs are open to this country with these filters. Try \"any tech\" or turn off a quick filter.",
      savedHint: "Jobs you save are kept on this device. A job disappears from the list below when it's no longer open.",
      savedEmpty: "No saved jobs yet. Tap Save on any job to keep it here.",
      topSkills: "Skills these jobs ask for", topSkillsHint: "Share of jobs that mention each skill. Tap one to see only jobs that need it.",
      nextSkill: "The next skill to learn",
      nextHintOn: (s) => `Based on your skills (${s}). A job is a match when you have 60% or more of the skills it lists.`,
      nextHintOff: "Add your skills at the top of the page to see which one skill would open the most jobs for you.",
      matchLine: (m, n) => `You match ${m} of ${n} jobs.`, noNext: "You already match most of these jobs, or they list too few skills.",
      salaryByRole: "Pay by role", salaryHint: "Median yearly salary in US dollars, from jobs that publish pay.",
      whereJobs: "Where the jobs are", whereHint: "Office and hybrid jobs by country, plus remote jobs.",
      companies: "Companies hiring the most", roles: "Most wanted roles",
      statJobs: "jobs", statRemote: "remote", statCompanies: "companies", statPay: "median pay (USD / year)",
      statPayNone: "no published pay yet", tooFew: "Not enough data for these filters yet.",
      listedOf: (a, b) => `${a} of ${b} tracked jobs are listed here.`,
      loadError: "The job list couldn't be loaded. Check your connection and refresh the page.",
      cvUpload: "Upload your CV", cvPaste: "or paste its text", cvPrivacy: "Read on your device. Your CV is never uploaded or stored.",
      cvPasteLabel: "Your CV text", cvPastePh: "Paste the text of your CV here", cvRead: "Find my skills",
      cvReading: (f) => `Reading ${f}…`, cvTooBig: "That file is over 10 MB. Try a smaller PDF or Word file.",
      cvType: "Use a PDF, Word (.docx) or text file.", cvNoText: "No text could be read from this file. If it's a scanned PDF, paste your CV text instead.",
      cvFail: "This file couldn't be read. Try saving it as PDF, or paste the text.",
      cvNoSkills: "No known tech skills were found in this text. Add your skills by hand below.",
      cvTitle: "From your CV", cvSkills: "skills found", cvYears: "years of experience", cvRole: "looks like",
      cvMatches: "jobs you match (60%+ of their skills)", cvAdded: "Your skills below were updated from your CV. Remove any that are wrong.",
      cvGapTitle: "Worth adding to your CV, if you have them:",
      cvGapHint: "These skills appear in many jobs close to your profile but not in your CV.",
      cvShowRole: (r) => `Show ${r} jobs`, cvShowBest: "Show my best matches", cvClear: "Forget my CV skills",
    },
    ar: {
      brand: "رادارك", code: "الكود المصدري", skip: "انتقل للوظايف",
      browseTracks: "تصفّح حسب المجال", allTracks: "كل التك",
      ask1: "أنا عايش في", ask2: "وبدوّر على وظايف", ask3: "", country: "الدولة", role: "الوظيفة",
      anyCountry: "أي دولة", anyRole: "أي مجال تقني", allOf: (x) => `${x} (كل الوظايف)`,
      countLabel: "وظيفة تقدر تقدّم عليها", countAll: "وظيفة تقنية متاحة", share: "شارك البحث ده", copied: "اتنسخ اللينك",
      updated: (d) => `آخر تحديث ${d}. وظايف جديدة بتتضاف كل يوم الصبح.`,
      yourSkills: "مهاراتك", addSkill: "ضيف مهارة عندك",
      yourSkillsHint: "ارفع الـ CV أو ضيف اللي بتعرفه. بنرتب الوظايف حسب عدد مهاراتها اللي عندك، ومهاراتك بتظهر عليها علامة ✓.",
      suggest: "مطلوبة كتير في الوظايف دي:", removeSkill: (s) => `شيل ${s}`,
      qRemote: "ريموت", qVisa: "فيزا أو انتقال", qJunior: "جونيور وتدريب", qPay: "فيها مرتب",
      qWeek: "اتنشرت الأسبوع ده", qHideNat: "اخفي اللي للمواطنين بس",
      moreFilters: "فلاتر أكتر", moreFiltersOn: (n) => `فلاتر أكتر (${n} شغالين)`,
      search: "بحث", searchPh: "وظيفة أو شركة أو مهارة", seniority: "المستوى", workMode: "نوع العمل",
      industry: "المجال", skill: "مهارة لازم تكون مطلوبة", arabic: "العربي", any: "الكل", arabicReq: "مطلوب",
      arabicNot: "مش مطلوب", reset: "امسح كل الفلاتر",
      tabJobs: "الوظايف", tabInsights: "المهارات والمرتبات", tabSaved: "المحفوظة", tabAbout: "إزاي بيشتغل",
      sortBy: "رتّب حسب", sortNew: "الأحدث", sortMatch: "الأنسب لمهاراتي", sortPay: "الأعلى مرتب",
      summary: (jobs, companies) => `<b>${jobs}</b> وظيفة في <b>${companies}</b> شركة`,
      remote: "ريموت", remoteWorld: "ريموت من أي مكان", visaTag: "فيزا / انتقال", natTag: "للمواطنين بس",
      arTag: "العربي مطلوب", longOpen: "مفتوحة من فترة", today: "النهارده", yesterday: "امبارح",
      daysAgo: (n) => `من ${n} يوم`, moreLocs: (n) => `+${n} أماكن تانية`,
      hideLocs: "اخفي الأماكن", save: "احفظ", saved: "محفوظة", youHave: (a, b) => `عندك ${a} من ${b} مهارات`,
      more: (n) => `اعرض ${n} كمان`,
      emptyJobs: "مفيش وظايف بكل الفلاتر دي.", emptyFix: "امسح الفلاتر الزيادة",
      emptyCountry: "وظايف قليلة مفتوحة للبلد دي بالفلاتر دي. جرّب \"أي مجال تقني\" أو اقفل فلتر سريع.",
      savedHint: "الوظايف اللي بتحفظها بتفضل على الجهاز ده. الوظيفة بتختفي من هنا لما تتقفل.",
      savedEmpty: "مفيش وظايف محفوظة لسه. اضغط احفظ على أي وظيفة.",
      topSkills: "المهارات المطلوبة في الوظايف دي", topSkillsHint: "نسبة الوظايف اللي بتطلب كل مهارة. اضغط على مهارة عشان تشوف وظايفها بس.",
      nextSkill: "المهارة الجاية اللي تتعلمها",
      nextHintOn: (s) => `على أساس مهاراتك (${s}). الوظيفة بتناسبك لو عندك 60% أو أكتر من مهاراتها.`,
      nextHintOff: "ضيف مهاراتك فوق في الصفحة عشان تعرف أنهي مهارة هتفتحلك أكبر عدد من الوظايف.",
      matchLine: (m, n) => `إنت مناسب لـ ${m} من ${n} وظيفة.`, noNext: "إنت مناسب لأغلب الوظايف دي، أو مهاراتها المكتوبة قليلة.",
      salaryByRole: "المرتبات حسب الوظيفة", salaryHint: "متوسط المرتب السنوي بالدولار، من الوظايف اللي بتعلن المرتب.",
      whereJobs: "الوظايف فين", whereHint: "وظايف المكتب والهايبرد حسب الدولة، بالإضافة للريموت.",
      companies: "أكتر شركات بتوظف", roles: "أكتر وظايف مطلوبة",
      statJobs: "وظيفة", statRemote: "ريموت", statCompanies: "شركة", statPay: "متوسط المرتب (دولار / سنة)",
      statPayNone: "مفيش مرتبات معلنة لسه", tooFew: "مفيش بيانات كفاية للفلاتر دي لسه.",
      listedOf: (a, b) => `${a} من ${b} وظيفة بنتابعها معروضة هنا.`,
      loadError: "مقدرناش نحمّل الوظايف. اتأكد من النت واعمل تحديث للصفحة.",
      cvUpload: "ارفع الـ CV بتاعك", cvPaste: "أو الصق النص", cvPrivacy: "بيتقري على جهازك. الـ CV مش بيترفع ولا بيتحفظ في أي مكان.",
      cvPasteLabel: "نص الـ CV", cvPastePh: "الصق نص الـ CV هنا", cvRead: "طلّع مهاراتي",
      cvReading: (f) => `بنقرا ${f}…`, cvTooBig: "الملف أكبر من 10 ميجا. جرّب PDF أو Word أصغر.",
      cvType: "استخدم ملف PDF أو Word (.docx) أو نص.", cvNoText: "مقدرناش نقرا نص من الملف ده. لو PDF متصوّر، الصق نص الـ CV بدل كده.",
      cvFail: "مقدرناش نقرا الملف ده. جرّب تحفظه PDF أو الصق النص.",
      cvNoSkills: "ملقيناش مهارات تقنية معروفة في النص ده. ضيف مهاراتك بإيدك تحت.",
      cvTitle: "من الـ CV بتاعك", cvSkills: "مهارة لقيناها", cvYears: "سنين خبرة", cvRole: "شكلك",
      cvMatches: "وظيفة مناسبة لك (60%+ من مهاراتها)", cvAdded: "مهاراتك تحت اتحدّثت من الـ CV. شيل أي مهارة غلط.",
      cvGapTitle: "تستاهل تضيفها للـ CV لو بتعرفها:",
      cvGapHint: "المهارات دي مطلوبة في وظايف كتير قريبة من بروفايلك ومش مكتوبة في الـ CV.",
      cvShowRole: (r) => `اعرض وظايف ${r}`, cvShowBest: "اعرض أنسب وظايف ليا", cvClear: "امسح مهارات الـ CV",
    },
  };
  const ABOUT = {
    en: `
      <h2>What this is</h2>
      <p>Radarak (Arabic for "your radar") collects tech job postings every day from company career pages and job APIs, and shows the ones you can actually apply to from where you live: office and hybrid jobs in your country, plus remote jobs that are open to your country or region.</p>
      <h2>How "jobs you can apply to" works</h2>
      <p>Many remote jobs are only open to people in certain countries. Each posting's location and eligibility text is mapped to countries and regions, so picking your country hides remote jobs you aren't allowed to take.</p>
      <h2>Your skills and matching</h2>
      <p>Skills are read from each job description (about 170 of them, from SQL to SAP). Add yours at the top: jobs where you have 60% or more of the listed skills count as a match, and <b>The next skill to learn</b> shows the one skill that would make you a match for the most extra jobs.</p>
      <h2>Tags on each job</h2>
      <ul>
        <li><b>Visa / relocation</b>: the posting says the employer sponsors visas or helps you relocate.</li>
        <li><b>Nationals only</b>: limited to citizens, for example "Saudi nationals only" or Emiratisation roles. Hidden by default.</li>
        <li><b>Arabic required</b>: Arabic is listed as a required language.</li>
        <li><b>Open for a while</b>: the job was first posted long ago and is still open.</li>
      </ul>
      <h2>Salaries</h2>
      <p>Only jobs that publish pay are counted. Salaries in any currency and period are turned into a yearly amount in US dollars.</p>
      <h2>Sources</h2>
      <p>Company career boards (Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Recruitee, Personio) and job APIs. Every job links to its original posting, where you apply. Some jobs carry their source's credit (for example, Jobs by Adzuna).</p>
      <p>The data is collected automatically and can miss jobs or contain mistakes. Saved jobs and your skills stay in your browser. The project is open source.</p>`,
    ar: `
      <h2>ده إيه</h2>
      <p>رادارك بيجمع وظايف التك كل يوم من صفحات التوظيف بتاعة الشركات ومن مواقع الوظايف، ويوريك اللي تقدر تقدّم عليها فعلًا من البلد اللي إنت فيها: وظايف المكتب والهايبرد في بلدك، والوظايف الريموت المفتوحة لبلدك أو منطقتك.</p>
      <h2>"وظايف تقدر تقدّم عليها" معناها إيه</h2>
      <p>وظايف ريموت كتير مفتوحة لناس في دول معينة بس. بنقرا مكان كل وظيفة وشروطها ونربطها بالدول والمناطق، فلما تختار بلدك بنخفي الوظايف اللي مش مسموح لك تقدّم عليها.</p>
      <h2>مهاراتك والتطابق</h2>
      <p>بنقرا المهارات من وصف كل وظيفة (حوالي 170 مهارة، من SQL لحد SAP). ضيف مهاراتك فوق: الوظيفة بتعتبر مناسبة لو عندك 60% أو أكتر من مهاراتها، و<b>المهارة الجاية اللي تتعلمها</b> بتقولك على المهارة اللي هتفتحلك أكبر عدد من الوظايف.</p>
      <h2>العلامات على كل وظيفة</h2>
      <ul>
        <li><b>فيزا / انتقال</b>: الشركة بتقول إنها بتعمل فيزا أو بتساعد في الانتقال.</li>
        <li><b>للمواطنين بس</b>: الوظيفة لمواطني البلد بس، زي "للسعوديين فقط". مخفية من الأول.</li>
        <li><b>العربي مطلوب</b>: اللغة العربية مطلوبة في الوظيفة.</li>
        <li><b>مفتوحة من فترة</b>: الوظيفة اتنشرت من زمان ولسه مفتوحة.</li>
      </ul>
      <h2>المرتبات</h2>
      <p>بنحسب بس الوظايف اللي بتعلن المرتب، وبنحوّل أي مرتب بأي عملة لمبلغ سنوي بالدولار.</p>
      <h2>المصادر</h2>
      <p>صفحات التوظيف بتاعة الشركات (Greenhouse و Lever و Ashby و SmartRecruiters و Workable و Recruitee و Personio) ومواقع وظايف. كل وظيفة فيها لينك للإعلان الأصلي، والتقديم بيكون هناك.</p>
      <p>البيانات بتتجمع أوتوماتيك وممكن يفوتها وظايف أو يكون فيها أخطاء. الوظايف المحفوظة ومهاراتك بتفضل في المتصفح بتاعك. المشروع مفتوح المصدر.</p>`,
  };

  // ------------------------------------------------------------------ state
  const $ = (id) => document.getElementById(id);
  const store = {
    get(k, d) { try { const v = localStorage.getItem("jr_" + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem("jr_" + k, JSON.stringify(v)); } catch { /* storage unavailable */ } },
  };
  let lang = store.get("lang", (navigator.language || "").startsWith("ar") ? "ar" : "en");
  let meta = null, jobs = [], regionOf = {}, shown = PAGE, groups = [], current = [];
  let mySkills = new Set(store.get("mySkills", []));
  let savedJobs = store.get("saved", {});               // id -> {t, c, l, u, p}
  const quick = { remote: false, visa: false, junior: false, pay: false, week: false, hideNat: true };
  const openLocs = new Set();
  const t = (k) => T[lang][k] ?? T.en[k] ?? k;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (n) => Number(n).toLocaleString("en-US");
  const weekAgo = new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10);
  // every track has its own colour (style.css: --t-<key>), used on job rows, chips, bars and the radar
  const TRACK_KEY = {
    "Data & Analytics": "data", "AI & Machine Learning": "ai", "Software Engineering": "sw", "Mobile Development": "mob",
    "QA & Testing": "qa", "UI/UX Design": "ux", "DevOps & Cloud": "ops", "Security": "sec", "ERP & CRM": "erp",
    "Networks & Telecom": "net", "Product & Delivery": "prod", "IT & Support": "it",
  };
  const trackOfRole = {};
  const tc = (track) => `--tc:var(--t-${TRACK_KEY[track] || "it"})`;

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
      items: [{ label: tr.name, value: "track:" + tr.name },
              ...tr.roles.map((r) => ({ label: r, value: "role:" + r }))],
    })), t("anyRole"));
    fillSelect($("seniority"), meta.seniorities, t("any"));
    fillSelect($("workMode"), meta.work_modes, t("any"));
    fillSelect($("industry"), meta.industries, t("any"));
    fillSelect($("skill"), meta.skills, t("any"));
    fillSelect($("arabic"), [{ label: t("arabicReq"), value: "req" }, { label: t("arabicNot"), value: "not" }], t("any"));
    $("skillList").innerHTML = meta.skills.map((s) => `<option value="${esc(s)}">`).join("");
  }

  // Hero dropdowns are as wide as the chosen text, so the sentence reads naturally.
  const measurer = document.createElement("canvas").getContext("2d");
  function autosize(sel) {
    const cs = getComputedStyle(sel);
    measurer.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const text = sel.selectedOptions[0] ? sel.selectedOptions[0].text : "";
    const room = sel.closest(".ask").clientWidth;
    sel.style.width = Math.min(Math.ceil(measurer.measureText(text).width + 10), room) + "px";
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
      $("footText").textContent = `${t("listedOf")(num(meta.listed_jobs), num(meta.total_active_jobs))} ${meta.credits.join(", ")}.`;
    }
  }

  // ------------------------------------------------------------------ filters <-> URL (shareable links)
  const FIELDS = ["country", "role", "seniority", "workMode", "industry", "skill", "arabic", "q", "sort"];
  function readHash() {
    const h = new URLSearchParams(location.hash.slice(1));
    FIELDS.forEach((f) => { $(f).value = h.get(f) || (f === "sort" ? "new" : (f === "country" ? $(f).value : "")); });
    Object.keys(quick).forEach((k) => { if (h.has(k)) quick[k] = h.get(k) === "1"; });
    syncToggles();
    if (h.has("tab")) selectTab(h.get("tab"), false);
  }
  function writeHash() {
    const h = new URLSearchParams();
    FIELDS.forEach((f) => { if ($(f).value && !(f === "sort" && $(f).value === "new")) h.set(f, $(f).value); });
    Object.entries(quick).forEach(([k, v]) => { if (v !== (k === "hideNat")) h.set(k, v ? "1" : "0"); });
    const tab = document.querySelector('[role="tab"][aria-selected="true"]').getAttribute("aria-controls");
    if (tab !== "jobs") h.set("tab", tab);
    history.replaceState(null, "", h.toString() ? "#" + h.toString() : location.pathname);
  }
  function syncToggles() {
    document.querySelectorAll(".toggle").forEach((b) => b.setAttribute("aria-pressed", String(quick[b.dataset.flag])));
  }

  function canApplyFrom(job, country) {
    if (!country) return true;
    if (job.co.includes(country)) return true;
    return job.w === "Remote" && (job.ww === 1 || job.rg.includes(regionOf[country]) || job.rg.includes("Worldwide"));
  }

  function filtered(ignoreRole) {
    const country = $("country").value, role = ignoreRole ? "" : $("role").value, sen = $("seniority").value, wm = $("workMode").value;
    const ind = $("industry").value, skill = $("skill").value, ar = $("arabic").value;
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
      if (quick.remote && j.w !== "Remote") return false;
      if (quick.visa && !(f & FLAG.visa)) return false;
      if (quick.junior && !JUNIOR.has(j.s)) return false;
      if (quick.pay && !j.$) return false;
      if (quick.week && (j.p < weekAgo || (f & FLAG.longOpen))) return false;
      if (quick.hideNat && (f & FLAG.nationals)) return false;
      if (ar === "req" && !(f & FLAG.arabic)) return false;
      if (ar === "not" && (f & FLAG.arabic)) return false;
      if (q && !j._text.includes(q)) return false;
      return canApplyFrom(j, country);
    });
  }

  // The same job is often posted once per city: show it once, with its other locations.
  function group(list) {
    const byKey = new Map();
    for (const j of list) {
      const key = j.t.toLowerCase() + "|" + (j.c || "").toLowerCase();
      const g = byKey.get(key);
      if (g) g.all.push(j); else byKey.set(key, { key, job: j, all: [j] });
    }
    const mine = mySkillIdx();
    const out = [...byKey.values()];
    for (const g of out) {
      g.all.sort((a, b) => (a.p < b.p ? 1 : -1));
      g.job = g.all[0];
      const pay = g.all.find((x) => x.$);
      g.pay = pay ? pay.$ : null;
      g.flags = g.all.reduce((f, x) => f | (x.f || 0), 0) & ~(g.all.every((x) => (x.f || 0) & FLAG.longOpen) ? 0 : FLAG.longOpen);
      const k = g.job.k;
      g.have = mine.size ? k.filter((i) => mine.has(i)).length : 0;
      // a job listing only 1-2 skills is weak evidence: "4 of 5" should rank above "1 of 1"
      g.match = mine.size && k.length ? g.have / Math.max(k.length, 4) : -1;
    }
    const sort = $("sort").value;
    const byNew = (a, b) => (a.job.p < b.job.p ? 1 : a.job.p > b.job.p ? -1 : 0);
    if (sort === "match") out.sort((a, b) => b.match - a.match || b.have - a.have || byNew(a, b));
    else if (sort === "pay") out.sort((a, b) => ((b.pay ? b.pay[0] + b.pay[1] : -1) - (a.pay ? a.pay[0] + a.pay[1] : -1)) || byNew(a, b));
    else out.sort(byNew);
    return out;
  }

  // ------------------------------------------------------------------ jobs
  function ago(iso) {
    const days = Math.max(0, Math.round((Date.now() - new Date(iso + "T12:00:00Z")) / 864e5));
    return days === 0 ? t("today") : days === 1 ? t("yesterday") : t("daysAgo")(days);
  }
  const payText = ($) => ($ ? ($[0] === $[1] ? `$${$[0]}k` : `$${$[0]}k – $${$[1]}k`) : "");
  const mySkillIdx = () => new Set([...mySkills].map((s) => meta.skills.indexOf(s)).filter((i) => i >= 0));

  function jobRow(g) {
    const j = g.job, f = g.flags, mine = mySkillIdx();
    const others = g.all.length - 1;
    const tags = [
      j.w === "Remote" ? `<span class="tag">${j.ww ? t("remoteWorld") : t("remote")}</span>` : `<span class="tag plain">${esc(j.w)}</span>`,
      f & FLAG.visa ? `<span class="tag visa">${t("visaTag")}</span>` : "",
      f & FLAG.nationals ? `<span class="tag nat">${t("natTag")}</span>` : "",
      f & FLAG.arabic ? `<span class="tag ar">${t("arTag")}</span>` : "",
      `<span class="tag role">${esc(j.r)}</span>`,
      j.s && j.s !== "Not stated" ? `<span class="tag plain">${esc(j.s)}</span>` : "",
      j.by ? `<span class="tag plain">${esc(j.by)}</span>` : "",
    ].join("");
    const ks = [...j.k].sort((a, b) => (mine.has(b) ? 1 : 0) - (mine.has(a) ? 1 : 0));
    const skills = ks.slice(0, SKILLS_SHOWN).map((k) => `<span class="sk${mine.has(k) ? " have" : ""}">${esc(meta.skills[k])}</span>`).join("")
      + (ks.length > SKILLS_SHOWN ? `<span class="sk">+${ks.length - SKILLS_SHOWN}</span>` : "");
    const isSaved = !!savedJobs[j.id];
    const locsOpen = openLocs.has(g.key);
    return `<li class="job" style="${tc(j.tr)}">
      <div>
        <h3><a href="${esc(j.u)}" target="_blank" rel="noopener nofollow">${esc(j.t)}</a></h3>
        <p class="where"><b>${esc(j.c || "")}</b><span>${esc(j.l || "")}</span>${others > 0
          ? `<button type="button" class="locbtn" data-key="${esc(g.key)}" aria-expanded="${locsOpen}">${locsOpen ? t("hideLocs") : t("moreLocs")(others)}</button>` : ""}</p>
      </div>
      <div class="side">
        ${g.pay ? `<span class="pay">${payText(g.pay)}</span>` : ""}
        <span>${f & FLAG.longOpen ? t("longOpen") : ago(j.p)}</span>
        <button type="button" class="save" data-id="${esc(j.id)}" aria-pressed="${isSaved}">${isSaved ? t("saved") : t("save")}</button>
      </div>
      ${locsOpen ? `<ul class="locs">${g.all.slice(1).map((x) => `<li><a href="${esc(x.u)}" target="_blank" rel="noopener nofollow">${esc(x.l || x.t)}</a></li>`).join("")}</ul>` : ""}
      <div class="tags">${tags}</div>
      ${j.k.length ? `<div class="skills">${skills}${mine.size ? `<span class="matchbadge">${t("youHave")(g.have, j.k.length)}</span>` : ""}</div>` : ""}
    </li>`;
  }

  function renderJobs() {
    const list = $("jobList");
    list.removeAttribute("aria-busy");
    list.innerHTML = groups.slice(0, shown).map(jobRow).join("");
    const companies = new Set(current.map((j) => (j.c || "").toLowerCase()).filter(Boolean)).size;
    $("resultSummary").innerHTML = t("summary")(num(groups.length), num(companies));
    const empty = $("empty");
    empty.hidden = groups.length > 0;
    if (!groups.length) {
      empty.innerHTML = `<p>${esc($("country").value ? t("emptyCountry") : t("emptyJobs"))}</p>
        <button type="button" class="more" id="emptyReset">${t("emptyFix")}</button>`;
      $("emptyReset").addEventListener("click", resetFilters);
    }
    const left = groups.length - shown;
    $("more").hidden = left <= 0;
    $("more").textContent = t("more")(Math.min(PAGE, left));
  }

  function renderSaved() {
    const ids = Object.keys(savedJobs);
    const open = new Map(jobs.map((j) => [j.id, j]));
    const still = ids.filter((id) => open.has(id));
    $("savedCount").hidden = !still.length;
    $("savedCount").textContent = still.length;
    if ($("saved").hidden) return;
    $("savedList").innerHTML = still.map((id) => jobRow({ key: "saved:" + id, job: open.get(id), all: [open.get(id)],
      pay: open.get(id).$ || null, flags: open.get(id).f || 0, have: 0, match: -1 })).join("");
    $("savedEmpty").hidden = still.length > 0;
    $("savedEmpty").textContent = t("savedEmpty");
  }

  function renderSkills() {
    $("mySkills").innerHTML = [...mySkills].map((s) =>
      `<button type="button" class="chip" data-skill="${esc(s)}" aria-label="${esc(t("removeSkill")(s))}">${esc(s)} ✕</button>`).join("");
    // suggestions: the most common skills in the current results that the visitor hasn't added
    const mine = mySkillIdx();
    const counts = new Map();
    current.forEach((j) => j.k.forEach((k) => { if (!mine.has(k)) counts.set(k, (counts.get(k) || 0) + 1); }));
    const top = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k]) => meta.skills[k]);
    $("suggestRow").hidden = !top.length;
    $("suggest").innerHTML = top.map((s) => `<button type="button" class="chip add" data-add="${esc(s)}">+ ${esc(s)}</button>`).join("");
  }

  // ------------------------------------------------------------------ insights
  function bars(el, rows, opts = {}) {
    if (!rows.length) { el.innerHTML = `<p class="none">${t("tooFew")}</p>`; return; }
    const max = Math.max(...rows.map((r) => r.v));
    el.innerHTML = rows.map((r) => {
      const tag = opts.click ? "button" : "div";
      const attrs = opts.click ? ` type="button" data-value="${esc(r.key ?? r.name)}"` : "";
      const color = r.tr ? ` style="${tc(r.tr)}"` : "";
      return `<${tag} class="bar${r.tr ? " tracked" : ""}"${attrs}${color}><span class="name" title="${esc(r.name)}">${esc(r.name)}</span>
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
    bars($("skillBars"), n ? countBy(js.flatMap((j) => j.k), (k) => k).filter(([k]) => meta.skills[k] !== chosen)
      .slice(0, 12).map(([k, c]) => ({ name: meta.skills[k], v: Math.round((100 * c) / n) })) : [],
      { fmt: (v) => v + "%", click: (s) => { $("skill").value = s; update(); } });

    const mine = mySkillIdx();
    $("nextHint").textContent = mine.size ? t("nextHintOn")([...mySkills].join(", ")) : t("nextHintOff");
    const withSkills = js.filter((j) => j.k.length);
    if (!mine.size) {
      $("matchLine").textContent = ""; $("nextBars").innerHTML = "";
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
      if (rows.length) bars($("nextBars"), rows, { fmt: (v) => "+" + num(v), click: (s) => addSkill(s) });
      else $("nextBars").innerHTML = `<p class="none">${t("noNext")}</p>`;
    }

    const byRole = new Map();
    js.filter((j) => j.$).forEach((j) => { const a = byRole.get(j.r) || []; a.push((j.$[0] + j.$[1]) / 2); byRole.set(j.r, a); });
    bars($("salaryBars"), [...byRole.entries()].filter(([, v]) => v.length >= 3)
      .map(([r, v]) => ({ name: r, v: Math.round(median(v)), tr: trackOfRole[r] })).sort((a, b) => b.v - a.v).slice(0, 10),
      { fmt: (v) => "$" + v + "k", click: (r) => { $("role").value = "role:" + r; update(); } });

    const places = countBy(js.filter((j) => j.w !== "Remote"), (j) => j.co[0]).slice(0, 8).map(([k, v]) => ({ name: k, v }));
    if (remote) places.push({ name: t("remote"), v: remote });
    bars($("placeBars"), places.sort((a, b) => b.v - a.v));

    $("companyList").innerHTML = countBy(js, (j) => j.c).slice(0, 10)
      .map(([c, v]) => `<li>${esc(c)} <span>(${num(v)})</span></li>`).join("") || `<p class="none">${t("tooFew")}</p>`;
    bars($("roleBars"), countBy(js, (j) => j.r).slice(0, 10).map(([k, v]) => ({ name: k, v, tr: trackOfRole[k] })),
      { click: (r) => { $("role").value = "role:" + r; update(); } });
  }

  // ------------------------------------------------------------------ CV (read in the browser, never uploaded)
  const loaded = {};
  function loadScript(src) {
    loaded[src] = loaded[src] || new Promise((ok, fail) => {
      const s = document.createElement("script"); s.src = src; s.onload = ok; s.onerror = () => fail(new Error("load " + src));
      document.head.appendChild(s);
    });
    return loaded[src];
  }
  async function pdfText(buf) {
    await loadScript("vendor/pdf.min.js");
    window.pdfjsLib.GlobalWorkerOptions.workerSrc = "vendor/pdf.worker.min.js";
    const doc = await window.pdfjsLib.getDocument({ data: buf }).promise;
    const parts = [];
    for (let i = 1; i <= Math.min(doc.numPages, 15); i++) {
      const page = await doc.getPage(i);
      const content = await page.getTextContent();
      parts.push(content.items.map((it) => it.str + (it.hasEOL ? "\n" : " ")).join(""));
    }
    return parts.join("\n");
  }
  async function docxText(buf) {
    await loadScript("vendor/mammoth.browser.min.js");
    return (await window.mammoth.extractRawText({ arrayBuffer: buf })).value;
  }

  let skillRegex = null;
  function findSkills(text) {
    skillRegex = skillRegex || (meta.skill_patterns || []).map((p) => { try { return p ? new RegExp(p, "i") : null; } catch { return null; } });
    return meta.skills.filter((s, i) => skillRegex[i] && skillRegex[i].test(text));
  }
  function findYears(text) {
    const now = new Date().getFullYear();
    let best = 0;
    for (const m of text.matchAll(/(\d{1,2})\s*\+?\s*(?:years|yrs|year)\b(?:\s+of)?(?:\s+\w+){0,3}\s+experience/gi)) best = Math.max(best, +m[1]);
    for (const m of text.matchAll(/\b(\d{1,2})\s*\+?\s*(?:years|yrs)\b/gi)) if (+m[1] <= 40 && best === 0) best = Math.max(best, +m[1]);
    // work-history ranges: "2019 - Present", "03/2018 – 2021"
    let first = null;
    const school = /universit|bachelor|faculty|school|college|degree|b\.?sc|m\.?sc|master|diploma|جامعة|كلية|بكالوريوس/i;
    for (const line of text.split(/\n+/)) {
      if (school.test(line)) continue;               // study years are not work experience
      for (const m of line.matchAll(/\b((?:19|20)\d{2})\s*(?:-|–|—|to)\s*(present|current|now|today|(?:19|20)\d{2})\b/gi)) {
        const start = +m[1];
        if (start >= 1980 && start <= now) first = first === null ? start : Math.min(first, start);
      }
    }
    const fromRanges = first !== null ? now - first : 0;
    const years = best || fromRanges;              // what the CV says beats what the dates suggest
    return years > 0 && years <= 45 ? years : null;
  }
  const ROLE_HINTS = [
    [/\bdata engineer/gi, "Data Engineer"], [/\banalytics engineer/gi, "Analytics Engineer"],
    [/\bdata scientist/gi, "Data Scientist"], [/\bdata analyst/gi, "Data Analyst"],
    [/\b(bi|business intelligence|power bi) (developer|analyst)/gi, "BI Analyst / Developer"],
    [/\b(machine learning|ml|ai) engineer/gi, "ML / AI Engineer"], [/\bmlops/gi, "MLOps Engineer"],
    [/\bback[\s-]?end (developer|engineer)/gi, "Backend Engineer"], [/\bfront[\s-]?end (developer|engineer)/gi, "Frontend Engineer"],
    [/\bfull[\s-]?stack (developer|engineer)/gi, "Full-Stack Engineer"], [/\bios (developer|engineer)/gi, "iOS Engineer"],
    [/\bandroid (developer|engineer)/gi, "Android Engineer"], [/\b(flutter|react native) (developer|engineer)/gi, "Cross-platform Mobile Engineer"],
    [/\bdevops/gi, "DevOps / Platform Engineer"], [/\bsite reliability|\bsre\b/gi, "Site Reliability Engineer"],
    [/\bcloud (engineer|architect)/gi, "Cloud / Infrastructure Engineer"],
    [/\b(qa|test automation|sdet|quality assurance) (engineer|analyst|tester)|\bsoftware tester/gi, "QA Automation Engineer"],
    [/\b(ux|ui|product) designer|\bux\/ui|\bui\/ux/gi, "UX / Product Designer"],
    [/\b(security|soc|cyber ?security) (engineer|analyst)|penetration tester/gi, "Security Engineer / Analyst"],
    [/\b(sap|abap|salesforce|dynamics 365|oracle ebs) (consultant|developer)/gi, "ERP / CRM Consultant"],
    [/\bnetwork engineer|\bnoc engineer/gi, "Network Engineer"], [/\bproduct (manager|owner)/gi, "Product Manager / Owner"],
    [/\bsoftware (engineer|developer)/gi, "Software Engineer"],
  ];
  function guessRole(text) {
    const known = new Set(meta.tracks.flatMap((t) => t.roles));
    let best = null, score = 0;
    for (const [re, role] of ROLE_HINTS) {
      const n = (text.match(re) || []).length;
      if (n > score && known.has(role)) { best = role; score = n; }
    }
    return best;
  }

  function cvStatus(msg, err) { const el = $("cvStatus"); el.textContent = msg || ""; el.classList.toggle("err", !!err); }

  function useCvText(text) {
    if (!text || text.trim().length < 80) { cvStatus(t("cvNoText"), true); return; }
    const skills = findSkills(text);
    if (!skills.length) { cvStatus(t("cvNoSkills"), true); return; }
    cvStatus("");
    const years = findYears(text), role = guessRole(text);
    mySkills = new Set(skills); store.set("mySkills", [...mySkills]);
    $("sort").value = "match";
    update();
    // jobs close to this profile: matches plus near-matches; what do they ask for that the CV doesn't mention?
    const mine = mySkillIdx();
    const near = current.filter((j) => j.k.length >= 3 && j.k.filter((k) => mine.has(k)).length / j.k.length >= 0.4);
    const matched = current.filter((j) => j.k.length && j.k.filter((k) => mine.has(k)).length / j.k.length >= MATCH).length;
    const gap = new Map();
    near.forEach((j) => j.k.forEach((k) => { if (!mine.has(k)) gap.set(k, (gap.get(k) || 0) + 1); }));
    const gaps = [...gap.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8).map(([k]) => meta.skills[k]);
    const r = $("cvResult");
    r.hidden = false;
    r.innerHTML = `<h3>${t("cvTitle")}</h3>
      <div class="facts">
        <div><b>${skills.length}</b><span>${t("cvSkills")}</span></div>
        ${years ? `<div><b>${years}</b><span>${t("cvYears")}</span></div>` : ""}
        <div><b>${num(matched)}</b><span>${t("cvMatches")}</span></div>
        ${role ? `<div><b>${esc(role)}</b><span>${t("cvRole")}</span></div>` : ""}
      </div>
      <p class="hint">${t("cvAdded")}</p>
      ${gaps.length ? `<div class="gap"><p><b>${t("cvGapTitle")}</b></p><p class="hint">${t("cvGapHint")}</p>
        <div class="chips">${gaps.map((s) => `<button type="button" class="chip add" data-add="${esc(s)}">+ ${esc(s)}</button>`).join("")}</div></div>` : ""}
      <div class="actions">
        ${role ? `<button type="button" class="cvbtn" id="cvRoleBtn">${esc(t("cvShowRole")(role))}</button>` : ""}
        <button type="button" class="sharebtn" id="cvBestBtn">${t("cvShowBest")}</button>
        <button type="button" class="linkbtn" id="cvClearBtn">${t("cvClear")}</button>
      </div>`;
    if (role) $("cvRoleBtn").addEventListener("click", () => { $("role").value = "role:" + role; update(); goToJobs(); });
    $("cvBestBtn").addEventListener("click", goToJobs);
    $("cvClearBtn").addEventListener("click", () => { mySkills.clear(); store.set("mySkills", []); r.hidden = true; $("sort").value = "new"; update(); });
  }
  function goToJobs() { selectTab("jobs"); $("results").scrollIntoView({ behavior: "smooth", block: "start" }); }

  async function readCvFile(file) {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) { cvStatus(t("cvTooBig"), true); return; }
    const name = file.name.toLowerCase();
    const kind = name.endsWith(".pdf") || file.type === "application/pdf" ? "pdf"
      : name.endsWith(".docx") ? "docx" : name.endsWith(".txt") || file.type.startsWith("text/") ? "txt" : null;
    if (!kind) { cvStatus(t("cvType"), true); return; }
    $("cvBtn").disabled = true; cvStatus(t("cvReading")(file.name));
    try {
      const text = kind === "txt" ? await file.text()
        : kind === "pdf" ? await pdfText(await file.arrayBuffer()) : await docxText(await file.arrayBuffer());
      useCvText(text);
    } catch {
      cvStatus(t("cvFail"), true);
    } finally {
      $("cvBtn").disabled = false; $("cvFile").value = "";
    }
  }

  // ------------------------------------------------------------------ track pills + radar
  function renderTracks() {
    // count jobs the way the list shows them: the same title at the same company counts once
    const keys = new Map(), all = new Set();
    for (const j of filtered(true)) {
      const k = j.t.toLowerCase() + "|" + (j.c || "").toLowerCase();
      all.add(k);
      if (!keys.has(j.tr)) keys.set(j.tr, new Set());
      keys.get(j.tr).add(k);
    }
    const counts = new Map([...keys].map(([tr, set]) => [tr, set.size]));
    const base = { length: all.size };
    const role = $("role").value;
    const active = role.startsWith("track:") ? role.slice(6) : role.startsWith("role:") ? trackOfRole[role.slice(5)] : "";
    const pill = (value, label, n, track) => `<button type="button" class="tpill${(value === "" ? !role : active === track) ? " on" : ""}"
      data-track="${esc(value)}"${track ? ` style="${tc(track)}"` : ""}><span class="dot"></span>${esc(label)} <span class="n">${num(n)}</span></button>`;
    $("trackPills").innerHTML = pill("", t("allTracks"), base.length, "")
      + meta.tracks.filter((tr) => counts.get(tr.name)).map((tr) => pill("track:" + tr.name, tr.name, counts.get(tr.name), tr.name)).join("");
    // on phones the pills scroll sideways: keep the chosen one in view (without scrolling the page)
    const wrap = $("trackPills"), on = wrap.querySelector(".tpill.on");
    if (on && wrap.scrollWidth > wrap.clientWidth) {
      const w = wrap.getBoundingClientRect(), r = on.getBoundingClientRect();
      if (r.left < w.left || r.right > w.right) wrap.scrollLeft += r.left - w.left - (w.width - r.width) / 2;
    }
    // radar blips: one per track, bigger and closer to the centre when it has more jobs
    const max = Math.max(1, ...counts.values());
    $("blips").innerHTML = meta.tracks.map((tr, i) => {
      const n = counts.get(tr.name) || 0;
      if (!n) return "";
      const share = n / max, angle = (i / meta.tracks.length) * 2 * Math.PI - Math.PI / 2 + 0.4;
      const rad = 175 - 110 * share, x = 200 + rad * Math.cos(angle), y = 200 + rad * Math.sin(angle);
      return `<circle class="blip${active && active !== tr.name ? " dim" : ""}" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}"
        r="${(5 + 9 * Math.sqrt(share)).toFixed(1)}" style="${tc(tr.name)};animation-delay:${(i * 0.12).toFixed(2)}s"><title>${esc(tr.name)}: ${num(n)}</title></circle>`;
    }).join("");
  }

  // ------------------------------------------------------------------ wiring
  function update(keepPage) {
    current = filtered();
    groups = group(current);
    if (!keepPage) shown = PAGE;
    sizeHero();
    $("count").textContent = num(groups.length);
    $("countLabel").textContent = $("country").value ? t("countLabel") : t("countAll");
    const extra = ["seniority", "workMode", "industry", "skill", "arabic", "q"].filter((f) => $(f).value).length;
    $("filterSummary").textContent = extra ? t("moreFiltersOn")(extra) : t("moreFilters");
    renderTracks();
    renderSkills();
    renderJobs();
    renderSaved();
    if (!$("insights").hidden) renderInsights();
    writeHash();
  }

  function selectTab(id, write = true) {
    document.querySelectorAll('[role="tab"]').forEach((b) => {
      const on = b.getAttribute("aria-controls") === id;
      b.setAttribute("aria-selected", String(on));
      $(b.getAttribute("aria-controls")).hidden = !on;
    });
    if (!meta) return;
    if (id === "insights") renderInsights();
    if (id === "saved") renderSaved();
    if (write) writeHash();
  }

  function addSkill(name) {
    const hit = meta.skills.find((s) => s.toLowerCase() === String(name).trim().toLowerCase());
    if (!hit) return false;
    mySkills.add(hit); store.set("mySkills", [...mySkills]);
    if ($("sort").value === "new") $("sort").value = "match";
    update(true);
    return true;
  }

  function resetFilters() {
    ["role", "seniority", "workMode", "industry", "skill", "arabic", "q"].forEach((f) => { $(f).value = ""; });
    Object.keys(quick).forEach((k) => { quick[k] = k === "hideNat"; });
    syncToggles(); update();
  }

  async function share() {
    const url = location.href;
    try {
      if (navigator.share) { await navigator.share({ title: document.title, url }); return; }
      await navigator.clipboard.writeText(url);
    } catch { return; }
    const b = $("share"); b.textContent = t("copied");
    setTimeout(() => { b.textContent = t("share"); }, 2000);
  }

  function bind() {
    FIELDS.forEach((f) => $(f).addEventListener(f === "q" ? "input" : "change", () => update()));
    document.querySelectorAll(".toggle").forEach((b) => b.addEventListener("click", () => {
      quick[b.dataset.flag] = !quick[b.dataset.flag]; syncToggles(); update();
    }));
    $("more").addEventListener("click", () => { shown += PAGE; renderJobs(); });
    $("trackPills").addEventListener("click", (e) => {
      const b = e.target.closest("[data-track]");
      if (b) { $("role").value = b.dataset.track; update(); }
    });
    $("reset").addEventListener("click", resetFilters);
    $("share").addEventListener("click", share);
    document.querySelectorAll('[role="tab"]').forEach((b) => b.addEventListener("click", () => selectTab(b.getAttribute("aria-controls"))));
    $("lang").addEventListener("click", () => {
      lang = lang === "ar" ? "en" : "ar"; store.set("lang", lang); applyLanguage(); readHash(); update(true);
    });
    $("country").addEventListener("change", () => store.set("country", $("country").value));
    $("mySkillInput").addEventListener("change", (e) => { if (addSkill(e.target.value)) e.target.value = ""; });
    $("cvBtn").addEventListener("click", () => $("cvFile").click());
    $("cvFile").addEventListener("change", (e) => readCvFile(e.target.files[0]));
    $("cvPasteBtn").addEventListener("click", () => {
      const box = $("cvPasteBox"); box.hidden = !box.hidden; $("cvPasteBtn").setAttribute("aria-expanded", String(!box.hidden));
      if (!box.hidden) $("cvText").focus();
    });
    $("cvRead").addEventListener("click", () => useCvText($("cvText").value));
    // drop a CV file anywhere on the skills box
    const box = document.querySelector(".skillsbox");
    box.addEventListener("dragover", (e) => { e.preventDefault(); });
    box.addEventListener("drop", (e) => { e.preventDefault(); readCvFile(e.dataTransfer.files[0]); });
    $("mySkillInput").addEventListener("keydown", (e) => { if (e.key === "Enter" && addSkill(e.target.value)) e.target.value = ""; });
    // delegated clicks: remove/add skill chips, save buttons, location toggles
    document.addEventListener("click", (e) => {
      const el = e.target.closest("[data-skill],[data-add],[data-id],.locbtn");
      if (!el) return;
      if (el.dataset.skill) { mySkills.delete(el.dataset.skill); store.set("mySkills", [...mySkills]); update(true); }
      else if (el.dataset.add) addSkill(el.dataset.add);
      else if (el.dataset.id) {
        const id = el.dataset.id, j = jobs.find((x) => x.id === id);
        if (savedJobs[id]) delete savedJobs[id]; else if (j) savedJobs[id] = { t: j.t, c: j.c, u: j.u };
        store.set("saved", savedJobs);
        el.setAttribute("aria-pressed", String(!!savedJobs[id]));
        el.textContent = savedJobs[id] ? t("saved") : t("save");
        renderSaved();
      } else if (el.classList.contains("locbtn")) {
        const k = el.dataset.key;
        if (openLocs.has(k)) openLocs.delete(k); else openLocs.add(k);
        renderJobs();
      }
    });
    window.addEventListener("hashchange", () => { readHash(); update(); });
    window.addEventListener("resize", sizeHero);
  }

  async function start() {
    applyLanguage();
    try {
      const [m, j] = await Promise.all([
        fetch("data/meta.json").then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }),
        fetch("data/jobs.json").then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }),
      ]);
      meta = m; jobs = j;
    } catch {
      $("count").textContent = "–";
      $("jobList").innerHTML = "";
      $("empty").hidden = false;
      $("empty").textContent = t("loadError");
      return;
    }
    meta.countries.forEach((c) => { regionOf[c.name] = c.region; });
    meta.tracks.forEach((tr) => tr.roles.forEach((r) => { trackOfRole[r] = tr.name; }));
    jobs.forEach((j) => { j._text = [j.t, j.c, j.r, ...j.k.map((k) => meta.skills[k])].join(" ").toLowerCase(); });
    applyLanguage();
    const saved = store.get("country", "");
    if (saved && !location.hash) $("country").value = saved;
    readHash();
    bind();
    if (document.fonts) document.fonts.ready.then(sizeHero);
    update(true);
  }

  start();
})();
