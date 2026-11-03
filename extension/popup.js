/* The toolbar popup: is the kit synced, which CV to use, and "Fill this page" for any site.
 * Built with DOM calls only (no HTML strings), as browser add-on stores prefer. */
(async () => {
  const { api, store, PENDING_HOURS } = globalThis.RA;
  const main = document.getElementById("main");
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === false || v == null) continue;
      if (k === "class") el.className = v; else if (k === "text") el.textContent = v; else el.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids) if (kid != null && kid !== false) el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    return el;
  }
  const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;

  const data = await store.get(["kit", "files", "synced", "pending"]);
  const kit = data.kit, files = data.files || {};
  const cvs = ((kit && kit.cvs) || []).filter((c) => files[c.id]);
  const hasProfile = kit && kit.profile && Object.values(kit.profile).some((v) => String(v || "").trim());
  main.textContent = "";
  if (!kit || (!cvs.length && !hasProfile)) {
    main.append(
      h("p", {}, "Set up your Apply kit on Radarak first: your details, CVs and cover letters."),
      h("p", {}, h("a", { href: "https://radarak.online/#tab=kit", target: "_blank", rel: "noopener" }, "Open Radarak → Apply kit")),
      h("p", { class: "muted" }, "Already did? Open radarak.online once in this browser and the kit is copied here."));
    return;
  }
  const p = kit.profile || {};
  const pending = data.pending && Date.now() - data.pending.at < PENDING_HOURS * 3600e3 ? data.pending : null;
  const defaultCv = pending && pending.cvId && files[pending.cvId] ? pending.cvId : (cvs[0] || {}).id;
  main.append(
    h("p", { class: "ok" }, `✓ Kit ready${p.first ? ` for ${p.first}` : ""}: ${plural(cvs.length, "CV")}, ${plural((kit.letters || []).length, "letter")}`),
    h("p", { class: "muted" }, `Copied from radarak.online ${data.synced ? new Date(data.synced).toLocaleString() : ""}`));
  if (pending) main.append(h("div", { class: "box" }, "Last job you opened on Radarak:", h("br"), h("b", {}, pending.title || ""), pending.company ? ` · ${pending.company}` : ""));
  let select = null;
  if (cvs.length) {
    select = h("select", { id: "cv" }, ...cvs.map((c) => h("option", { value: c.id, selected: c.id === defaultCv }, c.name)));
    main.append(h("label", {}, "CV to attach", select));
  }
  const btn = h("button", { class: "primary", id: "fill", type: "button" }, "⚡ Fill this page");
  const out = h("p", { class: "result muted", id: "result", role: "status", "aria-live": "polite" }, "It fills what it understands and never submits. You check and send.");
  main.append(btn, out);
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    try {
      const [tab] = await api.tabs.query({ active: true, currentWindow: true });
      const target = { tabId: tab.id, allFrames: true };
      await api.scripting.executeScript({ target, files: ["src/common.js", "src/fill.js"] });
      const res = await api.scripting.executeScript({ target, func: (id) => (globalThis.__radarakFill ? globalThis.__radarakFill({ cvId: id }) : null),
        args: [select ? select.value : null] });
      const filled = res.map((r) => r && r.result).filter((r) => r && r.ok).flatMap((r) => r.filled);
      out.className = "result " + (filled.length ? "ok" : "muted");
      out.textContent = filled.length ? `Filled ${plural(filled.length, "field")}. Check them (green) and submit yourself.`
        : "Nothing to fill on this page (or the fields already have answers).";
    } catch {
      out.className = "result muted";
      out.textContent = "This page can't be filled (browser pages and add-on stores are protected).";
    } finally { btn.disabled = false; }
  });
})();
