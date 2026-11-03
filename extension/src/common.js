/* Radarak Apply: shared by every part of the extension (Chrome, Edge, Brave, Opera, Firefox).
 * The Apply kit (details, CVs, cover letters) is copied from radarak.online into the extension's own storage
 * on this computer. Nothing is ever sent to a server: there is no network code in this extension. */
(() => {
  if (globalThis.RA) return;                       // injected twice (content script + popup "fill this page")
  const api = globalThis.browser || globalThis.chrome;

  const store = {
    async get(keys) { return (await api.storage.local.get(keys)) || {}; },
    async set(obj) { return api.storage.local.set(obj); },
    async remove(keys) { return api.storage.local.remove(keys); },
  };

  const PENDING_HOURS = 6;          // "the job you just clicked Apply on" is remembered this long

  // ---------------------------------------------------------------- what a form field is asking for
  // Each rule: kit key, test on the field's description, which kinds of fields it may fill.
  const RULES = [
    ["email", /e-?mail/, "text"],
    ["first", /first[\s_-]*name|given[\s_-]*name|fore[\s_-]*name|vorname|pr[ée]nom|\bnombre\b|^first$|firstname/, "text"],
    ["last", /last[\s_-]*name|sur[\s_-]*name|family[\s_-]*name|nachname|apellidos?|lastname|^last$/, "text"],
    ["linkedin", /linked\s*in/, "text"],
    ["portfolio", /github|git\s*lab|portfolio|personal\s*(web)?site|website|blog|^urls?\b/, "text"],
    ["phone", /phone|mobile|\btel\b|telephone|whats\s*app|handy|t[ée]l[ée]phone/, "text"],
    ["years", /years?.{0,25}experience|experience.{0,25}years|years?\s+of\s+(relevant|professional|work)/, "text"],
    ["notice", /notice\s*period|when\s+can\s+you\s+start|earliest\s+start|start\s*date|availability\s+to\s+start/, "text"],
    ["salary", /salary|compensation|pay\s+expectation|expected\s+(pay|ctc|package)|\bctc\b|desired\s+pay/, "text"],
    ["country", /\bcountry\b|\bland\b|\bpays\b|\bpa[íi]s\b/, "text"],
    ["city", /\bcity\b|\btown\b|location|where\s+(are\s+you|do\s+you)\s+(based|live|located)|current\s+(location|address)|\bort\b|\bville\b|\bciudad\b/, "text"],
    ["full", /full[\s_-]*name|your\s+name|^name$|^name\b|\bname\s*\*?$|candidate\s+name|legal\s+name/, "text"],
    ["letter", /cover[\s_-]*letter|motivation|anschreiben|lettre|why\s+(do\s+you\s+want|are\s+you\s+interested|this\s+role)|additional\s+information|anything\s+else|comments?|message\s+to/, "textarea"],
  ];
  // never put kit data into these, whatever their label says
  const NEVER = /company|employer|organi[sz]ation|school|university|college|reference|referr|manager|recruiter|password|search|captcha|coupon|promo|how\s+did\s+you\s+hear|pronoun|gender|race|ethnic|veteran|disabilit|sponsor|visa|authori[sz]ed|relocat|preferred\s+name|middle\s+name|nick/;

  function textOf(el) { return (el && (el.innerText || el.textContent) || "").replace(/\s+/g, " ").trim(); }

  // everything a person would read to know what a field wants
  function describe(el) {
    const bits = [];
    const doc = el.ownerDocument;
    if (el.labels) for (const l of el.labels) bits.push(textOf(l));
    const lb = el.getAttribute("aria-labelledby");
    if (lb) for (const id of lb.split(/\s+/)) { const x = doc.getElementById(id); if (x) bits.push(textOf(x)); }
    for (const a of ["aria-label", "placeholder", "name", "id", "autocomplete", "data-qa", "data-testid", "title"]) {
      const v = el.getAttribute(a);
      if (v) bits.push(v.replace(/[_\-[\]]+/g, " ").replace(/([a-z])([A-Z])/g, "$1 $2"));
    }
    if (!el.labels || !el.labels.length) {
      // a question wrapper with its own label/legend (Greenhouse, Ashby, Workable)
      const box = el.closest("fieldset, .field, .application-question, .form-group, [class*='field'], [class*='question'], li, div");
      const lab = box && box.querySelector("label, legend, .label, [class*='label'], [class*='title']");
      if (lab && !lab.contains(el)) bits.push(textOf(lab).slice(0, 120));
    }
    return bits.join(" | ").toLowerCase();
  }

  function visible(el) {
    if (el.type === "file") return !el.disabled;     // file inputs are often hidden behind a nice button
    const r = el.getBoundingClientRect(), cs = el.ownerDocument.defaultView.getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none" && !el.disabled && !el.readOnly;
  }

  function whatFor(el) {
    const d = describe(el);
    if (!d || NEVER.test(d.replace(/\|.*$/, "")) && !/e-?mail|phone|linked/.test(d)) return null;
    const kind = el.tagName === "TEXTAREA" ? "textarea" : "text";
    if (el.type === "email") return "email";
    if (el.type === "tel") return "phone";
    for (const [key, re, k] of RULES) {
      if (!re.test(d)) continue;
      if (key === "letter" && kind !== "textarea") continue;
      if (key !== "letter" && kind === "textarea" && !/city|location|salary|notice|years/.test(key)) continue;
      if (NEVER.test(d) && !["email", "phone", "linkedin"].includes(key)) return null;
      return key;
    }
    return null;
  }

  // set a value so that React / Vue / Angular forms notice it
  function setValue(el, value) {
    const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : el.tagName === "SELECT" ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
    el.focus({ preventScroll: true });
    setter.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.dispatchEvent(new Event("blur", { bubbles: true }));
  }
  function pickOption(sel, wanted) {
    const w = String(wanted || "").toLowerCase().trim();
    if (!w) return false;
    const opts = [...sel.options];
    const hit = opts.find((o) => o.text.toLowerCase().trim() === w) || opts.find((o) => o.text.toLowerCase().includes(w))
      || (/^\d+$/.test(w) ? opts.find((o) => (o.text.match(/\d+/g) || []).some((n, i, a) => +n === +w || (a.length > 1 && +a[0] <= +w && +w <= +a[1]))) : null);
    if (!hit || hit.selected) return false;
    setValue(sel, hit.value);
    return true;
  }
  function dataUrlToFile(dataUrl, name, type) {
    const [head, body] = String(dataUrl).split(",");
    const bin = atob(body || ""), bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new File([bytes], name || "cv.pdf", { type: type || (head.match(/data:([^;]+)/) || [])[1] || "application/octet-stream" });
  }
  function setFile(input, file) {
    try {
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      return input.files && input.files.length === 1;
    } catch { return false; }
  }

  function fillLetter(body, ctx, profile) {
    const vals = { company: ctx.company || "", job: ctx.title || "", first: profile.first || "", last: profile.last || "", years: profile.years || "" };
    return String(body || "").replace(/\{(company|job|first|last|years)\}/g, (m, k) => vals[k] || m);
  }

  // which CV and letter to use on this page
  function choose(data, ctx, opts = {}) {
    const kit = data.kit || {}, cvs = kit.cvs || [], files = data.files || {};
    const pending = data.pending && Date.now() - data.pending.at < PENDING_HOURS * 3600e3 ? data.pending : null;
    const cvId = opts.cvId || (pending && pending.cvId && files[pending.cvId] ? pending.cvId : null) || (cvs.find((c) => files[c.id]) || {}).id;
    const cv = cvs.find((c) => c.id === cvId) || null;
    const company = ctx.company || (pending && pending.company) || "";
    const title = ctx.title || (pending && pending.title) || "";
    let letter = "";
    if (pending && pending.letter && (!ctx.company || !pending.company || pending.company.toLowerCase() === ctx.company.toLowerCase())) letter = pending.letter;
    else if ((kit.letters || []).length) letter = fillLetter(kit.letters[0].body, { company, title }, kit.profile || {});
    return { cv, file: cv ? files[cv.id] : null, letter };
  }

  // fill every field we understand in this document; returns what was done
  function fillDocument(doc, data, ctx, opts = {}) {
    const p = (data.kit && data.kit.profile) || {};
    const pick = choose(data, ctx, opts);
    const values = {
      email: p.email, first: p.first, last: p.last, full: [p.first, p.last].filter(Boolean).join(" "), phone: p.phone,
      linkedin: p.linkedin, portfolio: p.portfolio, years: p.years, notice: p.notice, salary: p.salary,
      country: p.country, city: p.city, letter: pick.letter,
    };
    const filled = [], used = new Set();
    const fields = [...doc.querySelectorAll("input, textarea, select")]
      .filter((el) => !["hidden", "submit", "button", "checkbox", "radio", "password", "image", "reset", "search"].includes(el.type));
    // a "location" box gets "City, Country" when the form has no separate country field
    const hasCountry = fields.some((el) => el.type !== "file" && whatFor(el) === "country");
    let cvDone = false, letterFileDone = false;
    for (const el of fields) {
      if (!visible(el)) continue;
      if (el.type === "file") {
        const d = describe(el);
        if (/cover|letter|motivation|anschreiben/.test(d)) {
          if (!letterFileDone && pick.letter && !(el.files && el.files.length)) {
            const f = new File([pick.letter], "cover-letter.txt", { type: "text/plain" });
            if (setFile(el, f)) { filled.push("cover letter (file)"); letterFileDone = true; mark(el); }
          }
        } else if (!cvDone && pick.file && !(el.files && el.files.length) && (/resume|\bcv\b|curriculum|lebenslauf|attach|upload|document/.test(d) || !doc.querySelector("input[type=file][name*=resume i], input[type=file][id*=resume i]"))) {
          if (setFile(el, dataUrlToFile(pick.file.data, pick.file.fileName, pick.file.type))) { filled.push("CV"); cvDone = true; mark(el); }
        }
        continue;
      }
      const key = whatFor(el);
      if (!key || used.has(el)) continue;
      let v = values[key];
      if (key === "city" && !hasCountry && p.city && p.country && /location|address|where/.test(describe(el))) v = `${p.city}, ${p.country}`;
      if (!v || !String(v).trim()) continue;
      if (el.tagName === "SELECT") { if (pickOption(el, v)) { filled.push(key); mark(el); } continue; }
      if (String(el.value || "").trim()) continue;           // never overwrite what's there
      if (el.type === "number" && !/^\d+$/.test(String(v))) continue;
      setValue(el, String(v));
      used.add(el); filled.push(key); mark(el);
    }
    return { filled, cv: pick.cv ? pick.cv.name : null };
  }
  function mark(el) {
    el.style.outline = "2px solid #30D158";
    el.style.outlineOffset = "1px";
    el.dataset.radarakFilled = "1";
  }

  // the company and job title of an application page, from its address and headings
  function pageContext(doc, loc) {
    const host = loc.hostname, parts = loc.pathname.split("/").filter(Boolean);
    let company = "";
    if (/greenhouse\.io$/.test(host) && parts[0] && parts[0] !== "embed") company = parts[0];
    else if (/lever\.co$|ashbyhq\.com$|workable\.com$|smartrecruiters\.com$/.test(host) && parts[0]) company = parts[0];
    else if (/recruitee\.com$|teamtailor\.com$|bamboohr\.com$|personio\.(de|com)$|breezy\.hr$|pinpointhq\.com$/.test(host)) company = host.split(".")[0];
    const og = doc.querySelector('meta[property="og:site_name"]');
    if (og && og.content && !/greenhouse|lever|ashby|workable|smartrecruiters|recruitee|teamtailor|bamboo|personio|breezy|pinpoint/i.test(og.content)) company = og.content;
    company = company.replace(/[-_]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()).trim();
    const h = doc.querySelector("h1, .posting-headline h2, .app-title, [class*='job-title'], [class*='jobTitle'], h2");
    const title = (h && textOf(h).slice(0, 140)) || "";
    return { company, title };
  }

  globalThis.RA = { api, store, describe, whatFor, fillDocument, pageContext, fillLetter, choose, dataUrlToFile, PENDING_HOURS };
})();
