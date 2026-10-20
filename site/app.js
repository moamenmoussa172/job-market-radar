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
      yourSkills: "Match jobs to your skills", addSkill: "Add a skill you have",
      yourSkillsHint: "Upload your CV or add skills. Every job gets a match score, and the best matches come first.",
      heroTitle: "Tech jobs you can actually get.",
      heroSub: "Fresh every morning from company career pages and job boards across Egypt, the Gulf, Europe and remote, filtered by where you live.",
      segRole: "I'm looking for", segKeywords: "Keywords", searchBtn: "Search", browseTracks: "Browse by track",
      filters: "Filters", filtersN: (n) => `Filters (${n})`, quickTitle: "Show only", close: "Close",
      showN: (n) => `Show ${n} jobs`, miniPh: "Search jobs  ( / )", clearAll: "Clear all", removeFilter: (x) => `Remove filter ${x}`,
      applyOn: "Apply on the company site", copyLink: "Copy link", linkCopied: "Link copied", posted: "Posted",
      haveTitle: "Skills you have", missTitle: "Skills to add", missHint: "Tap one you already know to add it to your skills.",
      matchCta: "Add your skills or upload your CV to see how well you match this job.", matchCtaBtn: "Add my skills",
      noSkills: "This posting doesn't list specific skills.", alsoIn: "Also posted in", similarTitle: "Similar jobs",
      fWorkMode: "Work mode", fSalary: "Salary", fLevel: "Level", fRole: "Role", fIndustry: "Industry", fSource: "Source",
      yourMatch: (a, b) => `You have ${a} of the ${b} skills this job asks for`, longOpenFull: "Open for a while (posted long ago)", matchOf: (a, b) => `You have ${a} of ${b} skills this job asks for`, skillsMatch: "match",
      suggest: "Often asked for these jobs:", removeSkill: (s) => `Remove ${s}`,
      qRemote: "Remote", qVisa: "Visa or relocation", qJunior: "Junior & intern", qPay: "Shows salary",
      qWeek: "Posted this week", qHideNat: "Hide nationals-only",
      moreFilters: "More filters", moreFiltersOn: (n) => `More filters (${n} on)`,
      search: "Search", searchPh: "Title, company or skill", seniority: "Seniority", workMode: "Work mode",
      industry: "Industry", skill: "Must-have skill", arabic: "Arabic", any: "Any", arabicReq: "Required",
      arabicNot: "Not required", reset: "Clear all",
      tabJobs: "Jobs", tabInsights: "Skills & pay", tabSaved: "Saved", tabAbout: "How it works", tabTrends: "Trends",
      weeklyReport: "Weekly report", reportCta: "Get this week's report card",
      weeklyTitle: "New jobs per week", risingTitle: "Skills on the rise", fallingTitle: "Skills cooling down",
      trackMovesTitle: "Which tracks are hiring faster", trackMovesHint: "New jobs in the last 4 weeks compared with the 4 weeks before.",
      daysOpenTitle: "How long jobs stay open", daysOpenHint: "Typical days from posting until the job is taken down. Short = apply early.",
      trendScopeAll: "Trends for all places", trendScopeOf: (c) => `Trends for ${c}`,
      trendScopeFallback: (c) => `There isn't enough data for ${c} yet, so these trends cover all places.`,
      weeklyHint: "Jobs we saw for the first time each week. The last bar is this week so far.",
      skillsHint: (d) => `Share of open jobs that ask for each skill: now compared with ${d} days ago. Tap a skill to see its jobs.`,
      statNewWeek: "new jobs last week", statVsPrev: (p) => `${p} vs the week before`, statTopTrack: "fastest-growing track",
      statTopSkill: "skill rising fastest", statDaysOpen: "days a job typically stays open",
      trendsSoon: "Trends need a few weeks of data. New numbers arrive every morning, so check back soon.",
      pts: (v) => `${v > 0 ? "+" : ""}${v} pts`, soFar: "so far", newTrack: "new",
      sortBy: "Sort by", sortNew: "Newest", sortMatch: "Best match for my skills", sortPay: "Highest pay",
      summary: (jobs, companies) => `<b>${jobs}</b> jobs at <b>${companies}</b> companies`,
      remote: "Remote", remoteWorld: "Remote, worldwide", visaTag: "Visa / relocation", natTag: "Nationals only",
      arTag: "Arabic required", longOpen: "Open for a while", today: "Today", yesterday: "Yesterday",
      daysAgo: (n) => `${n} days ago`, moreLocs: (n) => `+${n} more ${n === 1 ? "location" : "locations"}`,
      hideLocs: "Hide locations", save: "Save", saved: "Saved", youHave: (a, b) => `You have ${a} of ${b} skills`,
      more: (n) => `Show ${n} more`,
      emptyJobs: "No jobs match all of these filters.", emptyFix: "Clear the extra filters",
      emptyCountry: "Few jobs are open to this country with these filters. Try \"any tech\" or turn off a quick filter.",
      savedHint: "Save jobs and tick the ones you applied to. Everything stays on this device, nothing is sent anywhere.",
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
      cvShowRole: (r) => `Show ${r} jobs`, showNat: "Showing nationals-only", cvShowBest: "Show my best matches", cvClear: "Forget my CV skills",
      browseJobs: "Jobs by country", browseJobsAll: "Browse tech jobs by country and role",
      navCompanies: "Companies", navJuniors: "Juniors", navSalaries: "Salaries", feedback: "Send feedback",
      reportClosed: "Job closed or wrong? Tell us", reported: "Thanks! We hid this job for you and will check it.",
      nlTitle: "Radarak Weekly", nlText: "Every Sunday: the week's new tech jobs in Egypt, the Gulf and remote, in one short email.",
      nlEmail: "Your email", nlEmailPh: "you@example.com", nlBtn: "Subscribe", nlThanks: "Check your inbox to confirm.",
      learnTitle: "What to learn next", learnNow: (m) => `You match <b>${m}</b> jobs right now.`,
      learnHint: "Each step counts the extra jobs you'd match (60%+ of their skills) after learning it and the ones above it.",
      learnJobs: (n) => `+${n} jobs`, learnTotal: (a, b) => `Learn all ${a === 1 ? "of it" : "three"}: <b>${b}</b> jobs you match`,
      learnKnow: "I know it", learnSee: "See jobs", learnNone: "You already match most jobs here, or they list too few skills to say.",
      applied: "Applied", markApplied: "Mark as applied", appliedOn: (d) => `Applied ${d}`, savedOn: (d) => `Saved ${d}`,
      savedAll: "All", savedTodo: "To apply", savedDone: "Applied", closedTag: "No longer listed", removeSaved: "Remove",
      savedNone: "Nothing here yet.",
      newTag: "New", newBanner: (n, d) => `<b>${n}</b> new ${n === 1 ? "job" : "jobs"} since your last visit (${d})`,
      newShow: "Show only new", newAll: "Show all jobs", qNew: "New since last visit",
      shareWa: "WhatsApp", shareMore: "Share", shareText: (ti, c) => `${ti}${c ? " at " + c : ""} (found on Radarak)`,
      installApp: "Install app", iosHint: "To install Radarak: tap the Share button in Safari, then “Add to Home Screen”.", gotIt: "Got it",
    },
    ar: {
      brand: "رادارك", code: "الكود المصدري", skip: "انتقل للوظايف",
      browseTracks: "تصفّح حسب المجال", allTracks: "كل التك",
      ask1: "أنا عايش في", ask2: "وبدوّر على وظايف", ask3: "", country: "الدولة", role: "الوظيفة",
      anyCountry: "أي دولة", anyRole: "أي مجال تقني", allOf: (x) => `${x} (كل الوظايف)`,
      countLabel: "وظيفة تقدر تقدّم عليها", countAll: "وظيفة تقنية متاحة", share: "شارك البحث ده", copied: "اتنسخ اللينك",
      updated: (d) => `آخر تحديث ${d}. وظايف جديدة بتتضاف كل يوم الصبح.`,
      yourSkills: "شوف الوظايف المناسبة لمهاراتك", addSkill: "ضيف مهارة عندك",
      yourSkillsHint: "ارفع الـ CV أو ضيف مهاراتك. كل وظيفة هتاخد نسبة تطابق، والأنسب هتظهر الأول.",
      heroTitle: "وظايف تك تقدر توصلها فعلًا.",
      heroSub: "بتتحدّث كل يوم الصبح من صفحات توظيف الشركات ومواقع الوظايف في مصر والخليج وأوروبا والريموت، ومفلترة حسب البلد اللي إنت فيها.",
      segRole: "بدوّر على", segKeywords: "كلمات بحث", searchBtn: "دوّر", browseTracks: "تصفّح حسب المجال",
      filters: "الفلاتر", filtersN: (n) => `الفلاتر (${n})`, quickTitle: "اعرض بس", close: "اقفل",
      showN: (n) => `اعرض ${n} وظيفة`, miniPh: "دوّر على وظيفة  ( / )", clearAll: "امسح الكل", removeFilter: (x) => `شيل فلتر ${x}`,
      applyOn: "قدّم على موقع الشركة", copyLink: "انسخ اللينك", linkCopied: "اتنسخ اللينك", posted: "اتنشرت",
      haveTitle: "مهارات عندك", missTitle: "مهارات تضيفها", missHint: "دوس على أي مهارة بتعرفها عشان تضيفها لمهاراتك.",
      matchCta: "ضيف مهاراتك أو ارفع الـ CV عشان تشوف قد إيه الوظيفة دي مناسبة ليك.", matchCtaBtn: "ضيف مهاراتي",
      noSkills: "الإعلان ده مش مكتوب فيه مهارات محددة.", alsoIn: "منشورة كمان في", similarTitle: "وظايف شبهها",
      fWorkMode: "نوع الشغل", fSalary: "المرتب", fLevel: "المستوى", fRole: "الوظيفة", fIndustry: "المجال", fSource: "المصدر",
      yourMatch: (a, b) => `عندك ${a} من ${b} مهارات الوظيفة دي طالباها`, longOpenFull: "مفتوحة من زمان (اتنشرت من فترة طويلة)", matchOf: (a, b) => `عندك ${a} من ${b} مهارات الوظيفة دي طالباها`, skillsMatch: "تطابق",
      suggest: "مطلوبة كتير في الوظايف دي:", removeSkill: (s) => `شيل ${s}`,
      qRemote: "ريموت", qVisa: "فيزا أو انتقال", qJunior: "جونيور وتدريب", qPay: "فيها مرتب",
      qWeek: "اتنشرت الأسبوع ده", qHideNat: "اخفي اللي للمواطنين بس",
      moreFilters: "فلاتر أكتر", moreFiltersOn: (n) => `فلاتر أكتر (${n} شغالين)`,
      search: "بحث", searchPh: "وظيفة أو شركة أو مهارة", seniority: "المستوى", workMode: "نوع العمل",
      industry: "المجال", skill: "مهارة لازم تكون مطلوبة", arabic: "العربي", any: "الكل", arabicReq: "مطلوب",
      arabicNot: "مش مطلوب", reset: "امسح الكل",
      tabJobs: "الوظايف", tabInsights: "المهارات والمرتبات", tabSaved: "المحفوظة", tabAbout: "إزاي بيشتغل", tabTrends: "الترندات",
      weeklyReport: "التقرير الأسبوعي", reportCta: "خد كارت تقرير الأسبوع ده",
      weeklyTitle: "الوظايف الجديدة كل أسبوع", risingTitle: "مهارات طالعة", fallingTitle: "مهارات بتهدى",
      trackMovesTitle: "أنهي مجالات بتوظّف أسرع", trackMovesHint: "الوظايف الجديدة في آخر 4 أسابيع مقارنة بالـ 4 اللي قبلهم.",
      daysOpenTitle: "الوظيفة بتفضل مفتوحة قد إيه", daysOpenHint: "متوسط الأيام من نشر الوظيفة لحد ما تتقفل. لو قليل يبقى قدّم بدري.",
      trendScopeAll: "ترندات كل الأماكن", trendScopeOf: (c) => `ترندات ${c}`,
      trendScopeFallback: (c) => `لسه مفيش بيانات كفاية عن ${c}، فالترندات دي لكل الأماكن.`,
      weeklyHint: "الوظايف اللي شفناها لأول مرة كل أسبوع. آخر عمود هو الأسبوع ده لحد دلوقتي.",
      skillsHint: (d) => `نسبة الوظايف المفتوحة اللي طالبة كل مهارة: دلوقتي مقارنة بـ ${d} يوم فاتوا. دوس على مهارة تشوف وظايفها.`,
      statNewWeek: "وظيفة جديدة الأسبوع اللي فات", statVsPrev: (p) => `${p} عن الأسبوع اللي قبله`, statTopTrack: "أسرع مجال بيكبر",
      statTopSkill: "أسرع مهارة طالعة", statDaysOpen: "يوم بتفضل الوظيفة مفتوحة عادةً",
      trendsSoon: "الترندات محتاجة كام أسبوع بيانات. أرقام جديدة بتيجي كل يوم الصبح، فارجع تاني قريب.",
      pts: (v) => `${v > 0 ? "+" : ""}${v} نقطة`, soFar: "لحد دلوقتي", newTrack: "جديد",
      sortBy: "رتّب حسب", sortNew: "الأحدث", sortMatch: "الأنسب لمهاراتي", sortPay: "الأعلى مرتب",
      summary: (jobs, companies) => `<b>${jobs}</b> وظيفة في <b>${companies}</b> شركة`,
      remote: "ريموت", remoteWorld: "ريموت من أي مكان", visaTag: "فيزا / انتقال", natTag: "للمواطنين بس",
      arTag: "العربي مطلوب", longOpen: "مفتوحة من فترة", today: "النهارده", yesterday: "امبارح",
      daysAgo: (n) => `من ${n} يوم`, moreLocs: (n) => `+${n} أماكن تانية`,
      hideLocs: "اخفي الأماكن", save: "احفظ", saved: "محفوظة", youHave: (a, b) => `عندك ${a} من ${b} مهارات`,
      more: (n) => `اعرض ${n} كمان`,
      emptyJobs: "مفيش وظايف بكل الفلاتر دي.", emptyFix: "امسح الفلاتر الزيادة",
      emptyCountry: "وظايف قليلة مفتوحة للبلد دي بالفلاتر دي. جرّب \"أي مجال تقني\" أو اقفل فلتر سريع.",
      savedHint: "احفظ الوظايف وعلّم على اللي قدّمت عليها. كل ده بيفضل على جهازك ومش بيتبعت لأي مكان.",
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
      cvShowRole: (r) => `اعرض وظايف ${r}`, showNat: "بيعرض وظايف المواطنين فقط", cvShowBest: "اعرض أنسب وظايف ليا", cvClear: "امسح مهارات الـ CV",
      browseJobs: "الوظايف حسب البلد", browseJobsAll: "تصفّح وظايف التك حسب البلد والوظيفة",
      navCompanies: "الشركات", navJuniors: "الجونيور", navSalaries: "المرتبات", feedback: "ابعتلنا رأيك",
      reportClosed: "الوظيفة اتقفلت أو فيها غلط؟ قولنا", reported: "شكرًا! خبّينا الوظيفة دي عندك وهنراجعها.",
      nlTitle: "نشرة رادارك الأسبوعية", nlText: "كل يوم حد: وظايف التك الجديدة في مصر والخليج والريموت، في إيميل واحد قصير.",
      nlEmail: "الإيميل بتاعك", nlEmailPh: "you@example.com", nlBtn: "اشترك", nlThanks: "شوف الإيميل بتاعك عشان تأكد الاشتراك.",
      learnTitle: "تتعلم إيه بعد كده", learnNow: (m) => `إنت مناسب لـ <b>${m}</b> وظيفة دلوقتي.`,
      learnHint: "كل خطوة بتحسب الوظايف الزيادة اللي هتبقى مناسب لها (60%+ من مهاراتها) لو اتعلمت المهارة دي واللي فوقها.",
      learnJobs: (n) => `+${n} وظيفة`, learnTotal: (a, b) => `لو اتعلمتهم ${a === 1 ? "" : "التلاتة"}: <b>${b}</b> وظيفة مناسبة ليك`,
      learnKnow: "بعرفها", learnSee: "شوف الوظايف", learnNone: "إنت مناسب لأغلب الوظايف هنا، أو مهاراتها المكتوبة قليلة.",
      applied: "قدّمت", markApplied: "قدّمت عليها", appliedOn: (d) => `قدّمت ${d}`, savedOn: (d) => `اتحفظت ${d}`,
      savedAll: "الكل", savedTodo: "لسه هقدّم", savedDone: "قدّمت", closedTag: "مش معروضة دلوقتي", removeSaved: "شيلها",
      savedNone: "مفيش حاجة هنا لسه.",
      newTag: "جديدة", newBanner: (n, d) => `<b>${n}</b> وظيفة جديدة من آخر زيارة ليك (${d})`,
      newShow: "اعرض الجديد بس", newAll: "اعرض كل الوظايف", qNew: "جديدة من آخر زيارة",
      shareWa: "واتساب", shareMore: "شارك", shareText: (ti, c) => `${ti}${c ? " في " + c : ""} (لقيتها على رادارك)`,
      installApp: "نزّل التطبيق", iosHint: "عشان تنزّل رادارك: دوس على زرار المشاركة في Safari، وبعدين \"Add to Home Screen\".", gotIt: "تمام",
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
      <p>Company career boards (Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Recruitee, Personio, and the Workday and SuccessFactors career sites of large employers) and job APIs. Every job links to its original posting, where you apply. Some jobs carry their source's credit (for example, Jobs by Adzuna).</p>
      <p>The data is collected automatically and can miss jobs or contain mistakes. Saved jobs and your skills stay in your browser. The site counts visits and clicks anonymously (GoatCounter, no cookies, nothing that identifies you) to know how many people it helps. The project is open source.</p>`,
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
      <p>صفحات التوظيف بتاعة الشركات (Greenhouse و Lever و Ashby و SmartRecruiters و Workable و Recruitee و Personio، وصفحات Workday و SuccessFactors بتاعة الشركات الكبيرة) ومواقع وظايف. كل وظيفة فيها لينك للإعلان الأصلي، والتقديم بيكون هناك.</p>
      <p>البيانات بتتجمع أوتوماتيك وممكن يفوتها وظايف أو يكون فيها أخطاء. الوظايف المحفوظة ومهاراتك بتفضل في المتصفح بتاعك. الموقع بيعدّ الزيارات والضغطات من غير ما يعرف إنت مين (GoatCounter، من غير كوكيز) عشان نعرف بنساعد كام واحد. المشروع مفتوح المصدر.</p>`,
  };

  // ------------------------------------------------------------------ state
  const $ = (id) => document.getElementById(id);
  const store = {
    get(k, d) { try { const v = localStorage.getItem("jr_" + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem("jr_" + k, JSON.stringify(v)); } catch { /* storage unavailable */ } },
  };
  let lang = store.get("lang", (navigator.language || "").startsWith("ar") ? "ar" : "en");
  let trends = null;
  let meta = null, jobs = [], regionOf = {}, shown = PAGE, groups = [], current = [];
  let mySkills = new Set(store.get("mySkills", []));
  let savedJobs = store.get("saved", {});               // id -> {t, c, l, u, sv: saved day, a: applied day}
  let savedView = "all";                                // Saved tab: all | todo | done
  const quick = { remote: false, visa: false, junior: false, pay: false, week: false, hideNat: true, fresh: false };
  const NOT_IN_LINKS = new Set(["fresh"]);              // "new for me" depends on the visitor, so shared links don't carry it
  let newSince = null;                                  // day of the data the visitor saw on their previous visit
  const hiddenJobs = new Set(store.get("hidden", []));  // jobs this visitor reported as closed
  const isNew = (j) => !!newSince && (j.fs || j.p) > newSince;
  const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
  const shortDate = (iso) => new Date(iso + "T12:00:00Z").toLocaleDateString(lang === "ar" ? "ar-EG" : "en-GB", { day: "numeric", month: "short" });
  const openLocs = new Set();
  const t = (k) => T[lang][k] ?? T.en[k] ?? k;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (n) => Number(n).toLocaleString("en-US");
  // anonymous usage counts (GoatCounter: no cookies, no personal data). Does nothing if analytics isn't set up.
  function track(name) {
    try { if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path: name, title: name, event: true }); } catch { /* never break the page */ }
  }
  const weekAgo = new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10);
  // every track has its own colour (style.css: --t-<key>), used on job rows, chips, bars and the radar
  const TRACK_KEY = {
    "Data & Analytics": "data", "AI & Machine Learning": "ai", "Software Engineering": "sw", "Mobile Development": "mob",
    "QA & Testing": "qa", "UI/UX Design": "ux", "DevOps & Cloud": "ops", "Security": "sec", "ERP & CRM": "erp",
    "Networks & Telecom": "net", "Product & Delivery": "prod", "IT & Support": "it",
    "Embedded & Chip Design": "emb",
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

  function sizeHero() { /* the search console has fixed-width fields */ }

  function applyLanguage() {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
    document.querySelectorAll("[data-i18n-aria]").forEach((el) => el.setAttribute("aria-label", t(el.dataset.i18nAria)));
    const btn = $("lang");
    btn.textContent = lang === "ar" ? "English" : "العربية";
    btn.lang = lang === "ar" ? "en" : "ar";
    $("aboutText").innerHTML = ABOUT[lang];
    document.querySelectorAll(".langpath").forEach((a) => { a.href = (lang === "ar" ? "ar/" : "") + a.dataset.path; });
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
    Object.keys(quick).forEach((k) => { if (h.has(k) && !NOT_IN_LINKS.has(k)) quick[k] = h.get(k) === "1"; });
    syncToggles();
    if (h.has("tab")) selectTab(h.get("tab"), false);
    const jid = h.get("job");
    if (jid && jid !== currentJob && meta) openJob(jid, null, false);
    else if (!jid && currentJob) closeJob(false);
  }
  function writeHash() {
    const h = new URLSearchParams();
    FIELDS.forEach((f) => { if ($(f).value && !(f === "sort" && $(f).value === "new")) h.set(f, $(f).value); });
    Object.entries(quick).forEach(([k, v]) => { if (v !== (k === "hideNat") && !NOT_IN_LINKS.has(k)) h.set(k, v ? "1" : "0"); });
    const tab = document.querySelector('[role="tab"][aria-selected="true"]').getAttribute("aria-controls");
    if (tab !== "jobs") h.set("tab", tab);
    if (currentJob) h.set("job", currentJob);
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
      if (quick.fresh && !isNew(j)) return false;
      if (hiddenJobs.has(j.id)) return false;
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

  const BOOKMARK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h12v18l-6-4.5L6 21z"/></svg>';
  const CHECK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>';
  const WA_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path class="wafill" d="M12 2.2a9.7 9.7 0 0 0-8.4 14.6L2.3 21.8l5.1-1.3A9.7 9.7 0 1 0 12 2.2Zm0 17.7a8 8 0 0 1-4.1-1.1l-.3-.2-3 .8.8-2.9-.2-.3A8 8 0 1 1 12 19.9Zm4.4-6c-.2-.1-1.4-.7-1.7-.8-.2-.1-.4-.1-.5.1l-.8 1c-.1.2-.3.2-.5.1a6.6 6.6 0 0 1-3.3-2.9c-.2-.4.2-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.5-.4h-.5a.9.9 0 0 0-.7.3 2.8 2.8 0 0 0-.9 2.1 4.9 4.9 0 0 0 1 2.6 11.2 11.2 0 0 0 4.3 3.8c1.6.7 2.2.7 3 .6a2.6 2.6 0 0 0 1.7-1.2 2.1 2.1 0 0 0 .2-1.2c-.1-.1-.2-.2-.5-.3Z"/></svg>';
  // a link that opens this job's details on Radarak (no filters, so it works for whoever receives it)
  const jobLink = (j) => location.origin + location.pathname + "#job=" + encodeURIComponent(j.id);
  const waLink = (j) => "https://wa.me/?text=" + encodeURIComponent(t("shareText")(j.t, j.c) + "\n" + jobLink(j));
  function matchRing(have, total) {
    const pct = Math.round((100 * have) / total), r = 17, c = 2 * Math.PI * r;
    const tone = pct >= 60 ? "hi" : pct >= 30 ? "mid" : "lo";
    return `<span class="ring ${tone}" role="img" aria-label="${esc(t("matchOf")(have, total))}" title="${esc(t("matchOf")(have, total))}">
      <svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="${r}"/>${pct ? `<circle class="val" cx="20" cy="20" r="${r}"
        stroke-dasharray="${((c * pct) / 100).toFixed(1)} ${c.toFixed(1)}"/>` : ""}</svg><b>${pct}%</b></span>`;
  }

  function jobRow(g) {
    const j = g.job, f = g.flags, mine = mySkillIdx();
    const others = g.all.length - 1;
    const sv = savedJobs[j.id];
    const facts = [
      g.all.some(isNew) ? `<span class="fact new">${t("newTag")}</span>` : "",
      sv && sv.a && !String(g.key).startsWith("saved:") ? `<span class="fact applied">✓ ${t("applied")}</span>` : "",
      g.pay ? `<span class="fact pay">${payText(g.pay)}</span>` : "",
      j.w === "Remote" ? `<span class="fact remote">${j.ww ? t("remoteWorld") : t("remote")}</span>` : `<span class="fact">${esc(j.w)}</span>`,
      f & FLAG.visa ? `<span class="fact visa">${t("visaTag")}</span>` : "",
      f & FLAG.nationals ? `<span class="fact nat">${t("natTag")}</span>` : "",
      f & FLAG.arabic ? `<span class="fact ar">${t("arTag")}</span>` : "",
      j.s && j.s !== "Not stated" ? `<span class="fact">${esc(j.s)}</span>` : "",
      `<span class="fact role">${esc(j.r)}</span>`,
    ].join("");
    const ks = [...j.k].sort((a, b) => (mine.has(b) ? 1 : 0) - (mine.has(a) ? 1 : 0));
    const skills = ks.slice(0, SKILLS_SHOWN).map((k) => `<span class="sk${mine.has(k) ? " have" : ""}">${esc(meta.skills[k])}</span>`).join("")
      + (ks.length > SKILLS_SHOWN ? `<span class="sk skmore">+${ks.length - SKILLS_SHOWN}</span>` : "");
    const isSaved = !!savedJobs[j.id];
    const locsOpen = openLocs.has(g.key);
    const initial = (j.c || j.t || "?").trim().charAt(0).toUpperCase();
    return `<li class="job" style="${tc(j.tr)}" data-jid="${esc(j.id)}">
      <span class="avatar" aria-hidden="true">${esc(initial)}</span>
      <div class="jmain">
        <h3><a href="${esc(j.u)}" target="_blank" rel="noopener nofollow">${esc(j.t)}</a></h3>
        <p class="where"><b>${esc(j.c || "")}</b><span>${esc(j.l || "")}</span>${others > 0
          ? `<button type="button" class="locbtn" data-key="${esc(g.key)}" aria-expanded="${locsOpen}">${locsOpen ? t("hideLocs") : t("moreLocs")(others)}</button>` : ""}</p>
        <div class="facts">${facts}</div>
        ${j.k.length ? `<div class="skills">${skills}</div>` : ""}
        ${j.by ? `<p class="credit">${esc(j.by)}</p>` : ""}
        ${locsOpen ? `<ul class="locs">${g.all.slice(1).map((x) => `<li><a href="${esc(x.u)}" target="_blank" rel="noopener nofollow">${esc(x.l || x.t)}</a></li>`).join("")}</ul>` : ""}
      </div>
      <div class="jside">
        ${mine.size && j.k.length ? matchRing(g.have, j.k.length) : ""}
        <span class="age">${f & FLAG.longOpen ? t("longOpen") : ago(j.p)}</span>
        <div class="rowbtns">
          <a class="wa" href="${esc(waLink(j))}" target="_blank" rel="noopener" data-share="${esc(j.id)}" aria-label="${esc(t("shareWa"))}" title="${esc(t("shareWa"))}">${WA_ICON}</a>
          <button type="button" class="save" data-id="${esc(j.id)}" aria-pressed="${isSaved}">${BOOKMARK}<span>${isSaved ? t("saved") : t("save")}</span></button>
        </div>
      </div>
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
    const open = new Map(jobs.map((j) => [j.id, j]));
    const ids = Object.keys(savedJobs);
    // saved jobs that closed are dropped, unless you applied: those stay as your application history
    const keep = ids.filter((id) => open.has(id) || savedJobs[id].a);
    const todo = keep.filter((id) => !savedJobs[id].a && open.has(id)), done = keep.filter((id) => savedJobs[id].a);
    $("savedCount").hidden = !todo.length;
    $("savedCount").textContent = todo.length;
    if ($("saved").hidden) return;
    $("savedTabs").innerHTML = [["all", t("savedAll"), keep.length], ["todo", t("savedTodo"), todo.length], ["done", t("savedDone"), done.length]]
      .map(([v, label, n]) => `<button type="button" class="stab${savedView === v ? " on" : ""}" data-saved-view="${v}" aria-pressed="${savedView === v}">${esc(label)} <span class="n">${num(n)}</span></button>`).join("");
    const list = savedView === "todo" ? todo : savedView === "done" ? done : keep;
    const byDay = (id) => savedJobs[id].a || savedJobs[id].sv || "";
    list.sort((a, b) => (byDay(a) < byDay(b) ? 1 : -1));
    $("savedList").innerHTML = list.map((id) => {
      const s = savedJobs[id], j = open.get(id);
      const status = `<p class="savedmeta">${s.a ? `<span class="fact applied">✓ ${esc(t("appliedOn")(shortDate(s.a)))}</span>` : s.sv ? esc(t("savedOn")(shortDate(s.sv))) : ""}
        <button type="button" class="applybtn" data-applied="${esc(id)}" aria-pressed="${!!s.a}">${CHECK}<span>${s.a ? t("applied") : t("markApplied")}</span></button></p>`;
      if (j) { const row = jobRow({ key: "saved:" + id, job: j, all: [j], pay: j.$ || null, flags: j.f || 0, have: 0, match: -1 }), at = row.lastIndexOf("</li>");
        return row.slice(0, at) + status + row.slice(at); }
      return `<li class="job closed"><span class="avatar" aria-hidden="true">${esc((s.c || s.t || "?").charAt(0).toUpperCase())}</span>
        <div class="jmain"><h3>${s.u ? `<a class="closedlink" href="${esc(s.u)}" target="_blank" rel="noopener nofollow">${esc(s.t)}</a>` : esc(s.t)}</h3>
          <p class="where"><b>${esc(s.c || "")}</b><span>${esc(s.l || "")}</span></p><div class="facts"><span class="fact">${t("closedTag")}</span></div></div>
        <div class="jside"><button type="button" class="linkbtn" data-unsave="${esc(id)}">${t("removeSaved")}</button></div>${status}</li>`;
    }).join("");
    $("savedEmpty").hidden = list.length > 0;
    $("savedEmpty").textContent = keep.length ? t("savedNone") : t("savedEmpty");
  }
  function toggleSaved(id) {
    const j = jobs.find((x) => x.id === id);
    if (savedJobs[id]) delete savedJobs[id];
    else if (j) { savedJobs[id] = { t: j.t, c: j.c, l: j.l, u: j.u, sv: today() }; track("save-job"); }
    store.set("saved", savedJobs);
  }
  function toggleApplied(id) {
    const j = jobs.find((x) => x.id === id);
    if (!savedJobs[id]) { if (!j) return; savedJobs[id] = { t: j.t, c: j.c, l: j.l, u: j.u, sv: today() }; }
    if (savedJobs[id].a) delete savedJobs[id].a; else { savedJobs[id].a = today(); track("applied"); }
    store.set("saved", savedJobs);
  }

  // ------------------------------------------------------------------ "what to learn next": the 3 skills that open the most jobs
  function learnPlan() {
    const mine = mySkillIdx();
    if (!mine.size) return null;
    const seen = new Set(), pool = [];
    for (const j of current) {          // count each job once, the way the list shows it
      if (j.k.length < 2) continue;
      const key = j.t.toLowerCase() + "|" + (j.c || "").toLowerCase();
      if (!seen.has(key)) { seen.add(key); pool.push(j); }
    }
    const isMatch = (j, have) => j.k.filter((k) => have.has(k)).length / j.k.length >= MATCH;
    const have = new Set(mine);
    let matched = pool.filter((j) => isMatch(j, have)).length;
    const start = matched, steps = [];
    for (let step = 0; step < 3; step++) {
      const gain = new Map();
      for (const j of pool) {
        const known = j.k.filter((k) => have.has(k)).length;
        if (known / j.k.length >= MATCH || (known + 1) / j.k.length < MATCH) continue;
        j.k.forEach((k) => { if (!have.has(k)) gain.set(k, (gain.get(k) || 0) + 1); });
      }
      const best = [...gain.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0];
      if (!best || best[1] < 2) break;
      have.add(best[0]); matched += best[1];
      steps.push({ skill: meta.skills[best[0]], gain: best[1] });
    }
    return { start, end: matched, steps };
  }
  function renderLearn() {
    const box = $("learnNext"), plan = learnPlan();
    box.hidden = !plan;
    if (!plan) return;
    const top = Math.max(1, ...plan.steps.map((s) => s.gain));
    box.innerHTML = `<div class="learnhead"><h3>🎯 ${t("learnTitle")}</h3><p>${t("learnNow")(num(plan.start))}</p></div>
      ${plan.steps.length ? `<ol class="learnsteps">${plan.steps.map((s, i) => `<li>
          <span class="lnum">${i + 1}</span>
          <div class="lmain"><b>${esc(s.skill)}</b><span class="lbar"><i style="width:${Math.round((100 * s.gain) / top)}%"></i></span></div>
          <span class="lgain">${t("learnJobs")(num(s.gain))}</span>
          <span class="lbtns"><button type="button" class="linkbtn" data-learn-see="${esc(s.skill)}">${t("learnSee")}</button>
            <button type="button" class="chip add" data-add="${esc(s.skill)}">+ ${t("learnKnow")}</button></span></li>`).join("")}</ol>
        <p class="learntotal">${t("learnTotal")(plan.steps.length, `${num(plan.start)} → ${num(plan.end)}`)}
          <span class="up">+${plan.start ? Math.round((100 * (plan.end - plan.start)) / plan.start) + "%" : num(plan.end - plan.start)}</span></p>
        <p class="hint">${t("learnHint")}</p>` : `<p class="hint">${t("learnNone")}</p>`}`;
  }

  // ------------------------------------------------------------------ "new since your last visit"
  function initVisit() {
    const day = (meta.generated_at || "").slice(0, 10);
    const v = store.get("visit", null);
    if (!v) store.set("visit", { data: day, prev: null });
    else if (v.data !== day) { newSince = v.data; store.set("visit", { data: day, prev: v.data }); }
    else newSince = v.prev;
  }
  function renderNewBanner() {
    const el = $("newBanner");
    if (!newSince) { el.hidden = true; return; }
    const was = quick.fresh;
    quick.fresh = false;
    const n = was ? groups.length : groups.filter((g) => g.all.some(isNew)).length;
    quick.fresh = was;
    el.hidden = !n && !was;
    if (el.hidden) return;
    el.innerHTML = `<span class="spark" aria-hidden="true">✨</span><p>${t("newBanner")(num(n), shortDate(newSince))}</p>
      <button type="button" class="${was ? "linkbtn" : "primary sm"}" id="newToggle">${was ? t("newAll") : t("newShow")}</button>`;
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
    // "Azure DevOps" is a tool (boards, pipelines) that testers and developers list too, not the DevOps role
    [/(?<!azure\s)\bdevops( ?\/ ?\w+)? (engineer|specialist|lead|architect)|\bplatform engineer/gi, "DevOps / Platform Engineer"], [/\bsite reliability|\bsre\b/gi, "Site Reliability Engineer"],
    [/\bcloud (engineer|architect)/gi, "Cloud / Infrastructure Engineer"],
    [/\b(qa|test automation|automation test(ing)?|sdet|quality assurance)( \/ test automation)? (engineer|analyst|tester|specialist)|\bsdet\b/gi, "QA Automation Engineer"],
    [/\b(software |manual |qa |qc )?test(ing)? (engineer|analyst|specialist)|\b(software |manual )?tester\b/gi, "QA / Test Engineer"],
    [/\b(ux|ui|product) designer|\bux\/ui|\bui\/ux/gi, "UX / Product Designer"],
    [/\b(cyber ?)?security (engineer|architect|specialist)|\bappsec\b|\bdevsecops\b/gi, "Security Engineer"],
    [/\bsoc (analyst|engineer)|\bsecurity analyst|incident response|threat hunt/gi, "SOC / Security Analyst"],
    [/\bpenetration test(er|ing)|\bpentest(er|ing)?\b|\bred team|ethical hack/gi, "Penetration Tester / Red Team"],
    [/\bgrc\b|\bit audit(or)?\b|iso ?27001 (lead )?(auditor|implementer)/gi, "GRC / IT Audit"],
    [/\b(iam|identity (and|&) access)( management)? (engineer|analyst|specialist|consultant)/gi, "Identity & Access (IAM)"],
    [/\bembedded (software )?(engineer|developer)|\bfirmware (engineer|developer)/gi, "Embedded / Firmware Engineer"],
    [/\bautosar\b|automotive (software|embedded)/gi, "Automotive Software Engineer"],
    [/\b(asic|fpga|rtl|vlsi|physical design) (design )?(engineer|developer)/gi, "ASIC / FPGA Design Engineer"],
    [/\b(design )?verification engineer|\buvm\b/gi, "Design Verification Engineer"],
    [/\b(pre-?sales|sales) engineer|\bsolutions? consultant/gi, "Pre-sales / Sales Engineer"],
    [/\b(solutions?|software|enterprise) architect/gi, "Software / Solutions Architect"],
    [/\b(llm|genai|generative ai) engineer|\bprompt engineer/gi, "LLM / GenAI Engineer"],
    [/\bcomputer vision (engineer|scientist|researcher)/gi, "Computer Vision Engineer"],
    [/\b(nlp|speech) (engineer|scientist|researcher)/gi, "NLP / Speech Engineer"],
    [/\bdata architect/gi, "Data Architect"], [/\bperformance test(ing)? (engineer|specialist)/gi, "Performance Test Engineer"],
    [/\bintegration (engineer|developer)|\bmulesoft (engineer|developer)/gi, "Integration / API Engineer"],
    [/\b(sap|abap|salesforce|dynamics 365|oracle ebs) (consultant|developer)/gi, "ERP / CRM Consultant"],
    [/\bnetwork engineer|\bnoc engineer/gi, "Network Engineer"], [/\bproduct (manager|owner)/gi, "Product Manager / Owner"],
    [/\bsoftware (engineer|developer)/gi, "Software Engineer"],
  ];
  function guessRole(text) {
    const known = new Set(meta.tracks.flatMap((t) => t.roles));
    const top = text.slice(0, 300);  // the title under the name says the most
    const scores = new Map();
    for (const [re, role] of ROLE_HINTS) {
      if (!known.has(role)) continue;
      const n = (text.match(re) || []).length + 3 * (top.match(re) || []).length;
      if (n) scores.set(role, (scores.get(role) || 0) + n);
    }
    // a tester who also automates is an automation tester
    if (scores.has("QA Automation Engineer") && scores.has("QA / Test Engineer")) {
      scores.set("QA Automation Engineer", scores.get("QA Automation Engineer") + scores.get("QA / Test Engineer"));
      scores.delete("QA / Test Engineer");
    }
    let best = null, score = 0;
    for (const [role, n] of scores) if (n > score) { best = role; score = n; }
    return best;
  }

  function cvStatus(msg, err) { const el = $("cvStatus"); el.textContent = msg || ""; el.classList.toggle("err", !!err); }

  function useCvText(text) {
    if (!text || text.trim().length < 80) { cvStatus(t("cvNoText"), true); return; }
    const skills = findSkills(text);
    if (!skills.length) { cvStatus(t("cvNoSkills"), true); return; }
    cvStatus("");
    const years = findYears(text), role = guessRole(text);
    track("cv-read");
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
      <button type="button" class="linkbtn learnjump" id="learnJump">${t("learnTitle")} ↓</button>
      <div class="actions">
        ${role ? `<button type="button" class="cvbtn" id="cvRoleBtn">${esc(t("cvShowRole")(role))}</button>` : ""}
        <button type="button" class="sharebtn" id="cvBestBtn">${t("cvShowBest")}</button>
        <button type="button" class="linkbtn" id="cvClearBtn">${t("cvClear")}</button>
      </div>`;
    if (role) $("cvRoleBtn").addEventListener("click", () => { track("cv-show-role"); $("role").value = "role:" + role; update(); goToJobs(); });
    $("cvBestBtn").addEventListener("click", goToJobs);
    $("learnJump").addEventListener("click", () => $("learnNext").scrollIntoView({ behavior: "smooth", block: "center" }));
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

  // ------------------------------------------------------------------ trends (data/trends.json, from the trend marts)
  const sumRange = (arr, from, to) => arr.slice(Math.max(0, from), Math.max(0, to)).reduce((a, b) => a + b, 0);
  const pct = (now, before) => (before > 0 ? Math.round((100 * (now - before)) / before) : null);
  const signed = (v) => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v) + "%";
  const fmtWeek = (iso) => new Date(iso + "T12:00:00Z").toLocaleDateString(lang === "ar" ? "ar-EG" : "en-GB", { day: "numeric", month: "short" });
  function selectedTrack() {
    const role = $("role").value;
    return role.startsWith("track:") ? role.slice(6) : role.startsWith("role:") ? trackOfRole[role.slice(5)] || "" : "";
  }
  function trendScope(country) {
    return country && trends.weekly[country] ? country : "All";
  }

  function renderTrends() {
    if (!trends) { $("trendScope").textContent = t("trendsSoon"); return; }
    const country = $("country").value, scope = trendScope(country), track = selectedTrack();
    $("trendScope").textContent = (country && scope === "All" ? t("trendScopeFallback")(country)
      : scope === "All" ? t("trendScopeAll") : t("trendScopeOf")(scope)) + (track ? " · " + track : "");
    const weekly = trends.weekly[scope] || {}, weeks = trends.weeks, n = weeks.length;
    const shownTracks = meta.tracks.map((x) => x.name).filter((name) => weekly[name] && (!track || name === track));
    const totals = weeks.map((_, i) => shownTracks.reduce((a, name) => a + weekly[name][i], 0));
    const enough = trends.history_days >= 14 && (totals[n - 2] || 0) > 0;   // a complete week with data

    // headline numbers (last complete week = n-2)
    const last = totals[n - 2] || 0, prev = totals[n - 3] || 0, change = prev >= 5 ? pct(last, prev) : null;
    const moves = shownTracks.map((name) => {
      const w = weekly[name], now4 = sumRange(w, n - 5, n - 1), before4 = sumRange(w, n - 9, n - 5);
      return { name, now4, before4, change: pct(now4, before4) };
    }).filter((m) => m.now4 + m.before4 >= 5);
    const growing = moves.filter((m) => m.change !== null && m.before4 >= 5).sort((a, b) => b.change - a.change)[0];
    const sk = trends.skills[scope] || trends.skills.All || { rising: [], falling: [] };
    const open = trends.days_open.filter((r) => !track || r[1] === track);
    const openN = open.reduce((a, r) => a + r[5], 0);
    const typical = openN >= 20 ? Math.round(open.reduce((a, r) => a + r[2] * r[5], 0) / openN) : null;
    $("trendStats").innerHTML = !enough ? "" : [
      [num(last), t("statNewWeek") + (change !== null ? ` (${t("statVsPrev")(signed(change))})` : "")],
      [growing ? signed(growing.change) : "–", t("statTopTrack") + (growing ? `: ${growing.name}` : "")],
      [sk.rising[0] ? t("pts")(sk.rising[0][3]) : "–", t("statTopSkill") + (sk.rising[0] ? `: ${sk.rising[0][0]}` : "")],
      [typical ? num(typical) : "–", t("statDaysOpen")],
    ].map(([v, l]) => `<div class="stat"><b>${esc(v)}</b><span>${esc(l)}</span></div>`).join("");

    // weekly chart: stacked by track (or one track's colour)
    $("weeklyHint").textContent = enough ? t("weeklyHint") : t("trendsSoon");
    const max = Math.max(1, ...totals);
    const firstWeek = Math.max(0, totals.findIndex((v) => v > 0));   // no empty bars before the data starts
    $("weeklyChart").innerHTML = !enough ? "" : weeks.map((w, i) => (i < firstWeek ? "" : (() => {
      const segs = shownTracks.map((name) => weekly[name][i] ? `<span class="wseg" style="${tc(name)};height:${(100 * weekly[name][i]) / max}%"
        title="${esc(name)}: ${num(weekly[name][i])}"></span>` : "").join("");
      return `<div class="wk${i === n - 1 ? " partial" : ""}"><span class="wv">${totals[i] ? num(totals[i]) : ""}</span>
        <div class="col">${segs}</div><span class="wl">${i === n - 1 ? t("soFar") : fmtWeek(w)}</span></div>`;
    })())).join("");
    $("weeklyLegend").innerHTML = !enough || track ? "" : shownTracks.map((name) =>
      `<span style="${tc(name)}"><i></i>${esc(name)}</span>`).join("");

    // skills: rising / falling (click = jobs that need it)
    const hint = trends.window_days ? t("skillsHint")(trends.window_days) : t("trendsSoon");
    $("risingHint").textContent = hint; $("fallingHint").textContent = "";
    const moveRow = (r) => `<li><button type="button" class="move" data-skill-filter="${esc(r[0])}"><span class="mname">${esc(r[0])}</span>
      <span class="mfrom">${r[1]}% → ${r[2]}%</span><span class="chg ${r[3] > 0 ? "up" : "down"}">${r[3] > 0 ? "▲" : "▼"} ${esc(t("pts")(r[3]))}</span></button></li>`;
    $("risingList").innerHTML = sk.rising.slice(0, 8).map(moveRow).join("") || `<li class="none">${esc(t("trendsSoon"))}</li>`;
    $("fallingList").innerHTML = sk.falling.slice(0, 8).map(moveRow).join("") || `<li class="none">${esc(t("trendsSoon"))}</li>`;

    // track momentum
    $("trackMoves").innerHTML = !enough ? `<li class="none">${esc(t("trendsSoon"))}</li>` : moves
      .sort((a, b) => (b.change ?? 999) - (a.change ?? 999)).map((m) => `<li style="${tc(m.name)}"><span class="dot"></span>
        <span class="mname">${esc(m.name)}</span><span class="mfrom">${num(m.before4)} → ${num(m.now4)}</span>
        <span class="chg ${m.change === null || m.change >= 0 ? "up" : "down"}">${m.change === null ? t("newTrack") : signed(m.change)}</span></li>`).join("");

    // days open, by role
    bars($("daysOpen"), open.slice(0, 10).map((r) => ({ name: r[0], v: r[2], tr: r[1] })),
      { fmt: (v) => `${v} ${lang === "ar" ? "يوم" : "d"}` });
    const link = new URLSearchParams(); if (scope !== "All") link.set("place", scope); if (lang === "ar") link.set("lang", "ar");
    $("reportLink").href = "report.html" + (link.toString() ? "?" + link : "");
  }

  // ------------------------------------------------------------------ job details panel
  let currentJob = null, drawerReturn = null;
  function groupFor(id) {
    const g = groups.find((x) => x.all.some((y) => y.id === id));
    if (g) return g;
    const j = jobs.find((x) => x.id === id);
    return j ? { key: "one:" + id, job: j, all: [j], pay: j.$ || null, flags: j.f || 0 } : null;
  }
  function similarJobs(j) {
    const mine = mySkillIdx(), country = $("country").value, seen = new Set([(j.t + "|" + j.c).toLowerCase()]);
    return jobs.filter((x) => x.r === j.r && x.id !== j.id && canApplyFrom(x, country) && !(quick.hideNat && (x.f || 0) & FLAG.nationals))
      .map((x) => ({ x, m: mine.size && x.k.length ? x.k.filter((k) => mine.has(k)).length / Math.max(x.k.length, 4) : 0 }))
      .sort((a, b) => b.m - a.m || (a.x.p < b.x.p ? 1 : -1))
      .filter(({ x }) => { const k = (x.t + "|" + x.c).toLowerCase(); if (seen.has(k)) return false; seen.add(k); return true; })
      .slice(0, 4).map(({ x }) => x);
  }
  function renderDrawer(g, j) {
    const mine = mySkillIdx(), f = g.flags;
    const have = j.k.filter((k) => mine.has(k)), miss = j.k.filter((k) => !mine.has(k));
    const fact = (label, value) => (value ? `<div><dt>${esc(label)}</dt><dd>${value}</dd></div>` : "");
    const tags = [f & FLAG.visa ? `<span class="fact visa">${t("visaTag")}</span>` : "",
      f & FLAG.arabic ? `<span class="fact ar">${t("arTag")}</span>` : "",
      f & FLAG.nationals ? `<span class="fact nat">${t("natTag")}</span>` : ""].join("");
    const posted = f & FLAG.longOpen ? t("longOpenFull")
      : new Date(j.p + "T12:00:00Z").toLocaleDateString(lang === "ar" ? "ar-EG" : "en-GB", { day: "numeric", month: "long", year: "numeric" }) + ` · ${ago(j.p)}`;
    const match = !j.k.length ? `<p class="hint">${t("noSkills")}</p>`
      : !mine.size ? `<div class="dcta"><p>${t("matchCta")}</p><button type="button" class="linkbtn" id="drawerAddSkills">${t("matchCtaBtn")}</button></div>
          <div class="dskills"><h3>${t("missTitle")}</h3><div class="chips">${j.k.map((k) => `<span class="chip ghost">${esc(meta.skills[k])}</span>`).join("")}</div></div>`
      : `<div class="dmatch">${matchRing(have.length, j.k.length)}<p>${esc(t("yourMatch")(have.length, j.k.length))}</p></div>
         ${have.length ? `<div class="dskills"><h3>${t("haveTitle")}</h3><div class="chips">${have.map((k) => `<span class="chip have">✓ ${esc(meta.skills[k])}</span>`).join("")}</div></div>` : ""}
         ${miss.length ? `<div class="dskills"><h3>${t("missTitle")}</h3><p class="hint">${t("missHint")}</p><div class="chips">${miss.map((k) =>
           `<button type="button" class="chip add" data-add="${esc(meta.skills[k])}">+ ${esc(meta.skills[k])}</button>`).join("")}</div></div>` : ""}`;
    const similar = similarJobs(j);
    $("drawerBody").innerHTML = `
      <header class="dhead" style="${tc(j.tr)}">
        <span class="avatar big" aria-hidden="true">${esc((j.c || j.t || "?").trim().charAt(0).toUpperCase())}</span>
        <div><h2 id="drawerTitle">${esc(j.t)}</h2><p class="where"><b>${esc(j.c || "")}</b><span>${esc(j.l || "")}</span></p>
          <div class="facts">${g.pay ? `<span class="fact pay">${payText(g.pay)}</span>` : ""}<span class="fact role">${esc(j.r)}</span>${tags}</div></div>
      </header>
      <div class="dactions">
        <a class="apply" href="${esc(j.u)}" target="_blank" rel="noopener nofollow">${t("applyOn")}
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17 17 7M9 7h8v8"/></svg></a>
        <button type="button" class="save" data-id="${esc(j.id)}" aria-pressed="${!!savedJobs[j.id]}">${BOOKMARK}<span>${savedJobs[j.id] ? t("saved") : t("save")}</span></button>
        <button type="button" class="applybtn" data-applied="${esc(j.id)}" aria-pressed="${!!(savedJobs[j.id] && savedJobs[j.id].a)}">${CHECK}<span>${savedJobs[j.id] && savedJobs[j.id].a ? t("applied") : t("markApplied")}</span></button>
      </div>
      <div class="dshare">
        <a class="wabtn" href="${esc(waLink(j))}" target="_blank" rel="noopener" data-share="${esc(j.id)}">${WA_ICON}<span>${t("shareWa")}</span></a>
        ${navigator.share ? `<button type="button" class="ghostbtn" id="shareJob">${t("shareMore")}</button>` : ""}
        <button type="button" class="ghostbtn" id="copyJob">${t("copyLink")}</button>
      </div>
      <section class="dsection">${match}</section>
      <dl class="dfacts">
        ${fact(t("fWorkMode"), esc(j.w === "Remote" ? (j.ww ? t("remoteWorld") : t("remote")) : j.w))}
        ${fact(t("fSalary"), g.pay ? payText(g.pay) + " / yr" : "")}
        ${fact(t("fLevel"), j.s && j.s !== "Not stated" ? esc(j.s) : "")}
        ${fact(t("fRole"), esc(j.r) + ` <span class="muted">· ${esc(j.tr)}</span>`)}
        ${fact(t("fIndustry"), j.i && j.i !== "Not identified" ? esc(j.i) : "")}
        ${fact(t("posted"), esc(posted))}
        ${fact(t("fSource"), j.by ? esc(j.by) : "")}
      </dl>
      ${g.all.length > 1 ? `<section class="dsection"><h3>${t("alsoIn")}</h3><ul class="dlocs">${g.all.filter((x) => x.id !== j.id).map((x) =>
        `<li><a href="${esc(x.u)}" target="_blank" rel="noopener nofollow">${esc(x.l || x.t)}</a></li>`).join("")}</ul></section>` : ""}
      <p class="dreport"><button type="button" class="linkbtn" id="reportJob">⚑ ${t("reportClosed")}</button></p>
      ${similar.length ? `<section class="dsection"><h3>${t("similarTitle")}</h3><ul class="similar">${similar.map((x) =>
        `<li style="${tc(x.tr)}"><button type="button" data-open="${esc(x.id)}"><span class="avatar sm" aria-hidden="true">${esc((x.c || "?").charAt(0).toUpperCase())}</span>
          <span><b>${esc(x.t)}</b><small>${esc(x.c || "")} · ${esc(x.l || "")}</small></span></button></li>`).join("")}</ul></section>` : ""}`;
  }
  function refreshDrawer() {
    if (!currentJob) return;
    const g = groupFor(currentJob), j = jobs.find((x) => x.id === currentJob);
    if (g && j) { const top = $("drawerBody").scrollTop; renderDrawer(g, j); $("drawerBody").scrollTop = top; }
  }
  function openJob(id, opener, write = true) {
    const g = groupFor(id), j = jobs.find((x) => x.id === id);
    if (!g || !j) return;
    if (!currentJob) drawerReturn = opener || document.activeElement;
    currentJob = id;
    renderDrawer(g, j);
    $("jobDrawer").hidden = false; $("drawerScrim").hidden = false;
    document.body.classList.add("drawer-open");
    $("drawerBody").scrollTop = 0;
    $("drawerClose").focus();
    track("job-view/" + j.tr);
    if (write) writeHash();
  }
  function closeJob(write = true) {
    if (!currentJob) return;
    currentJob = null;
    $("jobDrawer").hidden = true; $("drawerScrim").hidden = true;
    document.body.classList.remove("drawer-open");
    if (drawerReturn && document.contains(drawerReturn)) drawerReturn.focus();
    if (write) writeHash();
  }

  // ------------------------------------------------------------------ active filter chips
  function renderChips() {
    const chips = [];
    const add = (label, attr) => chips.push(`<button type="button" class="fchip" ${attr} aria-label="${esc(t("removeFilter")(label))}">${esc(label)}<span aria-hidden="true">×</span></button>`);
    if ($("country").value) add($("country").value, 'data-clear="country"');
    const role = $("role").value;
    if (role) add(role.replace(/^(track|role):/, ""), 'data-clear="role"');
    if ($("q").value.trim()) add(`“${$("q").value.trim()}”`, 'data-clear="q"');
    ["seniority", "workMode", "industry", "skill", "arabic"].forEach((f) => {
      if ($(f).value) add(f === "arabic" ? `${t("arabic")}: ${$(f).selectedOptions[0].text}` : $(f).selectedOptions[0].text, `data-clear="${f}"`);
    });
    const flagLabel = { remote: "qRemote", visa: "qVisa", junior: "qJunior", pay: "qPay", week: "qWeek" };
    Object.entries(flagLabel).forEach(([k, label]) => { if (quick[k]) add(t(label), `data-flag-off="${k}"`); });
    if (!quick.hideNat) add(t("showNat"), 'data-flag-on="hideNat"');
    if (quick.fresh) add(t("qNew"), 'data-flag-off="fresh"');
    $("activeFilters").innerHTML = chips.length > 1 || (chips.length && !$("country").value)
      ? chips.join("") + `<button type="button" class="linkbtn" id="chipsClear">${t("clearAll")}</button>` : chips.join("");
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
    const extra = ["seniority", "workMode", "industry", "skill", "arabic"].filter((f) => $(f).value).length
      + Object.entries(quick).filter(([k, v]) => v !== (k === "hideNat") && k !== "fresh").length;
    $("filterSummary").textContent = extra ? t("filtersN")(extra) : t("filters");
    $("filterOpen").classList.toggle("on", extra > 0);
    $("sheetDone").textContent = t("showN")(num(groups.length));
    renderTracks();
    renderChips();
    if (document.activeElement !== $("qMini")) $("qMini").value = $("q").value;
    renderSkills();
    renderLearn();
    renderNewBanner();
    renderJobs();
    if (currentJob) { const g = groupFor(currentJob), j = jobs.find((x) => x.id === currentJob); if (g && j) renderDrawer(g, j); }
    renderSaved();
    if (!$("insights").hidden) renderInsights();
    if (!$("trends").hidden) renderTrends();
    writeHash();
  }

  function selectTab(id, write = true) {
    // the skills box and filters belong to job views; reading views (Saved, How it works) get the full width
    document.body.dataset.tab = id;
    document.querySelectorAll('[role="tab"]').forEach((b) => {
      const on = b.getAttribute("aria-controls") === id;
      b.setAttribute("aria-selected", String(on));
      $(b.getAttribute("aria-controls")).hidden = !on;
    });
    if (!meta) return;
    if (id === "insights") renderInsights();
    if (id === "trends") renderTrends();
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
    track("share");
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
    // filters: a sidebar on wide screens, a bottom sheet on phones
    const sheet = (open) => {
      document.body.classList.toggle("sheet-open", open);
      $("scrim").hidden = !open;
      $("filterOpen").setAttribute("aria-expanded", String(open));
      if (open) $("sheetClose").focus(); else $("filterOpen").focus();
    };
    $("filterOpen").addEventListener("click", () => sheet(true));
    ["sheetClose", "sheetDone", "scrim"].forEach((id) => $(id).addEventListener("click", () => sheet(false)));
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && document.body.classList.contains("sheet-open")) sheet(false); });
    $("console").addEventListener("submit", () => {
      update(); selectTab("jobs");
      $("results").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    });
    $("trends").addEventListener("click", (e) => {
      const b = e.target.closest("[data-skill-filter]");
      if (!b) return;
      $("skill").value = b.dataset.skillFilter; selectTab("jobs"); update(); track("trend-skill");
      $("results").scrollIntoView({ behavior: "smooth" });
    });
    $("trackPills").addEventListener("click", (e) => {
      const b = e.target.closest("[data-track]");
      if (b) { $("role").value = b.dataset.track; update(); track("track/" + (b.dataset.track.slice(6) || "all")); }
    });
    $("reset").addEventListener("click", resetFilters);
    $("share").addEventListener("click", share);
    document.querySelectorAll('[role="tab"]').forEach((b) => b.addEventListener("click", () => selectTab(b.getAttribute("aria-controls"))));
    $("lang").addEventListener("click", () => {
      lang = lang === "ar" ? "en" : "ar"; store.set("lang", lang); track("language-" + lang); applyLanguage(); readHash(); update(true);
    });
    $("country").addEventListener("change", () => { store.set("country", $("country").value); track("country/" + ($("country").value || "any")); });
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
      const x = e.target.closest("[data-applied],[data-unsave],[data-saved-view],[data-learn-see],[data-share],#newToggle");
      if (x) {
        if (x.dataset.applied) { toggleApplied(x.dataset.applied); renderJobs(); renderSaved(); refreshDrawer(); }
        else if (x.dataset.unsave) { delete savedJobs[x.dataset.unsave]; store.set("saved", savedJobs); renderSaved(); }
        else if (x.dataset.savedView) { savedView = x.dataset.savedView; renderSaved(); }
        else if (x.dataset.learnSee) { $("skill").value = x.dataset.learnSee; update(); goToJobs(); track("learn-see"); }
        else if (x.dataset.share) { const j = jobs.find((y) => y.id === x.dataset.share); track("job-share/whatsapp/" + (j ? j.tr : "unknown")); }
        else if (x.id === "newToggle") { quick.fresh = !quick.fresh; if (quick.fresh) track("new-since-visit"); update(); }
        return;
      }
      const el = e.target.closest("[data-skill],[data-add],[data-id],.locbtn");
      if (!el) return;
      if (el.dataset.skill) { mySkills.delete(el.dataset.skill); store.set("mySkills", [...mySkills]); update(true); }
      else if (el.dataset.add) addSkill(el.dataset.add);
      else if (el.dataset.id) {
        const id = el.dataset.id;
        toggleSaved(id);
        el.setAttribute("aria-pressed", String(!!savedJobs[id]));
        el.querySelector("span").textContent = savedJobs[id] ? t("saved") : t("save");
        if (el.closest(".drawer")) { renderJobs(); refreshDrawer(); }
        renderSaved();
      } else if (el.classList.contains("locbtn")) {
        const k = el.dataset.key;
        if (openLocs.has(k)) openLocs.delete(k); else openLocs.add(k);
        renderJobs();
      }
    });
    // a job opens its details panel; Ctrl/Cmd/middle click still opens the original posting
    document.addEventListener("click", (e) => {
      const a = e.target.closest(".job h3 a");
      if (a && !e.metaKey && !e.ctrlKey && !e.shiftKey && e.button === 0) {
        e.preventDefault(); openJob(a.closest(".job").dataset.jid, a); return;
      }
      const o = e.target.closest("[data-open]");
      if (o) { e.preventDefault(); openJob(o.dataset.open, o); return; }
      // which kinds of jobs people apply to (the track only, nothing about the visitor)
      const go = e.target.closest(".drawer .apply, .dlocs a, .locs a");
      if (go) { const j = jobs.find((x) => x.id === currentJob); track("job-open/" + (j ? j.tr : "unknown")); }
    });
    $("drawerClose").addEventListener("click", () => closeJob());
    $("drawerScrim").addEventListener("click", () => closeJob());
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && currentJob) { closeJob(); return; }
      if (e.key === "/" && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)) {
        e.preventDefault();
        const mini = $("qMini");
        (mini.offsetParent ? mini : $("q")).focus();
      }
    });
    $("jobDrawer").addEventListener("click", (e) => {
      if (e.target.closest("#drawerAddSkills")) { closeJob(); selectTab("jobs"); document.querySelector(".skillsbox").scrollIntoView({ behavior: "smooth" }); $("mySkillInput").focus(); }
      if (e.target.closest("#copyJob")) {
        const b = e.target.closest("#copyJob");
        const j = jobs.find((x) => x.id === currentJob);
        navigator.clipboard.writeText(j ? jobLink(j) : location.href).then(() => { b.textContent = t("linkCopied"); setTimeout(() => { b.textContent = t("copyLink"); }, 2000); }).catch(() => {});
        track("job-share/copy");
      }
      if (e.target.closest("#reportJob")) {
        const id = currentJob, j = jobs.find((x) => x.id === id);
        track("report-closed/" + id + (j ? "/" + (j.c || "").replace(/[^\w-]+/g, "-") : ""));
        hiddenJobs.add(id); store.set("hidden", [...hiddenJobs].slice(-500));
        closeJob(); update(true); toast(t("reported"));
      }
      if (e.target.closest("#shareJob")) {
        const j = jobs.find((x) => x.id === currentJob);
        if (j) navigator.share({ title: j.t, text: t("shareText")(j.t, j.c), url: jobLink(j) }).then(() => track("job-share/native")).catch(() => {});
      }
    });
    // active filter chips
    $("activeFilters").addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      if (b.id === "chipsClear") { $("country").value = ""; store.set("country", ""); resetFilters(); return; }
      if (b.dataset.clear) { $(b.dataset.clear).value = ""; if (b.dataset.clear === "country") store.set("country", ""); }
      if (b.dataset.flagOff) quick[b.dataset.flagOff] = false;
      if (b.dataset.flagOn) quick[b.dataset.flagOn] = true;
      syncToggles(); update();
    });
    // the compact search in the sticky bar mirrors the main keywords box
    $("qMini").addEventListener("input", () => { $("q").value = $("qMini").value; update(); });
    $("qMini").addEventListener("keydown", (e) => { if (e.key === "Enter") { selectTab("jobs"); $("results").scrollIntoView({ behavior: "smooth" }); } });
    window.addEventListener("hashchange", () => { readHash(); update(); });
    window.addEventListener("resize", sizeHero);
  }

  let toastTimer = null;
  function toast(msg) {
    const el = $("toast"); el.textContent = msg; el.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { el.hidden = true; }, 3500);
  }
  // weekly email (Buttondown): shown only when the publish step filled in the newsletter name
  function setupNewsletter() {
    const box = $("newsletter"), name = box.dataset.bd;
    if (!name) return;
    box.hidden = false;
    $("nlForm").action = "https://buttondown.com/api/emails/embed-subscribe/" + encodeURIComponent(name);
    $("nlForm").addEventListener("submit", () => { track("newsletter-subscribe"); setTimeout(() => toast(t("nlThanks")), 300); });
  }

  // ------------------------------------------------------------------ install as an app (PWA)
  let installEvt = null;
  const standalone = () => matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent) && !window.MSStream;
  function setupInstall() {
    if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) {
      navigator.serviceWorker.register("sw.js").catch(() => {});
    }
    const btn = $("installBtn");
    if (standalone()) return;
    window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); installEvt = e; btn.hidden = false; });
    window.addEventListener("appinstalled", () => { btn.hidden = true; track("app-installed"); });
    if (isIOS()) btn.hidden = false;           // Safari has no install prompt: show how to do it by hand
    btn.addEventListener("click", async () => {
      track("install-click");
      if (installEvt) { installEvt.prompt(); const r = await installEvt.userChoice.catch(() => null); if (r && r.outcome === "accepted") btn.hidden = true; installEvt = null; return; }
      $("iosHint").hidden = false;
    });
    $("iosHintClose").addEventListener("click", () => { $("iosHint").hidden = true; });
  }

  async function start() {
    applyLanguage();
    setupInstall();
    setupNewsletter();
    try {
      const [m, j] = await Promise.all([
        fetch("data/meta.json").then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }),
        fetch("data/jobs.json").then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }),
      ]);
      meta = m; jobs = j;
      // trends are optional: the site works without them (e.g. before the first pipeline run with trend marts)
      trends = await fetch("data/trends.json").then((r) => (r.ok ? r.json() : null)).catch(() => null);
    } catch {
      $("count").textContent = "–";
      $("jobList").innerHTML = "";
      $("empty").hidden = false;
      $("empty").textContent = t("loadError");
      return;
    }
    meta.countries.forEach((c) => { regionOf[c.name] = c.region; });
    initVisit();
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
