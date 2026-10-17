/* Radarak weekly report: a shareable 1080x1350 image + post text, drawn in the browser
   from data/trends.json (trend marts) and data/jobs.json. Nothing is uploaded anywhere. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const W = 1080, H = 1350, PAD = 72;
  const SITE = location.href.replace(/report\.html.*$/, "").replace(/[?#].*$/, "");
  const TRACK_COLORS = {
    "Data & Analytics": "#7C5CFA", "AI & Machine Learning": "#E64980", "Software Engineering": "#3B82F6",
    "Mobile Development": "#FF7A1A", "QA & Testing": "#12B886", "UI/UX Design": "#D946EF", "DevOps & Cloud": "#0EA5E9",
    "Security": "#EF4444", "ERP & CRM": "#E89A00", "Networks & Telecom": "#14B8A6", "Product & Delivery": "#65A30D",
    "IT & Support": "#64748B",
  };
  const AR_PLACES = {
    All: "كل الأماكن", Remote: "ريموت", Egypt: "مصر", "Saudi Arabia": "السعودية", "United Arab Emirates": "الإمارات",
    Qatar: "قطر", Kuwait: "الكويت", Bahrain: "البحرين", Oman: "عُمان", Jordan: "الأردن", Morocco: "المغرب",
    Germany: "ألمانيا", "United Kingdom": "بريطانيا", Netherlands: "هولندا", France: "فرنسا", Spain: "إسبانيا",
    Ireland: "أيرلندا", Poland: "بولندا", Italy: "إيطاليا", "United States": "أمريكا", Canada: "كندا", India: "الهند",
  };
  const T = {
    en: {
      title: "This week's tech hiring report", back: "← Find jobs", place: "Place", post: "Post text",
      hint: "A shareable summary of the past week. Pick a place and language, then download the image and copy the post.",
      download: "Download image", copy: "Copy text", copied: "Copied", all: "All places", remote: "Remote jobs",
      kicker: "WEEKLY TECH HIRING REPORT", newJobs: "new tech jobs", vsPrev: "vs the week before",
      byTrack: "Hiring by track", rising: "Skills on the rise", topSkills: "Most asked-for skills",
      companies: "Companies hiring this week", pts: (v) => `${v > 0 ? "+" : ""}${v} pts`,
      footer1: "Find the jobs you can actually apply to", footer2: "Free · Arabic & English · updated every morning",
      soon: "Not enough history yet for a weekly report. Check back after a couple of weeks of data.",
      postText: (d) => [
        `📡 This week in tech hiring: ${d.place} (${d.range})`, "",
        `• ${d.n} new tech jobs${d.change !== null ? ` (${d.change > 0 ? "+" : ""}${d.change}% vs the week before)` : ""}`,
        d.tracks.length ? `• Hiring most: ${d.tracks.map((x) => `${x[0]} (${x[1]})`).join(", ")}` : "",
        d.rising.length ? `• Skills on the rise: ${d.rising.map((x) => `${x[0]} (+${x[3]} pts)`).join(", ")}` : "",
        d.companies.length ? `• Hiring this week: ${d.companies.map((x) => x[0]).join(", ")}` : "", "",
        `Find the jobs you can apply to from where you live, free in Arabic and English: ${SITE}`, "",
        `#TechJobs #Hiring${d.tag ? " #" + d.tag : ""} #Radarak`,
      ].filter((l, i, a) => l !== "" || a[i - 1] !== "").join("\n"),
    },
    ar: {
      title: "تقرير توظيف التك الأسبوعي", back: "دوّر على وظايف ←", place: "المكان", post: "نص البوست",
      hint: "ملخص للأسبوع اللي فات تقدر تشاركه. اختار المكان واللغة، ونزّل الصورة وانسخ البوست.",
      download: "نزّل الصورة", copy: "انسخ النص", copied: "اتنسخ", all: "كل الأماكن", remote: "وظايف ريموت",
      kicker: "تقرير توظيف التك الأسبوعي", newJobs: "وظيفة تك جديدة", vsPrev: "عن الأسبوع اللي قبله",
      byTrack: "التوظيف حسب المجال", rising: "مهارات طالعة", topSkills: "أكتر مهارات مطلوبة",
      companies: "شركات بتوظّف الأسبوع ده", pts: (v) => `${v > 0 ? "+" : ""}${v} نقطة`,
      footer1: "لاقي الوظايف اللي تقدر تقدّم عليها فعلًا", footer2: "مجاني · عربي وإنجليزي · بيتحدّث كل يوم الصبح",
      soon: "لسه مفيش بيانات كفاية لتقرير أسبوعي. ارجع بعد كام أسبوع.",
      postText: (d) => [
        `📡 التوظيف في التك الأسبوع ده: ${d.place} (${d.range})`, "",
        `• ${d.n} وظيفة تك جديدة${d.change !== null ? ` (${d.change > 0 ? "+" : ""}${d.change}% عن الأسبوع اللي قبله)` : ""}`,
        d.tracks.length ? `• أكتر مجالات بتوظّف: ${d.tracks.map((x) => `${x[0]} (${x[1]})`).join("، ")}` : "",
        d.rising.length ? `• مهارات طالعة: ${d.rising.map((x) => `${x[0]} (+${x[3]} نقطة)`).join("، ")}` : "",
        d.companies.length ? `• شركات بتوظّف: ${d.companies.map((x) => x[0]).join("، ")}` : "", "",
        `شوف الوظايف اللي تقدر تقدّم عليها من البلد اللي إنت فيها، مجانًا بالعربي والإنجليزي: ${SITE}`, "",
        `#وظائف #وظائف_تقنية${d.tag ? " #" + d.tag : ""} #Radarak`,
      ].filter((l, i, a) => l !== "" || a[i - 1] !== "").join("\n"),
    },
  };
  const params = new URLSearchParams(location.search);
  let lang = params.get("lang") === "ar" ? "ar" : "en";
  let meta, trends, jobs;
  const t = (k) => T[lang][k];
  const placeName = (p) => (lang === "ar" ? AR_PLACES[p] || p : p === "All" ? t("all") : p === "Remote" ? t("remote") : p);
  const count = (name) => { try { window.goatcounter && window.goatcounter.count({ path: name, title: name, event: true }); } catch { /* optional */ } };

  // ------------------------------------------------------------------ numbers for one place
  function summary(place) {
    const weeks = trends.weeks, n = weeks.length, w = trends.weekly[place] || {};
    const at = (i) => Object.values(w).reduce((a, arr) => a + (arr[i] || 0), 0);
    const last = at(n - 2), prev = at(n - 3);
    const start = new Date(weeks[n - 2] + "T12:00:00Z"), end = new Date(start.getTime() + 6 * 864e5);
    const loc = lang === "ar" ? "ar-EG" : "en-GB";
    const range = `${start.toLocaleDateString(loc, { day: "numeric", month: "short" })} – ${end.toLocaleDateString(loc, { day: "numeric", month: "short", year: "numeric" })}`;
    const tracks = Object.entries(w).map(([k, arr]) => [k, arr[n - 2] || 0]).filter((x) => x[1] > 0).sort((a, b) => b[1] - a[1]).slice(0, 5);
    const sk = trends.skills[place] || trends.skills.All || { rising: [], top: [] };
    const from = weeks[n - 2], to = end.toISOString().slice(0, 10);
    const inPlace = (j) => place === "All" || (place === "Remote" ? j.w === "Remote" : j.w !== "Remote" && j.co.includes(place));
    const byCo = new Map();
    jobs.forEach((j) => { if (j.c && j.p >= from && j.p <= to && !((j.f || 0) & 8) && inPlace(j)) byCo.set(j.c, (byCo.get(j.c) || 0) + 1); });
    const companies = [...byCo.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6);
    return {
      place: placeName(place), range, n: last, change: prev >= 5 ? Math.round((100 * (last - prev)) / prev) : null,
      tracks, rising: (sk.rising || []).slice(0, 4), top: (sk.top || []).slice(0, 4), companies,
      tag: place === "All" || place === "Remote" ? "" : (lang === "ar" ? AR_PLACES[place] || place : place).replace(/\s+/g, "_"), enough: trends.history_days >= 14 && last > 0,
    };
  }

  // ------------------------------------------------------------------ drawing
  const cv = $("card"), ctx = cv.getContext("2d");
  const rtl = () => lang === "ar";
  const fx = (x, w = 0) => (rtl() ? W - x - w : x);
  const display = (size, weight = 800) => (rtl() ? `700 ${size}px "IBM Plex Sans Arabic"` : `${weight} ${size}px "Bricolage Grotesque", "IBM Plex Sans Arabic"`);
  const body = (size, weight = 500) => `${weight} ${size}px "IBM Plex Sans Arabic", "Segoe UI", sans-serif`;
  function text(str, x, y, font, color, align = "start", maxW) {
    ctx.font = font; ctx.fillStyle = color; ctx.textAlign = align; ctx.direction = rtl() ? "rtl" : "ltr";
    let s = String(str);
    if (maxW) while (s.length > 1 && ctx.measureText(s).width > maxW) s = s.slice(0, -2) + "…";
    ctx.fillText(s, fx(x), y);
    return ctx.measureText(s).width;
  }
  function rrect(x, y, w, h, r, fill) {
    ctx.beginPath(); ctx.roundRect(fx(x, w), y, w, h, r); ctx.fillStyle = fill; ctx.fill();
  }
  function logo(x, y, s) {
    const cx = fx(x + s / 2), cy = y + s / 2, k = s / 32;
    ctx.fillStyle = "#5B3FE0"; ctx.beginPath(); ctx.arc(cx, cy, 15 * k, 0, 7); ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,.55)"; ctx.lineWidth = 1.8 * k; ctx.beginPath(); ctx.arc(cx, cy, 8.5 * k, 0, 7); ctx.stroke();
    [[6.5, -6.5, 3, "#FFB020"], [-6.5, 3.5, 2.5, "#FF5E3A"], [3.5, 6.5, 2.1, "#10B981"]].forEach(([dx, dy, r, c]) => {
      ctx.fillStyle = c; ctx.beginPath(); ctx.arc(cx + dx * k, cy + dy * k, r * k, 0, 7); ctx.fill();
    });
  }

  function draw(place) {
    const d = summary(place);
    ctx.clearRect(0, 0, W, H);
    // background
    ctx.fillStyle = "#F6F5FC"; ctx.fillRect(0, 0, W, H);
    let g = ctx.createRadialGradient(W * 0.92, 40, 0, W * 0.92, 40, 620);
    g.addColorStop(0, "#E2D9FF"); g.addColorStop(1, "rgba(226,217,255,0)"); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    g = ctx.createRadialGradient(0, H * 0.78, 0, 0, H * 0.78, 520);
    g.addColorStop(0, "#FFE1D6"); g.addColorStop(1, "rgba(255,225,214,0)"); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    // radar rings, top corner
    ctx.strokeStyle = "rgba(91,63,224,.13)"; ctx.lineWidth = 2;
    [220, 150, 80].forEach((r) => { ctx.beginPath(); ctx.arc(fx(W - 60), 120, r, 0, 7); ctx.stroke(); });

    // header
    logo(PAD, 64, 60);
    text(rtl() ? "رادارك" : "Radarak", PAD + 76, 108, display(44), "#19163A");
    text(t("kicker"), PAD, 190, body(22, 700), "#5B3FE0");
    text(`${d.place} · ${d.range}`, PAD, 236, display(40, 700), "#19163A", "start", W - 2 * PAD);

    if (!d.enough) {
      text(t("soon"), PAD, 340, body(30), "#615D80", "start", W - 2 * PAD);
      footer(); return d;
    }
    // big number
    ctx.save();
    ctx.font = `800 150px "Bricolage Grotesque", sans-serif`; ctx.direction = rtl() ? "rtl" : "ltr"; ctx.textAlign = "start";
    const numW = ctx.measureText(d.n.toLocaleString("en-US")).width;
    g = ctx.createLinearGradient(fx(PAD, numW), 0, fx(PAD, numW) + numW, 0);
    g.addColorStop(0, rtl() ? "#FF5E3A" : "#5B3FE0"); g.addColorStop(0.5, "#B03FE0"); g.addColorStop(1, rtl() ? "#5B3FE0" : "#FF5E3A");
    ctx.fillStyle = g; ctx.fillText(d.n.toLocaleString("en-US"), fx(PAD), 400);
    ctx.restore();
    text(t("newJobs"), PAD + numW + 22, 360, body(36, 600), "#19163A");
    if (d.change !== null) {
      const up = d.change >= 0, label = `${up ? "▲" : "▼"} ${Math.abs(d.change)}% ${t("vsPrev")}`;
      ctx.font = body(24, 700); const lw = ctx.measureText(label).width + 36;
      rrect(PAD + numW + 22, 376, lw, 46, 23, up ? "#D7F5EA" : "#FFE1DA");
      text(label, PAD + numW + 40, 408, body(24, 700), up ? "#0B7A55" : "#B4232F");
    }

    // hiring by track
    let y = 490;
    text(t("byTrack"), PAD, y, display(32), "#19163A"); y += 26;
    const maxT = Math.max(1, ...d.tracks.map((x) => x[1]));
    d.tracks.forEach(([name, n]) => {
      y += 46;
      text(name, PAD, y, body(25, 600), "#19163A", "start", 330);
      const bw = Math.max(8, (W - 2 * PAD - 360 - 80) * (n / maxT));
      rrect(PAD + 350, y - 24, W - 2 * PAD - 350 - 80, 28, 14, "#ECEAF6");
      rrect(PAD + 350, y - 24, bw, 28, 14, TRACK_COLORS[name] || "#5B3FE0");
      text(n.toLocaleString("en-US"), W - PAD, y, body(25, 700), "#19163A", "end");
    });

    // two columns: rising skills | most asked-for
    y += 72;
    const colW = (W - 2 * PAD - 40) / 2;
    const col = (x0, title, rows, valueOf, color) => {
      text(title, x0, y, display(30), "#19163A");
      rows.forEach((r, i) => {
        const yy = y + 50 + i * 44;
        text(r[0], x0, yy, body(25, 600), "#19163A", "start", colW - 150);
        text(valueOf(r), x0 + colW, yy, body(24, 700), color, "end");
      });
    };
    col(PAD, t("rising"), d.rising, (r) => t("pts")(r[3]), "#0B7A55");
    col(PAD + colW + 40, t("topSkills"), d.top, (r) => `${Math.round(r[2])}%`, "#5B3FE0");

    // companies
    y += 50 + Math.max(d.rising.length, d.top.length, 1) * 44 + 50;
    if (d.companies.length) {
      text(t("companies"), PAD, y, display(30), "#19163A");
      let x = PAD, yy = y + 26;
      ctx.font = body(23, 600);
      d.companies.forEach(([c]) => {
        const label = c.length > 26 ? c.slice(0, 25) + "…" : c, w = ctx.measureText(label).width + 36;
        if (x + w > W - PAD) { x = PAD; yy += 56; }
        if (yy + 44 > H - 170) return;
        rrect(x, yy, w, 44, 22, "#FFFFFF");
        ctx.strokeStyle = "#E3E1F0"; ctx.lineWidth = 2; ctx.beginPath(); ctx.roundRect(fx(x, w), yy, w, 44, 22); ctx.stroke();
        text(label, x + 18, yy + 30, body(23, 600), "#19163A");
        ctx.font = body(23, 600);
        x += w + 12;
      });
    }
    footer();
    return d;
  }

  function footer() {
    const fy = H - 150;
    const g = ctx.createLinearGradient(0, 0, W, 0);
    g.addColorStop(0, "#5B3FE0"); g.addColorStop(0.5, "#B03FE0"); g.addColorStop(1, "#FF5E3A");
    ctx.fillStyle = g; ctx.beginPath(); ctx.roundRect(PAD - 16, fy, W - 2 * PAD + 32, 108, 26); ctx.fill();
    text(t("footer1"), PAD + 14, fy + 44, body(27, 700), "#FFFFFF", "start", W - 2 * PAD - 30);
    text(SITE.replace(/^https?:\/\//, "").replace(/\/$/, ""), PAD + 14, fy + 84, body(22, 500), "rgba(255,255,255,.92)", "start", W - 2 * PAD - 30);
  }

  // ------------------------------------------------------------------ page
  function applyLang() {
    document.documentElement.lang = lang; document.documentElement.dir = rtl() ? "rtl" : "ltr";
    $("brandName").textContent = rtl() ? "رادارك" : "Radarak";
    $("rTitle").textContent = t("title"); $("rHint").textContent = t("hint"); $("backLink").textContent = t("back");
    $("placeLabel").textContent = t("place"); $("postLabel").textContent = t("post");
    $("download").textContent = t("download"); $("copy").textContent = t("copy");
    document.querySelectorAll("[data-lang]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
    $("backLink").href = "./";
  }
  function fillPlaces() {
    const sel = $("place"), prev = sel.value || params.get("place") || "All";
    const total = (p) => Object.values(trends.weekly[p] || {}).reduce((a, arr) => a + arr.reduce((x, y) => x + y, 0), 0);
    const places = Object.keys(trends.weekly).filter((p) => p !== "All").sort((a, b) => total(b) - total(a));
    sel.innerHTML = "";
    ["All", ...places].forEach((p) => sel.add(new Option(placeName(p), p)));
    sel.value = places.includes(prev) || prev === "All" ? prev : "All";
  }
  function render() {
    const place = $("place").value || "All";
    const d = draw(place);
    $("post").value = d.enough ? t("postText")(d) : t("soon");
    const q = new URLSearchParams(); if (place !== "All") q.set("place", place); if (lang === "ar") q.set("lang", "ar");
    history.replaceState(null, "", location.pathname + (q.toString() ? "?" + q : ""));
  }

  async function start() {
    applyLang();
    try {
      [meta, trends, jobs] = await Promise.all(["meta", "trends", "jobs"].map((f) =>
        fetch(`data/${f}.json`).then((r) => { if (!r.ok) throw new Error(f); return r.json(); })));
    } catch {
      $("rStatus").textContent = T[lang].soon; return;
    }
    await Promise.all(['800 40px "Bricolage Grotesque"', '700 40px "Bricolage Grotesque"', '500 20px "IBM Plex Sans Arabic"',
      '700 20px "IBM Plex Sans Arabic"', '600 20px "IBM Plex Sans Arabic"', '700 20px "IBM Plex Sans Arabic" ع']
      .map((f) => document.fonts.load(f).catch(() => null)));
    fillPlaces(); render();
    $("place").addEventListener("change", render);
    document.querySelectorAll("[data-lang]").forEach((b) => b.addEventListener("click", () => {
      lang = b.dataset.lang; applyLang(); fillPlaces(); render();
    }));
    $("download").addEventListener("click", () => {
      cv.toBlob((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `radarak-${($("place").value || "all").toLowerCase().replace(/\s+/g, "-")}-${trends.weeks[trends.weeks.length - 2]}-${lang}.png`;
        a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
      }, "image/png");
      count("report-download");
    });
    $("copy").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText($("post").value); } catch { $("post").select(); document.execCommand("copy"); }
      $("copy").textContent = t("copied"); setTimeout(() => { $("copy").textContent = t("copy"); }, 2000);
      count("report-copy");
    });
  }
  start();
})();
