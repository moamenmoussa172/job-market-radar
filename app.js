/* Radarak - static site. Data: data/meta.json + data/jobs.json (+ data/jobs-more.json on demand), refreshed daily by the pipeline. */
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
      yourSkills: "Match jobs to your skills", addSkill: "Add a skill you have", addByHand: "or add skills by hand",
      yourSkillsHint: "Upload your CV or add skills. Every job gets a match score, and the best matches come first.",
      heroTitle: "Tech jobs you can actually get.",
      heroSub: "Fresh every morning from company career pages and job boards across Egypt, the Gulf, Europe and remote, filtered by where you live.",
      segRole: "I'm looking for", segKeywords: "Keywords", searchBtn: "Search", browseTracks: "Browse by track",
      filters: "Filters", filtersN: (n) => `Filters (${n})`, quickTitle: "Show only", close: "Close",
      showN: (n) => `Show ${n} jobs`, miniPh: "Search jobs  ( / )", clearAll: "Clear all", removeFilter: (x) => `Remove filter ${x}`,
      openOn: (src) => `Open on ${src}`, cardFind: "company site ↗",
      adzNote: (place) => `Adzuna shows this job only to people in ${place}. If it says “not available in your region”, look for the same job on the company's own site:`,
      findOnSite: (c) => `Find it on ${c}'s site ↗`,
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
      tabKit: "Apply kit",
      askApplied: (job, co) => `Did you apply to ${job}${co ? " at " + co : ""}?`, askYes: "Yes, mark as applied", askNo: "Not yet",
      tipSaved: "Saved. Find it any time in the Saved tab.", tipApplied: "Marked as applied ✓ It's in Saved → Applied.",
      savedEmptyTitle: "Nothing saved yet", savedBrowse: "Browse jobs",
      cvToKit: "Save it to my Apply kit", cvToKitMore: "Add it to my Apply kit", cvToKitDone: "Saved in your Apply kit, on this device.",
      cvToKitHint: "Keep this CV in your Apply kit: every job will show how well it fits, and you can attach it in one tap.",
      kitPickLabel: "Your CVs:",
      kitTitle: "Your apply kit", kitStep1: "Your details", kitStep2: "Your CV", kitStep3: "Cover letter",
      kitProgress: (n) => `${n} of 3 steps done`, kitReady: "Your kit is ready. Open any job to see which CV fits it.",
      kitSeeJobs: "See jobs that fit", kitAddFirstCv: "+ Add your CV", kitEdit: "Edit",
      kitBackupHint: "A file with your whole kit, to move it to another browser or keep it safe.",
      extGet: "Fill applications in one click", extGetHint: "On a computer, the free Radarak Apply extension fills application forms (Greenhouse, Lever, Ashby, Workable and more) with this kit and attaches the CV that fits best.",
      extGetBtn: "Get the extension (Chrome, Edge, Firefox…)", extOn: "Radarak Apply extension connected.",
      extOnHint: "On an application form, click “Fill with Radarak”. It fills your details, attaches the best CV and adds the cover letter. You check and submit.",
      kitIntro: "Fill this once. Then every job shows which of your CVs fits it best, and every answer is ready to copy.",
      kitPrivacy: "🔒 Everything stays on this device. Nothing is uploaded to Radarak or sent anywhere. Use Backup to move it to another phone or browser.",
      kitDetails: "My details", kitCvs: "My CVs", kitLetters: "Cover letters", kitBackup: "Backup",
      kFirst: "First name", kLast: "Last name", kEmail: "Email", kPhone: "Phone (with country code)", kCountry: "Country",
      kCity: "City", kLinkedin: "LinkedIn", kPortfolio: "GitHub / portfolio", kYears: "Years of experience",
      kNotice: "Notice period", kNoticePh: "e.g. 1 month", kSalary: "Expected salary", kSalaryPh: "e.g. 40,000 EGP / month",
      kitSaved: "Saved on this device",
      kitAddCv: "+ Add a CV", kitCvHint: "PDF or Word. Up to 5, for example one per role. Read on your device only.",
      kitCvName: "Name of this CV", kitCvSkills: (n) => `${n} skills found`, kitCvYears: (n) => `${n} years`,
      kitUseCv: "Match jobs with this CV", kitDownload: "Download", kitDelete: "Delete", kitReallyDelete: "Tap again to delete",
      kitCvMax: "You can keep up to 5 CVs. Delete one to add another.", kitCvRead: (f) => `Reading ${f}…`,
      kitCvAdded: (n) => `Added: ${n}`, kitNoCvs: "No CVs yet. Add the CV you send most, then one per role if you have more.",
      kitAddLetter: "+ Add a cover letter", kitLetterName: "Name", kitLetterHelp: "These words fill in by themselves for each job: {company} {job} {first} {last} {years}",
      kitLetterDefaultName: "Short letter",
      kitLetterDefault: "Dear {company} hiring team,\n\nI'm applying for the {job} role. I have {years} years of experience, and the skills in this job match the work I do every day.\n\nI'd be happy to talk about how I can help your team.\n\nBest regards,\n{first} {last}",
      kitExport: "Save a backup file", kitImport: "Restore from a backup", kitImported: "Your apply kit is back",
      kitBadFile: "That file isn't a Radarak backup.", kitWipe: "Delete my apply kit", kitWiped: "Your apply kit was deleted from this device",
      kitNoStorage: "This browser can't keep files (private window?). Your CVs will be gone when you close it.",
      dSend: "Send", dTone_good: "strong match", dTone_ok: "partial match", dTone_low: "weak match",
      dMissShort: "This job asks for, but your CV doesn't mention:", dMissHint: "Have these skills? Add them to your CV before you send it.",
      dDownloadCv: "Download this CV", dExtHint: "Then click “Fill with Radarak” on the application form.",
      dLetterFor: (c) => (c ? `Cover letter for ${c}` : "Cover letter"),
      dKit: "Apply faster", dKitCta: "Save your details and CVs once. Then every job shows which CV fits it and gives you copy-ready answers.",
      dKitBtn: "Set up my apply kit", dFit: "Which of your CVs fits this job", dBest: "best fit",
      dMissing: (n) => `This job asks for ${n} that your best CV doesn't mention. If you have them, add them to the CV before you send it.`,
      dAllThere: "Your best CV mentions every skill this job asks for. 👍", dNoSkills: "This job lists no skills we can compare.",
      dCopy: "Copy your answers", dCopyHint: "Tap to copy, then paste into the application form.", dLetter: "Cover letter",
      copied: "Copied", copy: "Copy", dEditKit: "Edit my apply kit", dSentWith: (n) => `Sent with: ${n}`,
      tabJobsS: "Jobs", tabInsightsS: "Skills", tabTrendsS: "Trends", tabSavedS: "Saved", tabKitS: "Apply kit", tabAboutS: "About",
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
      savedEmpty: "Tap Save on a job to keep it here, then tick it when you apply.",
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
      loadingMore: "loading more jobs…",
      cvUpload: "Upload your CV", cvPaste: "or paste its text", cvPrivacy: "Read on your device. Your CV is never uploaded.",
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
      reportClosed: "Can't apply? Tell us", reported: "Thanks! We hid this job, and it's removed for everyone on the next update.",
      repAsk: "What does the job page say?", repGone: "Removed, expired or filled", repRegion: "“Not available in your region”",
      repCancel: "Cancel", repRegionNote: "That's the job board blocking visitors from other countries, not a closed job. Look for the same job on the company's own site:",
      nlTitle: "Radarak Weekly", nlText: "Every Sunday: the week's new tech jobs in Egypt, the Gulf and remote, in one short email.",
      nlEmail: "Your email", nlEmailPh: "you@example.com", nlBtn: "Subscribe", nlThanks: "Check your inbox to confirm.",
      tgPlace: (p) => `New ${p} jobs every morning on Telegram`, tgJoin: "Join on Telegram", tgAny: "New tech jobs every morning on Telegram", tgFoot: "New jobs every day on Telegram:", hideTip: "Hide",
      insKicker: "Insight of the day", insSee: "See the jobs", insImg: "Save image", insPrev: "Previous insight", insNext: "Next insight",
      insChannels: "New jobs every morning: t.me/radarak_egypt · gulf · remote",
      shareCard: "Share my result", shareCardDone: "Image saved. Share it on LinkedIn or WhatsApp!",
      cardMatch: "I match", cardJobs: (what, where) => `${what} jobs${where ? " in " + where : ""}`, cardTech: "tech", cardRemote: "remote",
      cardNext: "My next skills to learn", cardHave: "My top skills", cardJobsN: (n) => `+${n} jobs`,
      cardCta: "Find the jobs you can actually get", cardPrivacy: "My CV was read on my device. It was never uploaded.",
      cardShareText: "Here's what the job market says about my skills. Check yours:", learnTop: (s, n) => `🎯 Learn <b>${s}</b> → <b>+${n}</b> more jobs you match`,
      learnTitle: "What to learn next", learnNow: (m) => `You match <b>${m}</b> jobs right now.`,
      learnHint: "Each step counts the extra jobs you'd match (60%+ of their skills) after learning it and the ones above it.",
      learnJobs: (n) => `+${n} jobs`, learnPay: (p) => `jobs that ask for it pay ${p}% more`, learnRising: "rising",
      learnFalling: "cooling", learnPayHint: "Pay compares jobs with a published salary that ask for the skill with similar jobs that don't (same country and level).", learnTotal: (a, b) => `Learn all ${a === 1 ? "of it" : "three"}: <b>${b}</b> jobs you match`,
      learnKnow: "I know it", learnSee: "See jobs", learnNone: "You already match most jobs here, or they list too few skills to say.",
      applied: "Applied", markApplied: "Mark as applied", appliedOn: (d) => `Applied ${d}`, savedOn: (d) => `Saved ${d}`,
      savedAll: "All", savedTodo: "To apply", savedDone: "Applied", closedTag: "No longer listed", removeSaved: "Remove",
      savedTalks: "Interviews", stageLabel: "Stage", stApplied: "Applied", stInterview: "Interviewing", stOffer: "Offer 🎉", stRejected: "Not this time", stNone: "↩ Not applied yet", offerToast: "Congrats on the offer! 🎉",
      pipeApplied: "applied", pipeTalks: "interviews", pipeOffers: "offers", pipeRate: (p) => `${p}% got a reply`,
      followUp: (d) => `${d} days with no reply. A short, polite follow-up email often helps.`,
      watchAdd: "Alert me", watchOn: "Alert on", watchSaved: "Saved! Each time you open Radarak you'll see how many new jobs match this search.",
      watchRemoved: "Alert removed.", watchNew: (n) => `${n} new`, watchNone: "no new jobs", watchTitle: "My alerts",
      watchShowing: (l) => `New jobs for “${l}”`, watchAll: "Show all jobs", watchDel: (l) => `Remove alert “${l}”`,
      watchAll0: "All tech jobs", watchMax: "You can keep up to 8 alerts. Remove one first.",
      watchNotify: "🔔 Notify me when new jobs come", watchNotifyOn: "Notifications are on",
      watchNotifyHint: "Your phone shows a short note when the day's new jobs are in. Nothing about you is sent anywhere.",
      watchInstall: "Install Radarak as an app to see new jobs as a badge on its icon.",
      notifyTitle: "New jobs on Radarak", notifyBody: "Today's jobs are in. Open Radarak to see what's new for your alerts.",
      viewedTag: "Viewed", coPage: (c) => `${c}: all jobs, hiring pace and skills`, hideCo: (c) => `Hide jobs from ${c}`, hidCo: (c) => `Jobs from ${c} are hidden.`, undo: "Undo",
      hiddenCos: (n) => `${n} hidden ${n === 1 ? "company" : "companies"}`,
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
      yourSkills: "شوف الوظايف المناسبة لمهاراتك", addSkill: "ضيف مهارة عندك", addByHand: "أو ضيف مهاراتك بإيدك",
      yourSkillsHint: "ارفع الـ CV أو ضيف مهاراتك. كل وظيفة هتاخد نسبة تطابق، والأنسب هتظهر الأول.",
      heroTitle: "وظايف تك تقدر توصلها فعلًا.",
      heroSub: "بتتحدّث كل يوم الصبح من صفحات توظيف الشركات ومواقع الوظايف في مصر والخليج وأوروبا والريموت، ومفلترة حسب البلد اللي إنت فيها.",
      segRole: "بدوّر على", segKeywords: "كلمات بحث", searchBtn: "دوّر", browseTracks: "تصفّح حسب المجال",
      filters: "الفلاتر", filtersN: (n) => `الفلاتر (${n})`, quickTitle: "اعرض بس", close: "اقفل",
      showN: (n) => `اعرض ${n} وظيفة`, miniPh: "دوّر على وظيفة  ( / )", clearAll: "امسح الكل", removeFilter: (x) => `شيل فلتر ${x}`,
      openOn: (src) => `افتحها على ${src}`, cardFind: "موقع الشركة ↗",
      adzNote: (place) => `Adzuna بيعرض الوظيفة دي بس للي في ${place}. لو ظهرلك “not available in your region”، دوّر على نفس الوظيفة في موقع الشركة نفسها:`,
      findOnSite: (c) => `دوّر عليها في موقع ${c} ↗`,
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
      tabKit: "ملف التقديم",
      askApplied: (job, co) => `قدّمت على ${job}${co ? " في " + co : ""}؟`, askYes: "أيوه، علّمها إني قدّمت", askNo: "لسه",
      tipSaved: "اتحفظت. هتلاقيها في المحفوظة في أي وقت.", tipApplied: "اتعلّمت إنك قدّمت ✓ هتلاقيها في المحفوظة ← قدّمت.",
      savedEmptyTitle: "لسه مفيش حاجة محفوظة", savedBrowse: "شوف الوظايف",
      cvToKit: "احفظه في ملف التقديم", cvToKitMore: "ضيفه لملف التقديم", cvToKitDone: "اتحفظ في ملف التقديم، على الجهاز ده.",
      cvToKitHint: "احتفظ بالـ CV ده في ملف التقديم: كل وظيفة هتقولك هو مناسب قد إيه، وتقدر ترفقه بضغطة.",
      kitPickLabel: "الـ CVs بتاعتك:",
      kitTitle: "ملف التقديم بتاعك", kitStep1: "بياناتك", kitStep2: "الـ CV", kitStep3: "خطاب التقديم",
      kitProgress: (n) => `${n} من 3 خطوات خلصت`, kitReady: "ملفك جاهز. افتح أي وظيفة وهتعرف أنهي CV الأنسب ليها.",
      kitSeeJobs: "شوف الوظايف المناسبة", kitAddFirstCv: "+ ضيف الـ CV بتاعك", kitEdit: "تعديل",
      kitBackupHint: "ملف فيه كل حاجة في ملف التقديم، عشان تنقله لمتصفح تاني أو تحتفظ بيه.",
      extGet: "املى فورم التقديم بضغطة واحدة", extGetHint: "على الكمبيوتر، إضافة Radarak Apply المجانية بتملى فورمات التقديم (Greenhouse وLever وAshby وWorkable وغيرهم) من ملف التقديم ده، وبترفق الـ CV الأنسب.",
      extGetBtn: "نزّل الإضافة (Chrome وEdge وFirefox…)", extOn: "إضافة Radarak Apply متوصلة.",
      extOnHint: "في فورم التقديم، دوس “Fill with Radarak”. هتملى بياناتك وترفق الـ CV الأنسب وتضيف خطاب التقديم. انت تراجع وتبعت.",
      kitIntro: "املاه مرة واحدة. وبعدها كل وظيفة هتقولك أنهي CV من بتوعك الأنسب ليها، وكل الإجابات هتبقى جاهزة للنسخ.",
      kitPrivacy: "🔒 كل حاجة بتفضل على الجهاز ده بس. مفيش حاجة بتترفع على رادارك أو بتتبعت لأي حد. استخدم النسخة الاحتياطية عشان تنقلها لموبايل أو متصفح تاني.",
      kitDetails: "بياناتي", kitCvs: "الـ CVs بتاعتي", kitLetters: "خطابات التقديم", kitBackup: "نسخة احتياطية",
      kFirst: "الاسم الأول", kLast: "اسم العيلة", kEmail: "الإيميل", kPhone: "الموبايل (بكود الدولة)", kCountry: "الدولة",
      kCity: "المدينة", kLinkedin: "LinkedIn", kPortfolio: "GitHub / بورتفوليو", kYears: "سنين الخبرة",
      kNotice: "فترة الإخطار", kNoticePh: "مثلًا شهر", kSalary: "المرتب المتوقع", kSalaryPh: "مثلًا 40,000 جنيه في الشهر",
      kitSaved: "اتحفظ على الجهاز ده",
      kitAddCv: "+ ضيف CV", kitCvHint: "PDF أو Word. لحد 5، مثلًا واحد لكل وظيفة. بيتقري على جهازك بس.",
      kitCvName: "اسم الـ CV ده", kitCvSkills: (n) => `${n} مهارة`, kitCvYears: (n) => `${n} سنين`,
      kitUseCv: "طابق الوظايف بالـ CV ده", kitDownload: "نزّله", kitDelete: "امسح", kitReallyDelete: "دوس تاني عشان تمسح",
      kitCvMax: "تقدر تحتفظ بـ 5 CVs بس. امسح واحد عشان تضيف غيره.", kitCvRead: (f) => `بنقرا ${f}…`,
      kitCvAdded: (n) => `اتضاف: ${n}`, kitNoCvs: "لسه مفيش CVs. ضيف الـ CV اللي بتبعته أكتر، وبعدين واحد لكل وظيفة لو عندك.",
      kitAddLetter: "+ ضيف خطاب تقديم", kitLetterName: "الاسم", kitLetterHelp: "الكلمات دي بتتملى لوحدها لكل وظيفة: {company} {job} {first} {last} {years}",
      kitLetterDefaultName: "خطاب قصير",
      kitLetterDefault: "Dear {company} hiring team,\n\nI'm applying for the {job} role. I have {years} years of experience, and the skills in this job match the work I do every day.\n\nI'd be happy to talk about how I can help your team.\n\nBest regards,\n{first} {last}",
      kitExport: "احفظ ملف نسخة احتياطية", kitImport: "رجّع من نسخة احتياطية", kitImported: "ملف التقديم رجع",
      kitBadFile: "الملف ده مش نسخة احتياطية من رادارك.", kitWipe: "امسح ملف التقديم", kitWiped: "ملف التقديم اتمسح من الجهاز ده",
      kitNoStorage: "المتصفح ده مش بيحتفظ بالملفات (يمكن نافذة خاصة؟). الـ CVs هتتمسح لما تقفله.",
      dSend: "ابعت", dTone_good: "مناسب جدًا", dTone_ok: "مناسب لحد ما", dTone_low: "مش مناسب قوي",
      dMissShort: "الوظيفة طالبة دول والـ CV مش ذاكرهم:", dMissHint: "عندك المهارات دي؟ ضيفها للـ CV قبل ما تبعته.",
      dDownloadCv: "نزّل الـ CV ده", dExtHint: "وبعدين دوس “Fill with Radarak” في فورم التقديم.",
      dLetterFor: (c) => (c ? `خطاب التقديم لـ ${c}` : "خطاب التقديم"),
      dKit: "قدّم أسرع", dKitCta: "احفظ بياناتك والـ CVs مرة واحدة. وبعدها كل وظيفة هتقولك أنهي CV الأنسب، وهتديك إجابات جاهزة للنسخ.",
      dKitBtn: "جهّز ملف التقديم", dFit: "أنهي CV من بتوعك الأنسب للوظيفة دي", dBest: "الأنسب",
      dMissing: (n) => `الوظيفة دي طالبة ${n} والـ CV الأنسب مش ذاكرها. لو عندك المهارات دي، ضيفها للـ CV قبل ما تبعته.`,
      dAllThere: "الـ CV الأنسب فيه كل المهارات اللي الوظيفة طالباها. 👍", dNoSkills: "الوظيفة دي مش مكتوب فيها مهارات نقدر نقارنها.",
      dCopy: "انسخ إجاباتك", dCopyHint: "دوس عشان تنسخ، وبعدين الصق في فورم التقديم.", dLetter: "خطاب التقديم",
      copied: "اتنسخ", copy: "انسخ", dEditKit: "عدّل ملف التقديم", dSentWith: (n) => `اتبعت بـ: ${n}`,
      tabJobsS: "الوظايف", tabInsightsS: "المهارات", tabTrendsS: "الترندات", tabSavedS: "المحفوظة", tabKitS: "التقديم", tabAboutS: "عن الموقع",
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
      loadingMore: "بنحمّل باقي الوظايف…",
      cvUpload: "ارفع الـ CV بتاعك", cvPaste: "أو الصق النص", cvPrivacy: "بيتقري على جهازك. الـ CV مش بيترفع خالص.",
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
      reportClosed: "مش عارف تقدّم؟ قولنا", reported: "شكرًا! خبّينا الوظيفة، وهتتشال عند الكل في التحديث الجاي.",
      repAsk: "صفحة الوظيفة مكتوب فيها إيه؟", repGone: "اتشالت، انتهت أو اتملت", repRegion: "“Not available in your region”",
      repCancel: "إلغاء", repRegionNote: "ده موقع الوظايف بيمنع الزوار من بلاد تانية، الوظيفة نفسها لسه مفتوحة. دوّر عليها في موقع الشركة نفسها:",
      nlTitle: "نشرة رادارك الأسبوعية", nlText: "كل يوم حد: وظايف التك الجديدة في مصر والخليج والريموت، في إيميل واحد قصير.",
      nlEmail: "الإيميل بتاعك", nlEmailPh: "you@example.com", nlBtn: "اشترك", nlThanks: "شوف الإيميل بتاعك عشان تأكد الاشتراك.",
      tgPlace: (p) => `وظايف ${p} الجديدة كل صبح على تيليجرام`, tgJoin: "اشترك على تيليجرام", tgAny: "وظايف التك الجديدة كل صبح على تيليجرام", tgFoot: "وظايف جديدة كل يوم على تيليجرام:", hideTip: "إخفاء",
      insKicker: "معلومة النهارده", insSee: "شوف الوظايف", insImg: "احفظ الصورة", insPrev: "المعلومة اللي قبلها", insNext: "المعلومة اللي بعدها",
      insChannels: "وظايف جديدة كل صبح: t.me/radarak_egypt · gulf · remote",
      shareCard: "شارك نتيجتك", shareCardDone: "الصورة اتحفظت. شاركها على لينكدإن أو واتساب!",
      cardMatch: "أنا مناسب لـ", cardJobs: (what, where) => `وظيفة ${what}${where ? " في " + where : ""}`, cardTech: "تك", cardRemote: "ريموت",
      cardNext: "المهارات اللي هتعلمها بعد كده", cardHave: "أهم مهاراتي", cardJobsN: (n) => `+${n} وظيفة`,
      cardCta: "لاقي الوظايف اللي تقدر تاخدها فعلًا", cardPrivacy: "الـ CV بتاعي اتقرا على جهازي، ومترفعش في أي حتة.",
      cardShareText: "ده رأي سوق الشغل في مهاراتي. شوف مهاراتك:", learnTop: (s, n) => `🎯 اتعلم <b>${s}</b> ← <b>+${n}</b> وظيفة زيادة مناسبة ليك`,
      learnTitle: "تتعلم إيه بعد كده", learnNow: (m) => `إنت مناسب لـ <b>${m}</b> وظيفة دلوقتي.`,
      learnHint: "كل خطوة بتحسب الوظايف الزيادة اللي هتبقى مناسب لها (60%+ من مهاراتها) لو اتعلمت المهارة دي واللي فوقها.",
      learnJobs: (n) => `+${n} وظيفة`, learnPay: (p) => `الوظايف اللي بتطلبها مرتبها أعلى ${p}%`, learnRising: "طالعة",
      learnFalling: "بتهدى", learnPayHint: "المرتب: بنقارن الوظايف اللي كاتبة مرتب وبتطلب المهارة بوظايف شبهها مش بتطلبها (نفس البلد ونفس المستوى).", learnTotal: (a, b) => `لو اتعلمتهم ${a === 1 ? "" : "التلاتة"}: <b>${b}</b> وظيفة مناسبة ليك`,
      learnKnow: "بعرفها", learnSee: "شوف الوظايف", learnNone: "إنت مناسب لأغلب الوظايف هنا، أو مهاراتها المكتوبة قليلة.",
      applied: "قدّمت", markApplied: "قدّمت عليها", appliedOn: (d) => `قدّمت ${d}`, savedOn: (d) => `اتحفظت ${d}`,
      savedAll: "الكل", savedTodo: "لسه هقدّم", savedDone: "قدّمت", closedTag: "مش معروضة دلوقتي", removeSaved: "شيلها",
      savedTalks: "إنترفيوهات", stageLabel: "المرحلة", stApplied: "قدّمت", stInterview: "في إنترفيو", stOffer: "عرض 🎉", stRejected: "مش المرة دي", stNone: "↩ لسه مقدّمتش", offerToast: "مبروك على العرض! 🎉",
      pipeApplied: "قدّمت", pipeTalks: "إنترفيو", pipeOffers: "عروض", pipeRate: (p) => `${p}% ردّوا عليك`,
      followUp: (d) => `${d} يوم من غير رد. إيميل متابعة قصير ومحترم بيفرق كتير.`,
      watchAdd: "نبّهني", watchOn: "التنبيه شغال", watchSaved: "اتحفظ! كل ما تفتح رادارك هتشوف كام وظيفة جديدة على البحث ده.",
      watchRemoved: "شلنا التنبيه.", watchNew: (n) => `${n} جديدة`, watchNone: "مفيش جديد", watchTitle: "تنبيهاتي",
      watchShowing: (l) => `الوظايف الجديدة لـ «${l}»`, watchAll: "اعرض كل الوظايف", watchDel: (l) => `شيل تنبيه «${l}»`,
      watchAll0: "كل وظايف التك", watchMax: "تقدر تحتفظ بـ 8 تنبيهات بس. شيل واحد الأول.",
      watchNotify: "🔔 بلّغني لما تنزل وظايف جديدة", watchNotifyOn: "الإشعارات شغالة",
      watchNotifyHint: "موبايلك هيظهر إشعار صغير لما وظايف اليوم تنزل. مفيش أي حاجة عنك بتتبعت.",
      watchInstall: "نزّل رادارك كتطبيق علشان تشوف عدد الوظايف الجديدة على الأيقونة.",
      notifyTitle: "وظايف جديدة على رادارك", notifyBody: "وظايف النهارده نزلت. افتح رادارك وشوف الجديد في تنبيهاتك.",
      viewedTag: "اتفتحت", coPage: (c) => `${c}: كل الوظايف وسرعة التوظيف والمهارات`, hideCo: (c) => `خبّي وظايف ${c}`, hidCo: (c) => `خبّينا وظايف ${c}.`, undo: "تراجع",
      hiddenCos: (n) => `${n} ${n === 1 ? "شركة متخبّية" : "شركات متخبّية"}`,
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
      <p>Company career boards (Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Recruitee, Personio, and the Workday and SuccessFactors career sites of large employers) and job APIs. Every job links to its original posting, where you apply. Some jobs carry their source's credit (for example, Jobs by Adzuna or via Remote OK).</p>
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
  let insightsData = null, insIdx = 0;                  // data/insights.json: today's insight first
  let meta = null, jobs = [], regionOf = {}, shown = PAGE, groups = [], current = [];
  // The job list comes in two files: data/jobs.json (remote + Middle East & Africa, what most visitors need)
  // and data/jobs-more.json (everything else), fetched only when the visitor looks beyond those regions.
  let more = "none";                                    // none | loading | done | failed
  let morePromise = null;
  let mySkills = new Set(store.get("mySkills", []));
  let savedJobs = store.get("saved", {});               // id -> {t, c, l, u, sv: saved day, a: applied day}
  let savedView = "all";                                // Saved tab: all | todo | done | talks
  // jobs this visitor already opened (dimmed in the list) and companies they chose to hide - only in this browser
  const viewedJobs = new Set(store.get("viewed", []));
  const hiddenCos = new Set(store.get("hiddenCos", []));
  const coKey = (c) => String(c || "").trim().toLowerCase();
  function markViewed(id) {
    if (!id || viewedJobs.has(id)) return;
    viewedJobs.add(id); store.set("viewed", [...viewedJobs].slice(-1500));
    document.querySelectorAll("#jobList > li.job").forEach((li) => { if (li.dataset.jid === id) li.classList.add("seen"); });
  }
  // ---- "My alerts": saved searches, checked on every visit (only in this browser; nothing is sent)
  // {id, h: the search as URL params, l: label, since: data date of the last look}
  let watches = store.get("watches", []);
  let watchView = null;                                 // {id, since} while showing one alert's new jobs
  const WATCH_MAX = 8;
  const searchParams = () => {
    const h = new URLSearchParams();
    FIELDS.forEach((f) => { if (f !== "sort" && $(f).value) h.set(f, $(f).value); });
    Object.entries(quick).forEach(([k, v]) => { if (k !== "fresh" && v !== (k === "hideNat")) h.set(k, v ? "1" : "0"); });
    h.sort();
    return h.toString();
  };
  function searchLabel() {
    const parts = [];
    const role = $("role").value, sel = $("role");
    if (role) parts.push((sel.options[sel.selectedIndex] || {}).text || role.replace(/^\w+:/, ""));
    ["q", "skill", "seniority", "workMode"].forEach((f) => { if ($(f).value) parts.push($(f).value); });
    if ($("country").value) parts.push($("country").value);
    if (quick.remote) parts.push(t("remote"));
    if (quick.visa) parts.push("visa");
    return parts.join(" · ") || t("watchAll0");
  }
  // run the normal filters with a saved search, without touching what's on screen
  function jobsFor(params) {
    const h = new URLSearchParams(params), keep = {}, keepQ = { ...quick }, keepView = watchView;
    FIELDS.forEach((f) => { keep[f] = $(f).value; $(f).value = h.get(f) || (f === "sort" ? "new" : ""); });
    Object.keys(quick).forEach((k) => { quick[k] = h.has(k) ? h.get(k) === "1" : k === "hideNat"; });
    watchView = null;
    try { return filtered(); } finally {
      FIELDS.forEach((f) => { $(f).value = keep[f]; });
      Object.assign(quick, keepQ); watchView = keepView;
    }
  }
  const dataDay = () => (meta.generated_at || "").slice(0, 10);
  let watchMemo = { key: "", counts: [] };
  function watchCounts() {
    const key = JSON.stringify(watches) + "|" + JSON.stringify(watchView) + "|" + jobs.length + "|" + hiddenCos.size + "|" + hiddenJobs.size;
    if (key === watchMemo.key) return watchMemo.counts;
    watchMemo = { key, counts: watchCountsNow() };
    return watchMemo.counts;
  }
  function watchCountsNow() {
    return watches.map((w) => {
      const seen = new Set(), since = watchView && watchView.id === w.id ? watchView.since : w.since;
      jobsFor(w.h).forEach((j) => { if ((j.fs || j.p || "") > since) seen.add(j.t.toLowerCase() + "|" + (j.c || "").toLowerCase()); });
      return seen.size;
    });
  }
  function renderWatches() {
    const bar = $("watchBar"), cur = searchParams(), on = watches.some((w) => w.h === cur);
    $("watchAdd").setAttribute("aria-pressed", String(on));
    $("watchAddLabel").textContent = on ? t("watchOn") : t("watchAdd");
    $("watchAdd").title = on ? t("watchOn") : t("watchAdd");
    if (!watches.length) { bar.hidden = true; setBadge(0); return; }
    const counts = watchCounts(), total = counts.reduce((a, b) => a + b, 0);
    setBadge(total);
    const view = watchView && watches.find((w) => w.id === watchView.id);
    // background checks only work in the installed app (Chrome / Edge on Android and desktop)
    const canNotify = standalone() && "serviceWorker" in navigator && "Notification" in window && "PeriodicSyncManager" in window;
    const notifyOn = canNotify && Notification.permission === "granted" && store.get("notify", false);
    bar.innerHTML = `<div class="watchhead"><h3>🔔 ${esc(t("watchTitle"))}</h3>
        ${canNotify && !notifyOn ? `<button type="button" class="linkbtn" id="watchNotify">${esc(t("watchNotify"))}</button>`
          : notifyOn ? `<span class="muted">✓ ${esc(t("watchNotifyOn"))}</span>`
          : !standalone() ? `<span class="muted">${esc(t("watchInstall"))}</span>` : ""}</div>
      <div class="watchlist">${watches.map((w, i) => `<span class="watch${view && view.id === w.id ? " on" : ""}${counts[i] ? " hasnew" : ""}">
        <button type="button" class="wopen" data-watch="${esc(w.id)}"><b>${esc(w.l)}</b><span class="wn">${counts[i] ? esc(t("watchNew")(num(counts[i]))) : esc(t("watchNone"))}</span></button>
        <button type="button" class="wdel" data-watch-del="${esc(w.id)}" aria-label="${esc(t("watchDel")(w.l))}" title="${esc(t("watchDel")(w.l))}">×</button></span>`).join("")}</div>
      ${view ? `<p class="watchview">${esc(t("watchShowing")(view.l))} · <button type="button" class="linkbtn" id="watchAllBtn">${esc(t("watchAll"))}</button></p>` : ""}`;
    bar.hidden = false;
  }
  function setBadge(n) {
    try {
      if (n && navigator.setAppBadge) navigator.setAppBadge(n);
      else if (!n && navigator.clearAppBadge) navigator.clearAppBadge();
    } catch { /* not supported */ }
  }
  function toggleWatch() {
    const cur = searchParams(), i = watches.findIndex((w) => w.h === cur);
    if (i >= 0) { watches.splice(i, 1); toast(t("watchRemoved")); }
    else {
      if (watches.length >= WATCH_MAX) { toast(t("watchMax")); return; }
      watches.push({ id: Math.random().toString(36).slice(2, 9), h: cur, l: searchLabel(), since: dataDay() });
      track("alert-add"); toast(t("watchSaved"));
    }
    store.set("watches", watches); renderWatches();
  }
  function openWatch(id) {
    const w = watches.find((x) => x.id === id);
    if (!w) return;
    const h = new URLSearchParams(w.h);
    FIELDS.forEach((f) => { if (f !== "sort") $(f).value = h.get(f) || (f === "country" ? "" : ""); });
    Object.keys(quick).forEach((k) => { quick[k] = h.has(k) ? h.get(k) === "1" : k === "hideNat"; });
    syncToggles();
    watchView = { id: w.id, since: w.since };
    w.since = dataDay();                               // looked at: next visit counts from today
    store.set("watches", watches);
    track("alert-open");
    update();
    $("jobs").scrollIntoView({ behavior: "smooth", block: "start" });
  }
  async function turnOnNotify() {
    try {
      if (await Notification.requestPermission() !== "granted") return;
      const reg = await navigator.serviceWorker.ready;
      await reg.periodicSync.register("radarak-new-jobs", { minInterval: 12 * 60 * 60 * 1000 });
      store.set("notify", true); track("alert-notify-on");
    } catch { /* the browser said no (not installed, or not allowed) */ }
    renderWatches();
  }
  // tell the service worker which day's data this visitor has seen, so it only notifies about newer days
  function markDataSeen() {
    try { caches.open("radarak-state").then((c) => c.put("seen-day", new Response(dataDay()))); } catch { /* no cache API */ }
  }
  const STAGES = ["applied", "interview", "offer", "rejected"];
  const daysSince = (iso) => Math.floor((Date.now() - new Date(iso + "T12:00:00Z").getTime()) / 864e5);
  const stageOf = (s) => (s && s.a ? (STAGES.includes(s.st) ? s.st : "applied") : "");
  const quick = { remote: false, visa: false, junior: false, pay: false, week: false, hideNat: true, fresh: false };
  const NOT_IN_LINKS = new Set(["fresh"]);              // "new for me" depends on the visitor, so shared links don't carry it
  let newSince = null;                                  // day of the data the visitor saw on their previous visit
  const hiddenJobs = new Set(store.get("hidden", []));  // jobs this visitor reported as closed
  const isNew = (j) => !!newSince && (j.fs || j.p) > newSince;
  const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
  const shortDate = (iso) => new Date(iso + "T12:00:00Z").toLocaleDateString(lang === "ar" ? "ar-EG" : "en-GB", { day: "numeric", month: "short" });
  const openLocs = new Set();
  const t = (k) => T[lang][k] ?? T.en[k] ?? k;
  // Remote OK's terms ask for a normal (followed) link back; every other job link is nofollow.
  const linkRel = (j) => (j && j.df ? "noopener" : "noopener nofollow");
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
    "Embedded & Chip Design": "emb", "Clients & Projects": "biz",
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
    // only touch text that changes: re-writing the same heading makes the browser paint it again,
    // which counts as a late "largest paint" once the job data arrives
    document.querySelectorAll("[data-i18n]").forEach((el) => { const v = t(el.dataset.i18n); if (el.textContent !== v) el.textContent = v; });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { const v = t(el.dataset.i18nPlaceholder); if (el.placeholder !== v) el.placeholder = v; });
    document.querySelectorAll("[data-i18n-aria]").forEach((el) => { const v = t(el.dataset.i18nAria); if (el.getAttribute("aria-label") !== v) el.setAttribute("aria-label", v); });
    const btn = $("lang");
    btn.textContent = lang === "ar" ? "English" : "العربية";
    btn.lang = lang === "ar" ? "en" : "ar";
    $("aboutText").innerHTML = ABOUT[lang];
    if ($("kit") && !$("kit").hidden) renderKit();
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
      if (watchView && (j.fs || j.p || "") <= watchView.since) return false;
      if (hiddenJobs.has(j.id)) return false;
      if (hiddenCos.size && hiddenCos.has(coKey(j.c))) return false;
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
    else { out.sort(byNew); return spreadCompanies(out); }
    return out;
  }
  // Newest first, but one company that posted 30 jobs today shouldn't fill the whole first screen.
  // A company's 3rd and 4th job of a day are listed as if a day older, the 5th and 6th two days older, and so
  // on (at most a week); within each day, companies take turns (round robin) in the order they first appear.
  const dayNum = (iso) => Math.round(Date.parse(iso + "T12:00:00Z") / 864e5);
  function spreadCompanies(list) {
    const rank = new Map();
    const keyed = list.map((g, i) => {
      const c = (g.job.c || g.key).toLowerCase(), k = g.job.p + "|" + c, r = rank.get(k) || 0;
      rank.set(k, r + 1);
      return { g, c, i, day: dayNum(g.job.p) - Math.min(7, Math.floor(r / 2)) };
    });
    keyed.sort((a, b) => b.day - a.day || a.i - b.i);
    const res = [];
    for (let i = 0; i < keyed.length;) {
      let k = i;
      while (k < keyed.length && keyed[k].day === keyed[i].day) k++;
      const queues = new Map();
      for (const x of keyed.slice(i, k)) {
        if (!queues.has(x.c)) queues.set(x.c, []);
        queues.get(x.c).push(x.g);
      }
      const qs = [...queues.values()];
      for (let round = 0, left = k - i; left > 0; round++) {
        for (const q of qs) if (q.length > round) { res.push(q[round]); left--; }
      }
      i = k;
    }
    return res;
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
  // Adzuna hides a job from visitors outside its country ("not available in your region"):
  // for those visitors, offer a search for the same job on the company's own site
  const ADZUNA = "Jobs by Adzuna";
  let myCountry;
  const adzunaFar = (j) => {
    if (j.by !== ADZUNA) return false;
    if (myCountry === undefined) myCountry = guessCountry();
    return !(j.co || []).includes(myCountry);
  };
  const companySearch = (j) => "https://www.google.com/search?q=" + encodeURIComponent(`${j.c || ""} careers "${j.t}"`);
  const jobLink = (j) => location.origin + location.pathname + "#job=" + encodeURIComponent(j.id);
  const waLink = (j) => "https://wa.me/?text=" + encodeURIComponent(t("shareText")(j.t, j.c) + "\n" + jobLink(j));
  function matchRing(have, total) {
    const pct = Math.round((100 * have) / total), r = 17, c = 2 * Math.PI * r;
    const tone = pct >= 60 ? "hi" : pct >= 30 ? "mid" : "lo";
    return `<span class="ring ${tone}" role="img" aria-label="${esc(t("matchOf")(have, total))}" title="${esc(t("matchOf")(have, total))}">
      <svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="${r}"/>${pct ? `<circle class="val" cx="20" cy="20" r="${r}"
        stroke-dasharray="${((c * pct) / 100).toFixed(1)} ${c.toFixed(1)}"/>` : ""}</svg><b>${pct}%</b></span>`;
  }

  // "Remote", "Remote job", "Anywhere" next to the Remote badge says nothing new
  const placeText = (j) => (j.w === "Remote" && /^(remote( job| \(anywhere\))?|anywhere|worldwide)$/i.test((j.l || "").trim()) ? "" : j.l || "");
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
      viewedJobs.has(j.id) && !String(g.key).startsWith("saved:") ? `<span class="fact seentag">${t("viewedTag")}</span>` : "",
    ].join("");
    const ks = [...j.k].sort((a, b) => (mine.has(b) ? 1 : 0) - (mine.has(a) ? 1 : 0));
    const skills = ks.slice(0, SKILLS_SHOWN).map((k) => `<span class="sk${mine.has(k) ? " have" : ""}">${esc(meta.skills[k])}</span>`).join("")
      + (ks.length > SKILLS_SHOWN ? `<span class="sk skmore">+${ks.length - SKILLS_SHOWN}</span>` : "");
    const isSaved = !!savedJobs[j.id];
    const locsOpen = openLocs.has(g.key);
    const initial = (j.c || j.t || "?").trim().charAt(0).toUpperCase();
    const seen = viewedJobs.has(j.id) && !String(g.key).startsWith("saved:");
    return `<li class="job${seen ? " seen" : ""}" style="${tc(j.tr)}" data-jid="${esc(j.id)}">
      <span class="avatar" aria-hidden="true">${esc(initial)}</span>
      <div class="jmain">
        <h3><a href="${esc(j.u)}" target="_blank" rel="${linkRel(j)}">${esc(j.t)}</a></h3>
        <p class="where"><b>${esc(j.c || "")}</b><span>${esc(placeText(j))}</span>${others > 0
          ? `<button type="button" class="locbtn" data-key="${esc(g.key)}" aria-expanded="${locsOpen}">${locsOpen ? t("hideLocs") : t("moreLocs")(others)}</button>` : ""}</p>
        <div class="facts">${facts}</div>
        ${j.k.length ? `<div class="skills">${skills}</div>` : ""}
        ${j.by ? `<p class="credit">${esc(j.by)}${adzunaFar(j) && j.c ? ` · <a href="${esc(companySearch(j))}" target="_blank" rel="noopener nofollow">${t("cardFind")}</a>` : ""}</p>` : ""}
        ${locsOpen ? `<ul class="locs">${g.all.slice(1).map((x) => `<li><a href="${esc(x.u)}" target="_blank" rel="${linkRel(x)}">${esc(x.l || x.t)}</a></li>`).join("")}</ul>` : ""}
      </div>
      <div class="jside">
        ${mine.size && j.k.length ? matchRing(g.have, j.k.length) : ""}
        <span class="age">${f & FLAG.longOpen ? t("longOpen") : ago(j.p)}${j.by ? `<i class="by"> · ${esc(j.by)}</i>` : ""}</span>
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
    const rows = groups.slice(0, shown).map(jobRow);
    if (insightsData && insightsData.items.length && rows.length >= 6) rows.splice(4, 0, insightCard());
    list.innerHTML = rows.join("");
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
    const known = more === "done" || !(meta && meta.more_jobs);       // until then, a missing job may just be in the other file
    const keep = ids.filter((id) => open.has(id) || (known && savedJobs[id].a));
    const todo = keep.filter((id) => !savedJobs[id].a && open.has(id)), done = keep.filter((id) => savedJobs[id].a);
    const talks = done.filter((id) => ["interview", "offer"].includes(stageOf(savedJobs[id])));
    $("savedCount").hidden = !todo.length;
    $("savedCount").textContent = todo.length;
    if ($("saved").hidden) return;
    const tabs = [["all", t("savedAll"), keep.length], ["todo", t("savedTodo"), todo.length], ["done", t("savedDone"), done.length]];
    if (talks.length || savedView === "talks") tabs.push(["talks", t("savedTalks"), talks.length]);
    // your job hunt at a glance: how many applications, how many turned into interviews and offers
    const n = (st) => done.filter((id) => stageOf(savedJobs[id]) === st).length;
    const replied = n("interview") + n("offer") + n("rejected");
    const pipe = done.length ? `<div class="pipeline" id="pipeline">
        <span><b>${num(done.length)}</b> ${esc(t("pipeApplied"))}</span>
        <span class="pi"><b>${num(n("interview") + n("offer"))}</b> ${esc(t("pipeTalks"))}</span>
        <span class="po"><b>${num(n("offer"))}</b> ${esc(t("pipeOffers"))}</span>
        ${done.length >= 3 ? `<span class="pr">${esc(t("pipeRate")(Math.round((100 * replied) / done.length)))}</span>` : ""}</div>` : "";
    $("savedTabs").innerHTML = pipe + `<div class="stabs">` + tabs
      .map(([v, label, n]) => `<button type="button" class="stab${savedView === v ? " on" : ""}" data-saved-view="${v}" aria-pressed="${savedView === v}">${esc(label)} <span class="n">${num(n)}</span></button>`).join("") + `</div>`;
    const list = savedView === "todo" ? todo : savedView === "done" ? done : savedView === "talks" ? talks : keep;
    const byDay = (id) => savedJobs[id].a || savedJobs[id].sv || "";
    list.sort((a, b) => (byDay(a) < byDay(b) ? 1 : -1));
    $("savedList").innerHTML = list.map((id) => {
      const s = savedJobs[id], j = open.get(id);
      const status = `<p class="savedmeta">${s.a ? `<span class="fact applied">✓ ${esc(t("appliedOn")(shortDate(s.a)))}</span>${s.cv ? ` <span class="sentwith">${esc(t("dSentWith")(s.cv))}</span>` : ""}` : s.sv ? esc(t("savedOn")(shortDate(s.sv))) : ""}
        ${s.a ? "" : `<button type="button" class="applybtn" data-applied="${esc(id)}" aria-pressed="false">${CHECK}<span>${t("markApplied")}</span></button>`}
        ${s.a ? `<label class="stage st-${stageOf(s)}"><span class="sr">${esc(t("stageLabel"))}</span><select data-stage="${esc(id)}">${STAGES.map((st) =>
          `<option value="${st}"${stageOf(s) === st ? " selected" : ""}>${esc(t("st" + st[0].toUpperCase() + st.slice(1)))}</option>`).join("")}
          <option value="none">${esc(t("stNone"))}</option></select></label>` : ""}</p>
        ${s.a && stageOf(s) === "applied" && daysSince(s.sd || s.a) >= 7 ? `<p class="followup">💬 ${esc(t("followUp")(daysSince(s.sd || s.a)))}</p>` : ""}`;
      if (j) { const row = jobRow({ key: "saved:" + id, job: j, all: [j], pay: j.$ || null, flags: j.f || 0, have: 0, match: -1 }), at = row.lastIndexOf("</li>");
        return row.slice(0, at) + status + row.slice(at); }
      return `<li class="job closed"><span class="avatar" aria-hidden="true">${esc((s.c || s.t || "?").charAt(0).toUpperCase())}</span>
        <div class="jmain"><h3>${s.u ? `<a class="closedlink" href="${esc(s.u)}" target="_blank" rel="${linkRel(s)}">${esc(s.t)}</a>` : esc(s.t)}</h3>
          <p class="where"><b>${esc(s.c || "")}</b><span>${esc(s.l || "")}</span></p><div class="facts"><span class="fact">${t("closedTag")}</span></div></div>
        <div class="jside"><button type="button" class="linkbtn" data-unsave="${esc(id)}">${t("removeSaved")}</button></div>${status}</li>`;
    }).join("");
    $("savedEmpty").hidden = list.length > 0;
    $("savedEmpty").innerHTML = keep.length ? esc(t("savedNone")) : `<div class="emptystate"><span class="eicon" aria-hidden="true">🔖</span>
      <p><b>${esc(t("savedEmptyTitle"))}</b><br>${esc(t("savedEmpty"))}</p>
      <div class="erow"><button type="button" class="primary" data-gotab="jobs">${esc(t("savedBrowse"))}</button>
      ${kit.cvs.length ? "" : `<button type="button" class="chipbtn" data-gotab="kit">${esc(t("dKitBtn"))}</button>`}</div></div>`;
  }
  function toggleSaved(id) {
    const j = jobs.find((x) => x.id === id);
    if (savedJobs[id]) delete savedJobs[id];
    else if (j) { savedJobs[id] = { t: j.t, c: j.c, l: j.l, u: j.u, df: j.df, sv: today() }; track("save-job"); }
    store.set("saved", savedJobs);
  }
  function toggleApplied(id) {
    const j = jobs.find((x) => x.id === id);
    if (!savedJobs[id]) { if (!j) return; savedJobs[id] = { t: j.t, c: j.c, l: j.l, u: j.u, df: j.df, sv: today() }; }
    if (savedJobs[id].a) { delete savedJobs[id].a; delete savedJobs[id].cv; }
    else {
      savedJobs[id].a = today(); track("applied");
      const b = j && bestCv(j);                       // which CV you (most likely) sent, for your own records
      if (b) savedJobs[id].cv = b.cv.name;
    }
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
  // extra facts for a skill in the plan: does it pay more, is demand going up (trends.json, when loaded)
  function skillPayLift(skill) {
    // compared inside each place (and level), so "US jobs pay more" doesn't look like "this skill pays more"
    const k = meta.skills.indexOf(skill), groupsBy = new Map();
    current.forEach((j) => {
      if (!j.$) return;
      const key = (j.w === "Remote" ? "Remote" : (j.co || [])[0] || "?") + "|" + (j.s || "");
      if (!groupsBy.has(key)) groupsBy.set(key, { w: [], o: [] });
      groupsBy.get(key)[j.k.includes(k) ? "w" : "o"].push((j.$[0] + j.$[1]) / 2);
    });
    let weight = 0, sum = 0;
    groupsBy.forEach((g) => {
      if (g.w.length < 3 || g.o.length < 3) return;
      sum += g.w.length * (median(g.w) / median(g.o)); weight += g.w.length;
    });
    if (weight < 12) return null;
    const lift = Math.round(100 * (sum / weight - 1));
    return lift >= 5 ? Math.min(lift, 60) : null;     // only when clearly more; never shout huge numbers
  }
  function skillMove(skill) {
    if (!trends || !trends.skills) return 0;
    const sk = trends.skills.All || {};
    if ((sk.rising || []).slice(0, 25).some((r) => r[0] === skill)) return 1;
    if ((sk.falling || []).slice(0, 25).some((r) => r[0] === skill)) return -1;
    return 0;
  }
  function renderLearn() {
    const box = $("learnNext"), plan = learnPlan();
    box.hidden = !plan;
    if (!plan) return;
    const top = Math.max(1, ...plan.steps.map((s) => s.gain));
    box.innerHTML = `<div class="learnhead"><h3>🎯 ${t("learnTitle")}</h3><p>${t("learnNow")(num(plan.start))}</p></div>
      ${plan.steps.length ? `<ol class="learnsteps">${plan.steps.map((s, i) => `<li>
          <span class="lnum">${i + 1}</span>
          <div class="lmain"><b>${esc(s.skill)}${(() => { const m = skillMove(s.skill); return m ? ` <span class="ltrend ${m > 0 ? "up" : "down"}">${m > 0 ? "↑ " + t("learnRising") : "↓ " + t("learnFalling")}</span>` : ""; })()}</b>
            <span class="lbar"><i style="width:${Math.round((100 * s.gain) / top)}%"></i></span>
            ${(() => { const lift = skillPayLift(s.skill); return lift ? `<span class="lpay">💰 ${esc(t("learnPay")(lift))}</span>` : ""; })()}</div>
          <span class="lgain">${t("learnJobs")(num(s.gain))}</span>
          <span class="lbtns"><button type="button" class="linkbtn" data-learn-see="${esc(s.skill)}">${t("learnSee")}</button>
            <button type="button" class="chip add" data-add="${esc(s.skill)}">+ ${t("learnKnow")}</button></span></li>`).join("")}</ol>
        <p class="learntotal">${t("learnTotal")(plan.steps.length, `${num(plan.start)} → ${num(plan.end)}`)}
          <span class="up">+${plan.start ? Math.round((100 * (plan.end - plan.start)) / plan.start) + "%" : num(plan.end - plan.start)}</span></p>
        <p class="hint">${t("learnHint")}${plan.steps.some((s) => skillPayLift(s.skill)) ? " " + t("learnPayHint") : ""}</p>` : `<p class="hint">${t("learnNone")}</p>`}
      <button type="button" class="primary sm sharecard" data-sharecard>📸 ${t("shareCard")}</button>`;
  }

  // ------------------------------------------------------------------ insight of the day (a card in the job list)
  const L = (o) => (o && (o[lang] || o.en)) || "";
  function insightCard() {
    const items = insightsData.items, n = items.length, ins = items[((insIdx % n) + n) % n];
    const bars = ins.bars.map((b) => `<li><span>${esc(L(b.l))}</span><span class="ib"><i style="width:${Math.max(2, Math.round(b.v * 100))}%"></i></span><b>${esc(b.t)}</b></li>`).join("");
    return `<li class="insight" id="insight" aria-label="${esc(t("insKicker"))}">
      <p class="ins-k">📊 ${esc(t("insKicker"))} · ${esc(shortDate(insightsData.date))}</p>
      <div class="ins-main"><b class="ins-big">${esc(ins.big)}</b><div><h3>${esc(L(ins.title))}</h3><p>${esc(L(ins.big_label))}</p></div></div>
      <ul class="ins-bars">${bars}</ul>
      <p class="ins-note">${esc(L(ins.note))}</p>
      <div class="ins-act">
        <span class="ins-nav"><button type="button" data-ins="prev" aria-label="${esc(t("insPrev"))}">‹</button><span>${(((insIdx % n) + n) % n) + 1} / ${n}</span><button type="button" data-ins="next" aria-label="${esc(t("insNext"))}">›</button></span>
        ${ins.link ? `<a class="linkbtn" href="${esc(ins.link)}" data-ins="go">${esc(t("insSee"))} →</a>` : ""}
        <button type="button" class="ghostbtn sm" data-ins="img">📸 ${esc(t("insImg"))}</button>
      </div></li>`;
  }
  function onInsightClick(e) {
    const b = e.target.closest("[data-ins]");
    if (!b || !insightsData) return;
    const what = b.dataset.ins;
    if (what === "prev" || what === "next") {
      insIdx += what === "next" ? 1 : -1;
      const el = $("insight");
      if (el) el.outerHTML = insightCard();
      track("insight-" + what);
    } else if (what === "img") { insightImage(); }
    else if (what === "go") { track("insight-go"); }
  }
  async function insightImage() {
    const items = insightsData.items, n = items.length, ins = items[((insIdx % n) + n) % n];
    track("insight-image/" + ins.id);
    const W = 1080, H = 1350, P = 80, rtl = lang === "ar";
    const D = '"Bricolage Grotesque", "IBM Plex Sans Arabic", sans-serif', F = '"IBM Plex Sans Arabic", system-ui, sans-serif';
    try { await Promise.all(["800 80px " + D, "700 40px " + F, "500 30px " + F].map((f) => document.fonts.load(f))); } catch { /* system fonts */ }
    const cv = document.createElement("canvas"); cv.width = W; cv.height = H;
    const ctx = cv.getContext("2d");
    ctx.fillStyle = "#0F1222"; ctx.fillRect(0, 0, W, H);
    const glow = ctx.createRadialGradient(W, 0, 0, W, 0, 760); glow.addColorStop(0, "rgba(10,132,255,.35)"); glow.addColorStop(1, "rgba(15,18,34,0)");
    ctx.fillStyle = glow; ctx.fillRect(0, 0, W, H);
    ctx.direction = rtl ? "rtl" : "ltr";
    const X = (x) => (rtl ? W - x : x);
    const text = (s, x, y, font, color, align) => { ctx.font = font; ctx.fillStyle = color; ctx.textAlign = align || (rtl ? "right" : "left"); ctx.fillText(s, X(x), y); };
    text("Radarak", P, 130, "800 48px " + D, "#FFFFFF");
    text("📊 " + t("insKicker") + " · " + shortDate(insightsData.date), P, 210, "700 30px " + F, "#8FC1FF");
    ctx.font = "800 58px " + D;
    const title = wrapLines(ctx, L(ins.title), W - 2 * P).slice(0, 4);
    title.forEach((l, i) => text(l, P, 300 + i * 70, "800 58px " + D, "#FFFFFF"));
    let y = 300 + title.length * 70 + 130;
    text(ins.big, P, y, "800 130px " + D, "#0A84FF");
    ctx.font = "600 32px " + F;
    wrapLines(ctx, L(ins.big_label), W - 2 * P).slice(0, 2).forEach((l, i) => text(l, P, y + 56 + i * 42, "600 32px " + F, "#C7CCDB"));
    y += 130;
    const bars = ins.bars.slice(0, 5), rowH = bars.length > 3 ? 58 : 66;
    roundRect(ctx, P, y, W - 2 * P, 50 + bars.length * rowH, 26); ctx.fillStyle = "rgba(255,255,255,.06)"; ctx.fill();
    bars.forEach((b, i) => {
      const ry = y + 66 + i * rowH;
      text(L(b.l), P + 34, ry, "600 32px " + F, "#FFFFFF");
      text(b.t, W - P - 34, ry, "700 32px " + F, "#FFFFFF", rtl ? "left" : "right");
      const bw = Math.max(6, 300 * b.v), bx = rtl ? P + 34 + 130 : W - P - 34 - 130 - 300;
      roundRect(ctx, bx, ry - 22, 300, 14, 7); ctx.fillStyle = "rgba(255,255,255,.12)"; ctx.fill();
      roundRect(ctx, rtl ? bx + 300 - bw : bx, ry - 22, bw, 14, 7); ctx.fillStyle = "#0A84FF"; ctx.fill();
    });
    ctx.font = "500 28px " + F;
    const noteY = Math.min(H - 228, Math.max(y + 50 + bars.length * rowH + 60, H - 300));
    wrapLines(ctx, L(ins.note), W - 2 * P).slice(0, 1).forEach((l) => text(l, P, noteY, "500 28px " + F, "#C7CCDB"));
    roundRect(ctx, P, H - 190, W - 2 * P, 96, 48); ctx.fillStyle = "#FFFFFF"; ctx.fill();
    text("radarak.online", W / 2, H - 126, "800 46px " + D, "#0F1222", "center");
    text(t("insChannels"), W / 2, H - 44, "500 26px " + F, "rgba(255,255,255,.6)", "center");
    const blob = await new Promise((r) => cv.toBlob(r, "image/png"));
    if (!blob) return;
    const file = new File([blob], `radarak-insight-${insightsData.date}.png`, { type: "image/png" });
    try {
      if (navigator.canShare && navigator.canShare({ files: [file] })) { await navigator.share({ files: [file], text: L(ins.title) + " · radarak.online" }); return; }
    } catch (e) { if (e && e.name === "AbortError") return; }
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = file.name;
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    toast(t("shareCardDone"));
  }

  // ------------------------------------------------------------------ "share my result": an image made in the browser
  // Only counts and skill names go on the card; the CV itself never leaves the device.
  function cardScope() {
    const c = $("country").value, r = $("role").value || "";
    const what = r.startsWith("role:") || r.startsWith("track:") ? r.slice(r.indexOf(":") + 1)
      : quick.remote || $("workMode").value === "Remote" ? t("cardRemote") : t("cardTech");
    return t("cardJobs")(what, c);
  }
  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }
  function wrapLines(ctx, text, max) {
    const words = String(text).split(" "), lines = [];
    let line = "";
    for (const w of words) {
      const next = line ? line + " " + w : w;
      if (ctx.measureText(next).width > max && line) { lines.push(line); line = w; } else line = next;
    }
    if (line) lines.push(line);
    return lines;
  }
  async function makeCard() {
    const W = 1080, H = 1350, P = 84, rtl = lang === "ar";
    const D = '"Bricolage Grotesque", "IBM Plex Sans Arabic", sans-serif', F = '"IBM Plex Sans Arabic", system-ui, sans-serif';
    try { await Promise.all(["800 80px " + D, "700 40px " + F, "500 30px " + F].map((f) => document.fonts.load(f))); } catch { /* system fonts */ }
    const cv = document.createElement("canvas"); cv.width = W; cv.height = H;
    const ctx = cv.getContext("2d");
    ctx.fillStyle = "#0F1222"; ctx.fillRect(0, 0, W, H);
    [[W * 0.95, 60, 680, "rgba(10,132,255,.40)"], [40, H - 80, 560, "rgba(94,92,230,.28)"]].forEach(([x, y, r, c]) => {
      const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, c); g.addColorStop(1, "rgba(23,17,58,0)");
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    });
    ctx.strokeStyle = "rgba(255,255,255,.08)"; ctx.lineWidth = 2;
    [140, 230, 320].forEach((r) => { ctx.beginPath(); ctx.arc(W - 150, 190, r, 0, Math.PI * 2); ctx.stroke(); });
    ctx.direction = rtl ? "rtl" : "ltr";
    const X = (x) => (rtl ? W - x : x);
    const text = (s, x, y, font, color, align) => { ctx.font = font; ctx.fillStyle = color; ctx.textAlign = align || (rtl ? "right" : "left"); ctx.fillText(s, X(x), y); };
    // brand
    const lx = X(P + 30);
    ctx.fillStyle = "#0A84FF"; ctx.beginPath(); ctx.arc(lx, 128, 30, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,.55)"; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(lx, 128, 16, 0, Math.PI * 2); ctx.stroke();
    [[12, -12, 6, "#FFFFFF"], [-12, 7, 5, "#64D2FF"], [7, 13, 4, "#30D158"]].forEach(([dx, dy, r, c]) => { ctx.fillStyle = c; ctx.beginPath(); ctx.arc(lx + dx, 128 + dy, r, 0, Math.PI * 2); ctx.fill(); });
    text("Radarak", P + 76, 146, "800 50px " + D, "#FFFFFF");
    // the number
    const plan = learnPlan() || { start: 0, steps: [] };
    text(t("cardMatch"), P, 300, "600 44px " + F, "#C7CCDB");
    text(num(plan.start), P, 520, "800 230px " + D, "#FFFFFF");
    ctx.font = "700 54px " + F;
    const scope = wrapLines(ctx, cardScope(), W - 2 * P);
    scope.slice(0, 2).forEach((l, i) => text(l, P, 610 + i * 66, "700 54px " + F, "#FFFFFF"));
    // next skills (or the skills they have)
    let y = 610 + Math.min(2, scope.length) * 66 + 50;
    roundRect(ctx, P, y, W - 2 * P, 360, 28); ctx.fillStyle = "rgba(255,255,255,.08)"; ctx.fill();
    const steps = plan.steps.slice(0, 3);
    text(steps.length ? t("cardNext") : t("cardHave"), P + 36, y + 70, "700 34px " + F, "#FFB020");
    const top = Math.max(1, ...steps.map((s) => s.gain));
    const rows = steps.length ? steps : [...mySkills].slice(0, 3).map((s) => ({ skill: s }));
    rows.forEach((s, i) => {
      const ry = y + 140 + i * 82;
      text(s.skill, P + 36, ry, "700 40px " + F, "#FFFFFF");
      if (s.gain) {
        text(t("cardJobsN")(num(s.gain)), W - P - 36, ry, "700 36px " + F, "#4ADE9B", rtl ? "left" : "right");
        const bw = 300 * s.gain / top, bx = rtl ? P + 36 + 230 : W - P - 36 - 230 - bw;
        roundRect(ctx, bx, ry - 24, bw, 16, 8); ctx.fillStyle = "#0A84FF"; ctx.fill();
      }
    });
    // call to action
    y += 410;
    text(t("cardCta"), P, y, "600 34px " + F, "#C7CCDB");
    const g = ctx.createLinearGradient(P, 0, W - P, 0); g.addColorStop(0, "#0A84FF"); g.addColorStop(1, "#5E5CE6");
    roundRect(ctx, P, y + 30, W - 2 * P, 104, 52); ctx.fillStyle = g; ctx.fill();
    text("radarak.online", W / 2, y + 100, "800 52px " + D, "#FFFFFF", "center");
    text(t("cardPrivacy"), W / 2, H - 52, "500 26px " + F, "rgba(255,255,255,.55)", "center");
    return new Promise((resolve) => cv.toBlob(resolve, "image/png"));
  }
  async function shareCard() {
    track("share-card");
    const blob = await makeCard();
    if (!blob) return;
    const file = new File([blob], "radarak-my-match.png", { type: "image/png" });
    const url = location.origin + location.pathname;
    try {
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], text: t("cardShareText") + " " + url });
        return;
      }
    } catch (e) { if (e && e.name === "AbortError") return; }
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = file.name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    toast(t("shareCardDone"));
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

  let lastCv = null;
  const pastedCv = (text) => new File([text], "my-cv.txt", { type: "text/plain" });          // the CV just read in the skills box, so it can go into the Apply kit in one tap
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
    // same count as "What to learn next" and the share card: each job once, the way the list shows it
    const plan0 = learnPlan();
    const matched = plan0 ? plan0.start : current.filter((j) => j.k.length && j.k.filter((k) => mine.has(k)).length / j.k.length >= MATCH).length;
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
      ${(() => { const pl = learnPlan(), st = pl && pl.steps[0]; return st ? `<p class="learntop">${t("learnTop")(esc(st.skill), num(st.gain))}</p>` : ""; })()}
      <p class="hint">${t("cvAdded")}</p>
      ${gaps.length ? `<div class="gap"><p><b>${t("cvGapTitle")}</b></p><p class="hint">${t("cvGapHint")}</p>
        <div class="chips">${gaps.map((s) => `<button type="button" class="chip add" data-add="${esc(s)}">+ ${esc(s)}</button>`).join("")}</div></div>` : ""}
      <button type="button" class="linkbtn learnjump" id="learnJump">${t("learnTitle")} ↓</button>
      <div class="actions">
        <button type="button" class="primary" id="cvBestBtn">${t("cvShowBest")} →</button>
        ${role ? `<button type="button" class="chipbtn" id="cvRoleBtn">${esc(t("cvShowRole")(role))}</button>` : ""}
        <button type="button" class="chipbtn sharecard" data-sharecard>📸 ${t("shareCard")}</button>
        <button type="button" class="linkbtn" id="cvClearBtn">${t("cvClear")}</button>
      </div>
      ${lastCv && !kit.cvs.some((c) => c.fileName === lastCv.name) && kit.cvs.length < KIT_MAX_CVS
        ? `<div class="cvtokit"><p>⚡ ${esc(t("cvToKitHint"))}</p><button type="button" class="chipbtn" id="cvToKit">${esc(kit.cvs.length ? t("cvToKitMore") : t("cvToKit"))}</button></div>` : ""}`;
    if ($("cvToKit")) $("cvToKit").addEventListener("click", async (e) => {
      const b = e.currentTarget; b.disabled = true;
      await addKitCv(lastCv);
      b.closest(".cvtokit").innerHTML = `<p>✓ ${esc(t("cvToKitDone"))} <button type="button" class="linkbtn" data-gokit>${esc(t("dEditKit"))} →</button></p>`;
      track("cv-to-kit");
    });
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
      lastCv = file;
      useCvText(text);
    } catch {
      cvStatus(t("cvFail"), true);
    } finally {
      $("cvBtn").disabled = false; $("cvFile").value = "";
    }
  }

  // ------------------------------------------------------------------ Apply kit: details, CVs and letters, all on this device
  // Details and CV facts (skills, years) live in localStorage; the CV files themselves in IndexedDB.
  // Nothing here is ever sent anywhere.
  const KIT_FIELDS = [   // key, label, input type, autocomplete, placeholder
    ["first", "kFirst", "text", "given-name"], ["last", "kLast", "text", "family-name"], ["email", "kEmail", "email", "email"],
    ["phone", "kPhone", "tel", "tel"], ["country", "kCountry", "text", "country-name"], ["city", "kCity", "text", "address-level2"],
    ["linkedin", "kLinkedin", "url", "url"], ["portfolio", "kPortfolio", "url", "url"], ["years", "kYears", "number", "off"],
    ["notice", "kNotice", "text", "off", "kNoticePh"], ["salary", "kSalary", "text", "off", "kSalaryPh"],
  ];
  const KIT_MAX_CVS = 5;
  let kit = store.get("kit", null) || { profile: {}, cvs: [], letters: [] };
  kit.profile = kit.profile || {}; kit.cvs = kit.cvs || []; kit.letters = kit.letters || [];
  // The Radarak Apply browser extension (computers) asks the page for the kit with window.postMessage;
  // the kit and CV files go to the extension in this same browser and nowhere else.
  const extOn = () => document.documentElement.dataset.radarakExt === "1";
  async function kitForExtension() {
    const files = [];
    for (const cv of kit.cvs) {
      const rec = await cvFiles.get(cv.id);
      if (rec && rec.blob) files.push({ id: cv.id, blob: rec.blob, fileName: rec.fileName, type: rec.type });
    }
    window.postMessage({ type: "radarak-kit-data", kit, files }, location.origin);
  }
  window.addEventListener("message", (e) => {
    if (e.source === window && e.data && e.data.type === "radarak-ext-hello") {
      kitForExtension();
      const k = $("kit"); if (k && !k.hidden) renderKit();
    }
  });
  let extPush = 0;
  const saveKit = () => {
    store.set("kit", kit);
    renderKitPick();
    if (extOn()) { clearTimeout(extPush); extPush = setTimeout(kitForExtension, 400); }
  };
  const kitHasData = () => kit.cvs.length > 0 || Object.values(kit.profile).some((v) => String(v || "").trim());

  // a tiny IndexedDB key-value store for the CV files (localStorage is too small for files)
  const cvFiles = (() => {
    let dbp = null;
    const open = () => (dbp = dbp || new Promise((ok, no) => {
      try {
        const r = indexedDB.open("radarak", 1);
        r.onupgradeneeded = () => r.result.createObjectStore("cvs");
        r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error);
      } catch (e) { no(e); }
    }));
    const run = async (mode, fn) => {
      const db = await open();
      return new Promise((ok, no) => {
        const tx = db.transaction("cvs", mode), req = fn(tx.objectStore("cvs"));
        tx.oncomplete = () => ok(req ? req.result : undefined); tx.onerror = () => no(tx.error); tx.onabort = () => no(tx.error);
      });
    };
    const mem = new Map();          // fallback when IndexedDB is blocked (some private windows)
    let ok = true;
    return {
      async put(id, v) { try { if (ok) return await run("readwrite", (s) => s.put(v, id)); } catch { ok = false; } mem.set(id, v); return null; },
      async get(id) { try { if (ok) return await run("readonly", (s) => s.get(id)); } catch { ok = false; } return mem.get(id); },
      async del(id) { try { if (ok) return await run("readwrite", (s) => s.delete(id)); } catch { ok = false; } mem.delete(id); return null; },
      get persistent() { return ok; },
    };
  })();

  async function fileText(file) {
    const name = file.name.toLowerCase();
    const kind = name.endsWith(".pdf") || file.type === "application/pdf" ? "pdf"
      : name.endsWith(".docx") ? "docx" : name.endsWith(".txt") || file.type.startsWith("text/") ? "txt" : null;
    if (!kind) throw new Error("type");
    return kind === "txt" ? file.text() : kind === "pdf" ? pdfText(await file.arrayBuffer()) : docxText(await file.arrayBuffer());
  }

  // how well one CV covers a job: its skills that the job asks for, and the ones it doesn't mention
  function cvFit(cv, j) {
    const have = new Set((cv.skills || []).map((s) => meta.skills.indexOf(s)).filter((i) => i >= 0));
    const hit = j.k.filter((k) => have.has(k)), miss = j.k.filter((k) => !have.has(k));
    return { cv, pct: j.k.length ? Math.round((100 * hit.length) / j.k.length) : 0, hit, miss };
  }
  function bestCv(j) {
    if (!kit.cvs.length || !j.k.length) return null;
    return kit.cvs.map((cv) => cvFit(cv, j)).sort((a, b) => b.pct - a.pct || a.miss.length - b.miss.length)[0];
  }
  function fillLetter(body, j) {
    const p = kit.profile;
    const vals = { company: j.c || "", job: j.t || "", first: p.first || "", last: p.last || "", years: p.years || "" };
    return String(body || "").replace(/\{(company|job|first|last|years)\}/g, (m, k) => vals[k] || m);
  }

  async function copyText(text, btn) {
    let done = false;
    try { await navigator.clipboard.writeText(text); done = true; } catch { /* older browsers: fall back below */ }
    if (!done) {
      const ta = document.createElement("textarea");
      ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { done = document.execCommand("copy"); } catch { done = false; }
      ta.remove();
    }
    if (done && btn) {
      btn.classList.add("done"); const old = btn.dataset.label || btn.textContent;
      btn.dataset.label = old; btn.querySelector(".cl") ? (btn.querySelector(".cl").textContent = t("copied")) : (btn.textContent = t("copied"));
      setTimeout(() => { btn.classList.remove("done"); if (btn.querySelector(".cl")) btn.querySelector(".cl").textContent = t("copy"); else btn.textContent = old; }, 1600);
    }
    return done;
  }
  async function downloadCv(id) {
    const rec = await cvFiles.get(id);
    if (!rec || !rec.blob) return;
    const url = URL.createObjectURL(rec.blob), a = document.createElement("a");
    a.href = url; a.download = rec.fileName || "cv"; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
    track("kit-cv-download");
  }

  let kitMsg = "", kitJustAdded = null;
  const HALF = new Set(["first", "last", "country", "city", "years", "notice"]);
  function kitSteps() {
    const p = kit.profile;
    return [
      ["details", t("kitStep1"), !!(p.first && p.email && p.phone)],
      ["cvs", t("kitStep2"), kit.cvs.length > 0],
      ["letters", t("kitStep3"), kit.letters.length > 0],
    ];
  }
  function renderKit() {
    const p = kit.profile, el = $("kitBody");
    if (!el) return;
    const steps = kitSteps(), done = steps.filter((x) => x[2]).length;
    const field = ([k, label, type, ac, ph]) => `<label class="kfield${HALF.has(k) ? " half" : ""}"><span>${esc(t(label))}</span>
      <input id="k-${k}" data-kit="${k}" type="${type}" autocomplete="${ac}" ${type === "number" ? 'min="0" max="50" inputmode="numeric"' : ""}
        ${type === "tel" ? 'inputmode="tel"' : ""} ${ph ? `placeholder="${esc(t(ph))}"` : ""} value="${esc(p[k] || "")}" dir="auto"></label>`;
    const cvs = kit.cvs.map((cv) => `<li class="kcv${kitJustAdded === cv.id ? " justadded" : ""}" data-cv="${esc(cv.id)}">
        <span class="kcvicon" aria-hidden="true">📄</span>
        <div class="kcvmain"><input class="kcvname" data-cvname="${esc(cv.id)}" value="${esc(cv.name)}" aria-label="${esc(t("kitCvName"))}" dir="auto">
          <p class="kcvfacts">${esc(cv.fileName || "")} · ${esc(t("kitCvSkills")(cv.skills.length))}${cv.years ? " · " + esc(t("kitCvYears")(cv.years)) : ""}</p>
          <div class="kcvbtns"><button type="button" class="chipbtn" data-cvuse="${esc(cv.id)}">${esc(t("kitUseCv"))}</button>
            <button type="button" class="chipbtn" data-cvdl="${esc(cv.id)}">${esc(t("kitDownload"))}</button>
            <button type="button" class="linkbtn danger" data-cvdel="${esc(cv.id)}">${esc(t("kitDelete"))}</button></div></div></li>`).join("");
    const letters = kit.letters.map((l, i) => `<li class="kletter" data-letter="${esc(l.id)}"><details${i === 0 && kit.letters.length === 1 ? "" : ""}>
        <summary><span>✉️ ${esc(l.name)}</span><small>${esc(t("kitEdit"))}</small></summary>
        <div class="kletterbody"><label class="kfield"><span>${esc(t("kitLetterName"))}</span><input data-lname="${esc(l.id)}" value="${esc(l.name)}" dir="auto"></label>
        <textarea data-lbody="${esc(l.id)}" rows="9" dir="auto" aria-label="${esc(l.name)}">${esc(l.body)}</textarea>
        <button type="button" class="linkbtn danger" data-ldel="${esc(l.id)}">${esc(t("kitDelete"))}</button></div></details></li>`).join("");
    el.innerHTML = `
      <header class="kithead">
        <h2>${esc(t("kitTitle"))}</h2>
        <p>${esc(t("kitIntro"))}</p>
        <ol class="ksteps" aria-label="${esc(t("kitProgress")(done))}">${steps.map(([id, label, ok], i) =>
          `<li class="${ok ? "ok" : ""}"><a href="#k-sec-${id}" data-kitjump="${id}"><b>${ok ? "✓" : i + 1}</b><span>${esc(label)}</span></a></li>`).join("")}</ol>
        ${done === 3 ? `<p class="kready">✓ ${esc(t("kitReady"))} <button type="button" class="linkbtn" data-kitjobs>${esc(t("kitSeeJobs"))} →</button></p>` : ""}
        <p class="kitprivacy">${esc(t("kitPrivacy"))}</p>
        ${cvFiles.persistent ? "" : `<p class="kitwarn">${esc(t("kitNoStorage"))}</p>`}
      </header>
      <div class="kitext">${extOn() ? `<p><b>✓ ${esc(t("extOn"))}</b> ${esc(t("extOnHint"))}</p>`
        : `<p><b>⚡ ${esc(t("extGet"))}</b> ${esc(t("extGetHint"))}</p><a class="ghostbtn" href="extension/" target="_blank" rel="noopener">${esc(t("extGetBtn"))}</a>`}</div>
      <section class="kitsec" id="k-sec-details"><h3><b class="knum">1</b>${esc(t("kitDetails"))}</h3>
        <form class="kgrid" id="kitForm" autocomplete="on" onsubmit="return false">${KIT_FIELDS.map(field).join("")}</form>
        <p class="hint kitsaved" id="kitSavedNote" hidden>✓ ${esc(t("kitSaved"))}</p></section>
      <section class="kitsec" id="k-sec-cvs"><h3><b class="knum">2</b>${esc(t("kitCvs"))} <span class="muted">${kit.cvs.length}/${KIT_MAX_CVS}</span></h3>
        ${kit.cvs.length ? `<ul class="kcvs">${cvs}</ul>` : ""}
        ${kitJustAdded ? `<div class="kadded"><span>✓ ${esc(kitMsg)}</span><button type="button" class="primary" data-cvuse="${esc(kitJustAdded)}">${esc(t("kitSeeJobs"))} →</button></div>`
          : `<p class="kitmsg" id="kitMsg" role="status" aria-live="polite">${esc(kitMsg)}</p>`}
        ${kit.cvs.length < KIT_MAX_CVS ? `<button type="button" class="kdrop" id="kitAddCv"><b>${esc(kit.cvs.length ? t("kitAddCv") : t("kitAddFirstCv"))}</b>
          <span>${esc(t("kitCvHint"))}</span></button>` : `<p class="hint">${esc(t("kitCvMax"))}</p>`}
        <input id="kitCvFile" type="file" accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain" hidden></section>
      <section class="kitsec" id="k-sec-letters"><h3><b class="knum">3</b>${esc(t("kitLetters"))}</h3>
        <p class="hint">${esc(t("kitLetterHelp"))}</p>
        ${kit.letters.length ? `<ul class="kletters">${letters}</ul>` : ""}
        <button type="button" class="chipbtn" id="kitAddLetter">${esc(t("kitAddLetter"))}</button></section>
      <section class="kitsec quiet"><h3>${esc(t("kitBackup"))}</h3>
        <p class="hint">${esc(t("kitBackupHint"))}</p>
        <div class="kitrow"><button type="button" class="chipbtn" id="kitExport">${esc(t("kitExport"))}</button>
          <button type="button" class="chipbtn" id="kitImportBtn">${esc(t("kitImport"))}</button>
          <input id="kitImportFile" type="file" accept=".json,application/json" hidden>
          <button type="button" class="linkbtn danger" id="kitWipe">${esc(t("kitWipe"))}</button></div></section>`;
    kitMsg = ""; kitJustAdded = null;
  }
  // the skills box offers the CVs already in the Apply kit: one CV, one place
  function renderKitPick() {
    const el = $("kitPick");
    if (!el) return;
    el.hidden = !kit.cvs.length;
    el.innerHTML = kit.cvs.length ? `<span>${esc(t("kitPickLabel"))}</span>${kit.cvs.map((cv) =>
      `<button type="button" class="chip" data-kitcv="${esc(cv.id)}">📄 ${esc(cv.name)}</button>`).join("")}` : "";
  }
  function refreshKitSteps() {        // update the 1-2-3 progress while typing, without redrawing the form
    const steps = kitSteps();
    document.querySelectorAll(".ksteps li").forEach((li, i) => {
      li.classList.toggle("ok", steps[i][2]);
      const b = li.querySelector("b"); if (b) b.textContent = steps[i][2] ? "✓" : String(i + 1);
    });
  }

  let kitSaveTimer = 0;
  function kitInput(e) {
    const x = e.target;
    if (x.dataset.kit) { kit.profile[x.dataset.kit] = x.value.trim(); }
    else if (x.dataset.cvname) { const cv = kit.cvs.find((c) => c.id === x.dataset.cvname); if (cv) cv.name = x.value.trim() || cv.fileName; }
    else if (x.dataset.lname) { const l = kit.letters.find((c) => c.id === x.dataset.lname); if (l) l.name = x.value; }
    else if (x.dataset.lbody) { const l = kit.letters.find((c) => c.id === x.dataset.lbody); if (l) l.body = x.value; }
    else return;
    clearTimeout(kitSaveTimer);
    refreshKitSteps();
    kitSaveTimer = setTimeout(() => { saveKit(); const n = $("kitSavedNote"); if (n) { n.hidden = false; setTimeout(() => { n.hidden = true; }, 1500); } }, 300);
  }

  async function addKitCv(file) {
    if (!file) return;
    const say = (m) => { kitMsg = m; const el = $("kitMsg"); if (el) el.textContent = m; };
    if (kit.cvs.length >= KIT_MAX_CVS) { say(t("kitCvMax")); return; }
    if (file.size > 10 * 1024 * 1024) { say(t("cvTooBig")); return; }
    say(t("kitCvRead")(file.name));
    let text;
    try { text = await fileText(file); } catch (e) { say(e && e.message === "type" ? t("cvType") : t("cvFail")); return; }
    if (!text || text.trim().length < 80) { say(t("cvNoText")); return; }
    const skills = findSkills(text), role = guessRole(text), years = findYears(text);
    const id = "cv" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const base = file.name.replace(/\.[^.]+$/, "");
    await cvFiles.put(id, { blob: file, fileName: file.name, type: file.type, text });
    kit.cvs.push({ id, name: role ? `${role} CV` : base, fileName: file.name, skills, years, role, added: today() });
    if (!kit.profile.years && years) kit.profile.years = String(years);
    if (!kit.letters.length) kit.letters.push({ id: "l" + Date.now().toString(36), name: t("kitLetterDefaultName"), body: t("kitLetterDefault") });
    saveKit();
    track("kit-cv-add");
    kitMsg = t("kitCvAdded")(kit.cvs[kit.cvs.length - 1].name);
    kitJustAdded = id;
    renderKit(); refreshDrawer();
  }

  const KIT_VERSION = 1;
  async function exportKit() {
    const toB64 = (blob) => new Promise((ok) => { const r = new FileReader(); r.onload = () => ok(String(r.result)); r.readAsDataURL(blob); });
    const files = {};
    for (const cv of kit.cvs) {
      const rec = await cvFiles.get(cv.id);
      if (rec && rec.blob) files[cv.id] = { data: await toB64(rec.blob), fileName: rec.fileName, type: rec.type, text: rec.text };
    }
    const blob = new Blob([JSON.stringify({ radarak_kit: KIT_VERSION, saved: new Date().toISOString(), kit, files })], { type: "application/json" });
    const url = URL.createObjectURL(blob), a = document.createElement("a");
    a.href = url; a.download = `radarak-apply-kit-${today()}.json`; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
    track("kit-export");
  }
  async function importKit(file) {
    let data;
    try { data = JSON.parse(await file.text()); } catch { data = null; }
    if (!data || data.radarak_kit !== KIT_VERSION || !data.kit) { toast(t("kitBadFile")); return; }
    for (const cv of kit.cvs) await cvFiles.del(cv.id);
    kit = { profile: data.kit.profile || {}, cvs: (data.kit.cvs || []).slice(0, KIT_MAX_CVS), letters: data.kit.letters || [] };
    for (const cv of kit.cvs) {
      const f = (data.files || {})[cv.id];
      if (!f) continue;
      const blob = await (await fetch(f.data)).blob();
      await cvFiles.put(cv.id, { blob, fileName: f.fileName, type: f.type, text: f.text });
    }
    saveKit(); renderKit(); refreshDrawer(); toast(t("kitImported")); track("kit-import");
  }

  function kitClick(e) {
    const jump = e.target.closest("[data-kitjump]");
    if (jump) { e.preventDefault(); const sec = $("k-sec-" + jump.dataset.kitjump); if (sec) { sec.scrollIntoView({ behavior: "smooth", block: "start" });
      const f = sec.querySelector("input:not([type=file]), button"); if (f) setTimeout(() => f.focus({ preventScroll: true }), 350); } return; }
    const b = e.target.closest("button");
    if (!b) return;
    if (b.dataset.kitjobs !== undefined) { const cv = kit.cvs[0]; if (cv) b.dataset.cvuse = cv.id; else { goToJobs(); return; } }
    if (b.id === "kitAddCv") $("kitCvFile").click();
    else if (b.id === "kitAddLetter") {
      kit.letters.push({ id: "l" + Date.now().toString(36), name: t("kitLetterDefaultName"), body: t("kitLetterDefault") });
      saveKit(); renderKit();
    } else if (b.id === "kitExport") exportKit();
    else if (b.id === "kitImportBtn") $("kitImportFile").click();
    else if (b.id === "kitWipe" || b.dataset.cvdel || b.dataset.ldel) {
      if (!b.classList.contains("sure")) { b.classList.add("sure"); b.dataset.was = b.textContent; b.textContent = t("kitReallyDelete");
        setTimeout(() => { if (b.isConnected) { b.classList.remove("sure"); b.textContent = b.dataset.was; } }, 4000); return; }
      if (b.id === "kitWipe") {
        Promise.all(kit.cvs.map((cv) => cvFiles.del(cv.id))).then(() => {
          kit = { profile: {}, cvs: [], letters: [] }; saveKit(); renderKit(); refreshDrawer(); toast(t("kitWiped"));
        });
      } else if (b.dataset.cvdel) {
        cvFiles.del(b.dataset.cvdel); kit.cvs = kit.cvs.filter((c) => c.id !== b.dataset.cvdel); saveKit(); renderKit(); refreshDrawer();
      } else {
        kit.letters = kit.letters.filter((l) => l.id !== b.dataset.ldel); saveKit(); renderKit();
      }
    } else if (b.dataset.cvdl) downloadCv(b.dataset.cvdl);
    else if (b.dataset.cvuse) {
      cvFiles.get(b.dataset.cvuse).then((rec) => { if (rec && rec.text) { lastCv = null; useCvText(rec.text); track("kit-cv-use"); goToJobs(); } });
    }
  }

  // the "Apply faster" part of a job's details
  const wide = () => matchMedia("(min-width: 721px)").matches;
  function kitDrawer(j) {
    if (!kitHasData()) {
      return `<section class="dsection dkit dkitcta"><div><b>⚡ ${esc(t("dKit"))}</b><p>${esc(t("dKitCta"))}</p></div>
        <button type="button" class="primary" data-kitgo>${esc(t("dKitBtn"))}</button></section>`;
    }
    const p = kit.profile;
    let fit = "";
    if (kit.cvs.length && j.k.length) {
      const rows = kit.cvs.map((cv) => cvFit(cv, j)).sort((a, b) => b.pct - a.pct);
      const best = rows[0], tone = best.pct >= 70 ? "good" : best.pct >= 40 ? "ok" : "low";
      const miss = best.miss.map((k) => meta.skills[k]);
      fit = `<div class="dfitcard ${tone}">
          <div class="dfithead"><span class="dfitname">📄 ${esc(t("dSend"))} <b>${esc(best.cv.name)}</b></span>
            <span class="dfitpct">${best.pct}% · ${esc(t("dTone_" + tone))}</span></div>
          <span class="fbar big"><i style="width:${best.pct}%"></i></span>
          ${rows.length > 1 ? `<ul class="dfit">${rows.map((r, i) => `<li class="${i === 0 ? "best" : ""}"><span class="fname">${esc(r.cv.name)}${i === 0 ? ` <em>${esc(t("dBest"))}</em>` : ""}</span>
            <span class="fbar"><i style="width:${r.pct}%"></i></span><b>${r.pct}%</b></li>`).join("")}</ul>` : ""}
          ${miss.length ? `<p class="dmisslabel">${esc(t("dMissShort"))}</p><div class="chips">${miss.slice(0, 8).map((m) => `<span class="chip ghost">${esc(m)}</span>`).join("")}${miss.length > 8 ? `<span class="chip ghost">+${miss.length - 8}</span>` : ""}</div>
            <p class="hint">${esc(t("dMissHint"))}</p>` : `<p class="hint">${esc(t("dAllThere"))}</p>`}
          <div class="dfitbtns"><button type="button" class="chipbtn" data-cvdl="${esc(best.cv.id)}">⬇ ${esc(t("dDownloadCv"))}</button>
            ${extOn() ? `<span class="hint">⚡ ${esc(t("dExtHint"))}</span>` : ""}</div>
        </div>`;
    } else if (kit.cvs.length) fit = `<p class="hint">${esc(t("dNoSkills"))}</p>`;
    const name = [p.first, p.last].filter(Boolean).join(" ");
    const items = [[t("kFirst") + " / " + t("kLast"), name], ...KIT_FIELDS.filter(([k]) => !["first", "last"].includes(k)).map(([k, l]) => [t(l), p[k]])]
      .filter(([, v]) => String(v || "").trim());
    const copies = items.map(([l, v]) => `<button type="button" class="kcopy" data-copy="${esc(v)}"><small>${esc(l)}</small><span dir="auto">${esc(v)}</span><i class="cl">${esc(t("copy"))}</i></button>`).join("");
    const letters = kit.letters.length ? `<details class="dfold"${wide() ? " open" : ""}><summary>✉️ ${esc(t("dLetterFor")(j.c || ""))}</summary>
        <div class="dletterhead">${kit.letters.length > 1 ? `<select id="dLetterPick" aria-label="${esc(t("dLetter"))}">${kit.letters.map((l, i) => `<option value="${i}">${esc(l.name)}</option>`).join("")}</select>` : ""}
          <button type="button" class="chipbtn" id="dLetterCopy"><span class="cl">${esc(t("copy"))}</span></button></div>
        <textarea id="dLetterText" rows="7" readonly dir="auto">${esc(fillLetter(kit.letters[0].body, j))}</textarea></details>` : "";
    return `<section class="dsection dkit"><h3 class="dkittitle">⚡ ${esc(t("dKit"))}</h3>
      ${fit}
      ${copies ? `<details class="dfold"${wide() ? " open" : ""}><summary>📋 ${esc(t("dCopy"))} <small>${items.length}</small></summary>
        <p class="hint">${esc(t("dCopyHint"))}</p><div class="kcopies">${copies}</div></details>` : ""}
      ${letters}
      <button type="button" class="linkbtn" data-kitgo>${esc(t("dEditKit"))}</button></section>`;
  }
  function kitDrawerClick(e, j) {
    const c = e.target.closest("[data-copy]");
    if (c) { copyText(c.dataset.copy, c); track("kit-copy"); return true; }
    if (e.target.closest("#dLetterCopy")) { copyText($("dLetterText").value, e.target.closest("#dLetterCopy")); track("kit-letter-copy"); return true; }
    const d = e.target.closest("[data-cvdl]");
    if (d && d.closest(".dkit")) { downloadCv(d.dataset.cvdl); return true; }
    if (e.target.closest("[data-kitgo]")) { closeJob(); selectTab("kit"); window.scrollTo({ top: $("kit").offsetTop - 80, behavior: "smooth" }); return true; }
    return false;
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
        <a class="apply" href="${esc(j.u)}" target="_blank" rel="${linkRel(j)}"${(() => { const b = bestCv(j); return b ? ` data-cv="${esc(b.cv.id)}"` : ""; })()}>${j.by === ADZUNA ? t("openOn")("Adzuna") : t("applyOn")}
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17 17 7M9 7h8v8"/></svg></a>
        <button type="button" class="save" data-id="${esc(j.id)}" aria-pressed="${!!savedJobs[j.id]}">${BOOKMARK}<span>${savedJobs[j.id] ? t("saved") : t("save")}</span></button>
        <button type="button" class="applybtn" data-applied="${esc(j.id)}" aria-pressed="${!!(savedJobs[j.id] && savedJobs[j.id].a)}">${CHECK}<span>${savedJobs[j.id] && savedJobs[j.id].a ? t("applied") : t("markApplied")}</span></button>
      </div>
      ${adzunaFar(j) && j.c ? `<p class="adznote">${esc(t("adzNote")((j.co || []).join(", ") || "its country"))}
        <a href="${esc(companySearch(j))}" target="_blank" rel="noopener nofollow">${esc(t("findOnSite")(j.c))}</a></p>` : ""}
      ${j.c && meta.cpages && meta.cpages[j.c] ? `<p class="dcompany"><a href="${lang === "ar" ? "ar/" : ""}companies/${esc(meta.cpages[j.c])}/" data-copage>🏢 ${esc(t("coPage")(j.c))} →</a></p>` : ""}
      ${kitDrawer(j)}
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
        `<li><a href="${esc(x.u)}" target="_blank" rel="${linkRel(x)}">${esc(x.l || x.t)}</a></li>`).join("")}</ul></section>` : ""}
      <div class="dreport" id="reportBox"><button type="button" class="linkbtn" id="reportJob">⚑ ${t("reportClosed")}</button>
        ${j.c ? `<button type="button" class="linkbtn" id="hideCo">🚫 ${esc(t("hideCo")(j.c))}</button>` : ""}</div>
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
    currentJobWanted = id;
    const g = groupFor(id), j = jobs.find((x) => x.id === id);
    if (!g || !j) { if (more === "none" && meta && meta.more_jobs) loadMore(); return; }
    if (!currentJob) drawerReturn = opener || document.activeElement;
    currentJob = id;
    renderDrawer(g, j);
    $("jobDrawer").hidden = false; $("drawerScrim").hidden = false;
    document.body.classList.add("drawer-open");
    $("drawerBody").scrollTop = 0;
    $("drawerClose").focus();
    track("job-view/" + j.tr);
    markViewed(id);
    if (write) writeHash();
  }
  function closeJob(write = true) {
    currentJobWanted = null;
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
    $("activeFilters").innerHTML = (chips.length > 1 || (chips.length && !$("country").value)
      ? chips.join("") + `<button type="button" class="linkbtn" id="chipsClear">${t("clearAll")}</button>` : chips.join(""))
      + (hiddenCos.size ? `<button type="button" class="fchip ghost" id="unhideCos" aria-label="${esc(t("hiddenCos")(hiddenCos.size))} ×">${esc(t("hiddenCos")(hiddenCos.size))}<span aria-hidden="true">×</span></button>` : "");
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
    if (watchView) {                                   // changed the search: leave the alert's "new only" view
      const w = watches.find((x) => x.id === watchView.id);
      if (!w || w.h !== searchParams()) watchView = null;
    }
    current = filtered();
    groups = group(current);
    if (!keepPage) shown = PAGE;
    sizeHero();
    $("count").textContent = num(groups.length);
    $("countLabel").textContent = ($("country").value ? t("countLabel") : t("countAll"))
      + (more === "loading" && !isCoreCountry($("country").value) ? " · " + t("loadingMore") : "");
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
    renderAlerts();
    renderWatches();
    document.querySelector(".skillsbox").classList.toggle("has", mySkills.size > 0);
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
    if (id === "saved") { renderSaved(); maybeLoadMore(); }
    if (id === "kit") renderKit();
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

  function bindKit() {
    const k = $("kit");
    k.addEventListener("input", kitInput);
    k.addEventListener("click", kitClick);
    k.addEventListener("dragover", (e) => { const d = e.target.closest(".kdrop"); if (d) { e.preventDefault(); d.classList.add("over"); } });
    k.addEventListener("dragleave", (e) => { const d = e.target.closest(".kdrop"); if (d) d.classList.remove("over"); });
    k.addEventListener("drop", (e) => {
      const d = e.target.closest(".kdrop");
      if (!d) return;
      e.preventDefault(); d.classList.remove("over");
      const f = e.dataTransfer && e.dataTransfer.files[0];
      if (f) addKitCv(f);
    });
    k.addEventListener("change", (e) => {
      if (e.target.id === "kitCvFile") { const f = e.target.files[0]; e.target.value = ""; addKitCv(f); }
      if (e.target.id === "kitImportFile") { const f = e.target.files[0]; e.target.value = ""; if (f) importKit(f); }
    });
    $("drawerBody").addEventListener("change", (e) => {
      if (e.target.id !== "dLetterPick") return;
      const j = jobs.find((x) => x.id === currentJob), l = kit.letters[+e.target.value];
      if (j && l) $("dLetterText").value = fillLetter(l.body, j);
    });
  }
  function bind() {
    bindKit();
    renderKitPick();
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
    document.querySelectorAll('[role="tab"]').forEach((b) => b.addEventListener("click", () => {
      const id = b.getAttribute("aria-controls"), was = document.body.dataset.tab;
      selectTab(id);
      // a new view starts at its top: the page (reading views) or the job list (job views)
      if (id !== was) {
        const top = ["saved", "kit", "about", "jobs"].includes(id) ? 0 : Math.max(0, $(id).getBoundingClientRect().top + scrollY - 90);
        if (scrollY > top) window.scrollTo(0, top);
      }
    }));
    $("lang").addEventListener("click", () => {
      lang = lang === "ar" ? "en" : "ar"; store.set("lang", lang); track("language-" + lang); applyLanguage(); readHash(); update(true);
    });
    $("country").addEventListener("change", () => { store.set("country", $("country").value); track("country/" + ($("country").value || "any")); maybeLoadMore(); });
    $("mySkillInput").addEventListener("change", (e) => { if (addSkill(e.target.value)) e.target.value = ""; });
    $("cvBtn").addEventListener("click", () => $("cvFile").click());
    $("cvFile").addEventListener("change", (e) => readCvFile(e.target.files[0]));
    $("cvPasteBtn").addEventListener("click", () => {
      const box = $("cvPasteBox"); box.hidden = !box.hidden; $("cvPasteBtn").setAttribute("aria-expanded", String(!box.hidden));
      if (!box.hidden) $("cvText").focus();
    });
    $("cvRead").addEventListener("click", () => { lastCv = pastedCv($("cvText").value); useCvText($("cvText").value); });
    document.addEventListener("click", (e) => {
      if (e.target.closest("[data-gokit]")) { selectTab("kit"); window.scrollTo(0, 0); }
      const gt = e.target.closest("[data-gotab]");
      if (gt) { selectTab(gt.dataset.gotab); window.scrollTo(0, 0); }
      const k = e.target.closest("[data-kitcv]");
      if (k) cvFiles.get(k.dataset.kitcv).then((rec) => { if (rec && rec.text) { lastCv = null; useCvText(rec.text); track("kit-cv-use"); } });
    });
    // drop a CV file anywhere on the skills box
    const box = document.querySelector(".skillsbox");
    box.addEventListener("dragover", (e) => { e.preventDefault(); });
    box.addEventListener("drop", (e) => { e.preventDefault(); readCvFile(e.dataTransfer.files[0]); });
    $("mySkillInput").addEventListener("keydown", (e) => { if (e.key === "Enter" && addSkill(e.target.value)) e.target.value = ""; });
    // delegated clicks: remove/add skill chips, save buttons, location toggles
    document.addEventListener("click", (e) => {
      const x = e.target.closest("[data-applied],[data-unsave],[data-saved-view],[data-learn-see],[data-share],#newToggle");
      if (x) {
        if (x.dataset.applied) { toggleApplied(x.dataset.applied); if (savedJobs[x.dataset.applied] && savedJobs[x.dataset.applied].a) toast(t("tipApplied")); renderJobs(); renderSaved(); refreshDrawer(); }
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
        if (savedJobs[id] && !store.get("tipSaved", false)) { toast(t("tipSaved")); store.set("tipSaved", true); }   // first save: where it went
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
      if (currentJob && e.target.closest("#drawerBody .dkit")) {
        const j = jobs.find((x) => x.id === currentJob);
        if (j && kitDrawerClick(e, j)) return;
      }
      const a = e.target.closest(".job h3 a");
      if (a && !e.metaKey && !e.ctrlKey && !e.shiftKey && e.button === 0) {
        e.preventDefault(); openJob(a.closest(".job").dataset.jid, a); return;
      }
      const o = e.target.closest("[data-open]");
      if (o) { e.preventDefault(); openJob(o.dataset.open, o); return; }
      // which kinds of jobs people apply to (the track only, nothing about the visitor)
      const go = e.target.closest(".drawer .apply, .dlocs a, .locs a");
      if (go) {
        const j = jobs.find((x) => x.id === currentJob);
        track("job-open/" + (j ? j.tr : "unknown"));
        if (j && go.classList.contains("apply") && !(savedJobs[j.id] && savedJobs[j.id].a)) wentToApply = { id: j.id, at: Date.now() };
      }
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
      // "Can't apply?": a closed job is hidden (and reported, so the next update drops it for everyone);
      // "not available in your region" is the board blocking other countries, so we point to the company site instead
      if (e.target.closest("#reportJob")) {
        $("reportBox").innerHTML = `<p class="repask">${t("repAsk")}</p><div class="repchoices">
          <button type="button" class="ghostbtn" id="repGone">${t("repGone")}</button>
          <button type="button" class="ghostbtn" id="repRegion">${t("repRegion")}</button>
          <button type="button" class="linkbtn" id="repCancel">${t("repCancel")}</button></div>`;
        $("repGone").focus();
      }
      if (e.target.closest("#repCancel")) refreshDrawer();
      if (e.target.closest("#hideCo")) {
        const j = jobs.find((x) => x.id === currentJob);
        if (!j || !j.c) return;
        const key = coKey(j.c);
        hiddenCos.add(key); store.set("hiddenCos", [...hiddenCos]);
        track("hide-company");
        closeJob(); update(true);
        toast(t("hidCo")(j.c), t("undo"), () => { hiddenCos.delete(key); store.set("hiddenCos", [...hiddenCos]); update(true); });
      }
      if (e.target.closest("#repGone")) {
        const id = currentJob;
        track("closed/" + id);
        hiddenJobs.add(id); store.set("hidden", [...hiddenJobs].slice(-500));
        closeJob(); update(true); toast(t("reported"));
      }
      if (e.target.closest("#repRegion")) {
        const j = jobs.find((x) => x.id === currentJob);
        track("region-blocked/" + currentJob);
        $("reportBox").innerHTML = `<p class="adznote">${esc(t("repRegionNote"))}
          ${j && j.c ? `<a href="${esc(companySearch(j))}" target="_blank" rel="noopener nofollow">${esc(t("findOnSite")(j.c))}</a>` : ""}</p>`;
      }
      if (e.target.closest("#shareJob")) {
        const j = jobs.find((x) => x.id === currentJob);
        if (j) navigator.share({ title: j.t, text: t("shareText")(j.t, j.c), url: jobLink(j) }).then(() => track("job-share/native")).catch(() => {});
      }
    });
    // application stage in Saved
    document.addEventListener("change", (e) => {
      const sel = e.target.closest("select[data-stage]");
      if (!sel || !savedJobs[sel.dataset.stage]) return;
      if (sel.value === "none") { toggleApplied(sel.dataset.stage); delete savedJobs[sel.dataset.stage].st; store.set("saved", savedJobs); renderJobs(); renderSaved(); return; }
      savedJobs[sel.dataset.stage].st = sel.value; savedJobs[sel.dataset.stage].sd = today();
      store.set("saved", savedJobs); track("stage/" + sel.value);
      if (sel.value === "offer") toast(t("offerToast"));
      renderSaved();
    });
    // active filter chips
    $("activeFilters").addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      if (b.id === "unhideCos") { hiddenCos.clear(); store.set("hiddenCos", []); update(); return; }
      if (b.id === "chipsClear") { $("country").value = ""; store.set("country", ""); resetFilters(); return; }
      if (b.dataset.clear) { $(b.dataset.clear).value = ""; if (b.dataset.clear === "country") store.set("country", ""); }
      if (b.dataset.flagOff) quick[b.dataset.flagOff] = false;
      if (b.dataset.flagOn) quick[b.dataset.flagOn] = true;
      syncToggles(); update();
    });
    // the compact search in the sticky bar mirrors the main keywords box
    $("qMini").addEventListener("input", () => { $("q").value = $("qMini").value; update(); });
    $("qMini").addEventListener("keydown", (e) => { if (e.key === "Enter") { selectTab("jobs"); $("results").scrollIntoView({ behavior: "smooth" }); } });
    window.addEventListener("hashchange", () => { readHash(); update(); maybeLoadMore(); });
    window.addEventListener("resize", sizeHero);
  }

  let toastTimer = null;
  // back from the company's site after "Apply": ask once whether to mark the job as applied
  let wentToApply = null;
  function askApplied() {
    if (!wentToApply || document.hidden) return;
    const { id, at } = wentToApply;
    wentToApply = null;
    if (Date.now() - at < 4000 || Date.now() - at > 6 * 3600e3) return;          // a quick tab flick isn't an application
    const j = jobs.find((x) => x.id === id);
    if (!j || (savedJobs[id] && savedJobs[id].a)) return;
    const bar = $("askBar");
    bar.innerHTML = `<p>${esc(t("askApplied")(j.t, j.c || ""))}</p>
      <div><button type="button" class="primary" data-ask="yes">${esc(t("askYes"))}</button>
      <button type="button" class="chipbtn" data-ask="no">${esc(t("askNo"))}</button></div>`;
    bar.hidden = false;
    bar.onclick = (e) => {
      const b = e.target.closest("[data-ask]");
      if (!b) return;
      if (b.dataset.ask === "yes") { toggleApplied(id); renderJobs(); renderSaved(); refreshDrawer(); toast(t("tipApplied")); track("ask-applied-yes"); }
      bar.hidden = true;
    };
  }
  document.addEventListener("visibilitychange", askApplied);
  function toast(msg, actionLabel, action) {
    const el = $("toast"); el.textContent = msg; el.hidden = false;
    if (actionLabel && action) {
      const b = document.createElement("button");
      b.type = "button"; b.className = "toastbtn"; b.textContent = actionLabel;
      b.addEventListener("click", () => { el.hidden = true; action(); });
      el.append(" ", b);
    }
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { el.hidden = true; }, actionLabel ? 6000 : 3500);
  }
  // weekly email (Buttondown): shown only when the publish step filled in the newsletter name
  function setupNewsletter() {
    const box = $("newsletter"), name = box.dataset.bd;
    if (!name) return;
    box.hidden = false;
    $("nlForm").action = "https://buttondown.com/api/emails/embed-subscribe/" + encodeURIComponent(name);
    $("nlForm").addEventListener("submit", () => { track("newsletter-subscribe"); setTimeout(() => toast(t("nlThanks")), 300); });
  }

  const TZ_COUNTRY = {
    "Africa/Cairo": "Egypt", "Asia/Riyadh": "Saudi Arabia", "Asia/Dubai": "United Arab Emirates", "Asia/Qatar": "Qatar",
    "Asia/Kuwait": "Kuwait", "Asia/Bahrain": "Bahrain", "Asia/Muscat": "Oman", "Asia/Amman": "Jordan", "Asia/Beirut": "Lebanon",
    "Asia/Baghdad": "Iraq", "Asia/Damascus": "Syria", "Asia/Aden": "Yemen", "Asia/Gaza": "Palestine", "Asia/Hebron": "Palestine",
    "Africa/Casablanca": "Morocco", "Africa/Algiers": "Algeria", "Africa/Tunis": "Tunisia", "Africa/Tripoli": "Libya",
    "Africa/Khartoum": "Sudan", "Africa/Lagos": "Nigeria", "Africa/Nairobi": "Kenya", "Africa/Accra": "Ghana",
    "Africa/Johannesburg": "South Africa", "Africa/Addis_Ababa": "Ethiopia", "Europe/Istanbul": "Turkey",
    "Asia/Karachi": "Pakistan", "Asia/Kolkata": "India", "Asia/Calcutta": "India", "Asia/Dhaka": "Bangladesh",
    "Europe/London": "United Kingdom", "Europe/Berlin": "Germany", "Europe/Paris": "France", "Europe/Amsterdam": "Netherlands",
    "Europe/Madrid": "Spain", "Europe/Dublin": "Ireland", "Europe/Warsaw": "Poland", "Europe/Rome": "Italy",
  };
  function guessCountry() {
    let tz = "";
    try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch { /* old browser */ }
    const c = TZ_COUNTRY[tz];
    return c && [...$("country").options].some((o) => o.value === c) ? c : "";
  }

  // Telegram channels (meta.telegram, from TELEGRAM_CHANNELS) and RSS feeds (meta.feeds): new jobs without coming back
  const tgName = (ch) => ch.pl.includes("Remote") ? t("remote")
    : ch.pl.length === 1 ? ch.pl[0]
    : ch.u.split("/").pop().replace(/^radarak_?/i, "").replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase()) || ch.pl[0];
  function pickChannel() {
    const chans = (meta && meta.telegram) || [], c = $("country").value;
    const remote = chans.find((x) => x.pl.includes("Remote"));
    if (quick.remote || $("workMode").value === "Remote") return remote || null;
    if (!c) return chans[0] || null;
    return chans.find((x) => x.pl.includes(c)) || remote || null;
  }
  function renderAlerts() {
    const row = $("alertRow"), ch = pickChannel();
    renderFootTg();
    if (!ch || store.get("alertsHidden", "") === "1") { row.hidden = true; return; }
    const c = $("country").value, isRemote = ch.pl.includes("Remote");
    const label = isRemote ? t("remote") : ch.pl.includes(c) && ch.pl.length > 1 ? c : tgName(ch);
    const text = !c && !isRemote ? t("tgAny") : t("tgPlace")(label);
    const html = `<p>📣 ${esc(text)}</p><a class="tg" href="${esc(ch.u)}" target="_blank" rel="noopener" data-tg>${esc(t("tgJoin"))}</a>`
      + `<button class="x" type="button" data-hide aria-label="${esc(t("hideTip"))}" title="${esc(t("hideTip"))}">×</button>`;
    if (row.innerHTML !== html) row.innerHTML = html;
    row.hidden = false;
  }
  function setupWatches() {
    $("watchAdd").addEventListener("click", toggleWatch);
    $("watchBar").addEventListener("click", (e) => {
      const o = e.target.closest("[data-watch]"), d = e.target.closest("[data-watch-del]");
      if (o) openWatch(o.dataset.watch);
      else if (d) {
        watches = watches.filter((w) => w.id !== d.dataset.watchDel);
        if (watchView && watchView.id === d.dataset.watchDel) watchView = null;
        store.set("watches", watches); toast(t("watchRemoved")); update(true);
      } else if (e.target.closest("#watchAllBtn")) { watchView = null; update(); }
      else if (e.target.closest("#watchNotify")) turnOnNotify();
    });
    markDataSeen();
  }
  function setupTelegram() {
    const chans = meta.telegram || [];
    $("alertRow").addEventListener("click", (e) => {
      if (e.target.closest("[data-tg]")) track("telegram-join/" + e.target.closest("[data-tg]").href.split("/").pop());
      if (e.target.closest("[data-hide]")) { store.set("alertsHidden", "1"); $("alertRow").hidden = true; track("telegram-hide"); }
    });
  }
  function renderFootTg() {             // the footer line, again after a language switch
    const chans = (meta && meta.telegram) || [], foot = $("footTg");
    if (!chans.length) return;
    const html = esc(t("tgFoot")) + chans.map((ch) => ` <a href="${esc(ch.u)}" target="_blank" rel="noopener">${esc(tgName(ch))}</a>`).join(" ·");
    if (foot.innerHTML !== html) foot.innerHTML = html;
    foot.hidden = false;
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

  const prepJob = (j) => { j._text = [j.t, j.c, j.r, ...j.k.map((k) => meta.skills[k])].join(" ").toLowerCase(); };
  const isCoreCountry = (c) => !!c && (meta.core_regions || []).includes(regionOf[c]);
  function needMore() {
    if (more !== "none" || !meta || !meta.more_jobs) return false;
    if (!isCoreCountry($("country").value)) return true;                    // any country, or one outside the regions
    const ids = new Set(jobs.map((j) => j.id));
    if (currentJobWanted && !ids.has(currentJobWanted)) return true;       // a shared link to one of the other jobs
    return !$("saved").hidden && Object.keys(savedJobs).some((id) => !ids.has(id));   // Saved tab: a job may be in the other file
  }
  let currentJobWanted = null;
  function loadMore() {
    if (morePromise) return morePromise;
    more = "loading"; update(true);
    morePromise = fetch("data/jobs-more.json").then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then((extra) => {
        extra.forEach(prepJob);
        jobs = jobs.concat(extra);
        more = "done";
      })
      .catch(() => { more = "failed"; })
      .then(() => {
        update(true);
        if (currentJobWanted && !currentJob) openJob(currentJobWanted, null, false);
      });
    return morePromise;
  }
  const maybeLoadMore = () => { if (needMore()) loadMore(); };

  async function start() {
    applyLanguage();
    setupInstall();
    setupNewsletter();
    // let the page paint first (the headline is the biggest thing on screen), then fetch the big job list,
    // so the first paint never waits for, or competes with, a multi-megabyte download
    await new Promise((resolve) => requestAnimationFrame(() => setTimeout(resolve, 0)));
    // the insight of the day: optional, shown as a card in the job list
    const wantInsight = location.hash === "#insight";
    fetch("data/insights.json").then((r) => (r.ok ? r.json() : null)).catch(() => null).then((d) => {
      if (!d || !d.items || !d.items.length) return;
      insightsData = d;
      if (meta) renderJobs();
      if (wantInsight && $("insight")) $("insight").scrollIntoView({ behavior: "smooth", block: "center" });
    });
    // trends are optional and only needed on the Trends tab: load them in the background
    fetch("data/trends.json").then((r) => (r.ok ? r.json() : null)).catch(() => null).then((tr) => {
      trends = tr;
      if (meta && !$("trends").hidden) renderTrends();
      if (meta && tr && mySkills.size) renderLearn();
    });
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
    initVisit();
    meta.tracks.forEach((tr) => tr.roles.forEach((r) => { trackOfRole[r] = tr.name; }));
    jobs.forEach(prepJob);
    applyLanguage();
    setupTelegram();
    setupWatches();
    document.addEventListener("click", (e) => { if (e.target.closest("[data-sharecard]")) shareCard(); });
    $("jobList").addEventListener("click", onInsightClick);
    $("skillsHandBtn").addEventListener("click", () => {
      document.querySelector(".skillsbox").classList.add("open");
      $("mySkillInput").focus();
    });
    // the visitor's last country; on a first visit, a guess from the device's time zone (Africa/Cairo -> Egypt),
    // so the first screen shows jobs they can apply to. Picking "any country" is remembered and stops the guess.
    const saved = store.get("country", null);
    if (!location.hash) {
      if (saved) $("country").value = saved;
      else if (saved === null) {
        const g = guessCountry();
        if (g) { $("country").value = g; track("country-guess/" + g); }
      }
    }
    readHash();
    bind();
    if (document.fonts) document.fonts.ready.then(sizeHero);
    update(true);
    if (wantInsight && $("insight")) $("insight").scrollIntoView({ behavior: "smooth", block: "center" });
    maybeLoadMore();
  }

  start();
})();
