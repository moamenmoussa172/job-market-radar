/* On an application form: a small "Fill with Radarak" button. Nothing is filled until you click it,
 * and nothing is ever submitted: you check the form and send it yourself. */
(() => {
  if (globalThis.__radarakFill) return;
  const { store, fillDocument, pageContext } = globalThis.RA;

  async function fill(opts = {}) {
    const data = await store.get(["kit", "files", "pending"]);
    if (!data.kit) return { ok: false, reason: "nokit" };
    const res = fillDocument(document, data, pageContext(document, location), opts);
    return { ok: true, ...res };
  }
  globalThis.__radarakFill = fill;

  const looksLikeForm = () => !!document.querySelector(
    "input[type=file], input[type=email], input[name*=email i], input[autocomplete=email], input[name*=first i][name*=name i]");

  let host = null;
  function button() {
    if (host || !looksLikeForm() || window.top !== window && !document.querySelector("input[type=file], input[type=email]")) return;
    host = document.createElement("div");
    host.id = "radarak-apply";
    host.style.cssText = "position:fixed;z-index:2147483646;bottom:20px;inset-inline-end:20px;";
    const sh = host.attachShadow({ mode: "open" });
    sh.innerHTML = `<style>
      .b{display:flex;align-items:center;gap:8px;border:0;border-radius:999px;padding:12px 18px;background:#0071E3;color:#fff;
         font:600 15px/1 system-ui,-apple-system,"Segoe UI",sans-serif;box-shadow:0 6px 20px rgba(0,0,0,.18);cursor:pointer}
      .b:hover{background:#0062c4}.b:focus-visible{outline:3px solid #64D2FF;outline-offset:2px}
      .n{margin-top:8px;max-width:300px;background:#1D1D1F;color:#fff;border-radius:12px;padding:10px 12px;
         font:14px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif;box-shadow:0 6px 20px rgba(0,0,0,.18)}
      .n[hidden]{display:none}.x{float:right;background:none;border:0;color:#aaa;cursor:pointer;font-size:16px;margin-left:6px}
      svg{width:18px;height:18px}
    </style>
    <button class="b" type="button" part="button"><svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="15" fill="#fff" fill-opacity=".25"/>
      <circle cx="22.5" cy="9.5" r="3" fill="#fff"/><circle cx="9.5" cy="19.5" r="2.5" fill="#64D2FF"/><circle cx="19.5" cy="22.5" r="2.1" fill="#30D158"/></svg>
      <span>Fill with Radarak</span></button>
    <div class="n" role="status" aria-live="polite" hidden></div>`;
    const note = sh.querySelector(".n");
    // parts: strings, or [text] for bold; built with DOM calls (no HTML strings)
    const say = (...parts) => {
      note.textContent = "";
      const x = document.createElement("button"); x.className = "x"; x.type = "button"; x.setAttribute("aria-label", "Close"); x.textContent = "×";
      x.onclick = () => { note.hidden = true; };
      note.append(x);
      for (const part of parts) {
        if (part === "\n") note.append(document.createElement("br"));
        else if (Array.isArray(part)) { const b = document.createElement("b"); b.textContent = part[0]; note.append(b); }
        else note.append(document.createTextNode(part));
      }
      note.hidden = false;
    };
    sh.querySelector(".b").addEventListener("click", async () => {
      const r = await fill();
      if (!r.ok) { say("Set up your Apply kit first: open ", ["radarak.online"], " → ", ["Apply kit"], "."); return; }
      const n = r.filled.length;
      if (!n) { say("Nothing to fill here, or the fields already have answers."); return; }
      say(`Filled ${n} field${n === 1 ? "" : "s"}`, ...(r.filled.includes("CV") && r.cv ? [" and attached ", [r.cv]] : []), ".", "\n",
        "Check everything (green), answer the other questions, then submit yourself.");
    });
    (document.body || document.documentElement).appendChild(host);
  }

  button();
  // single-page apps (Ashby, Workable, SmartRecruiters) show the form later
  const mo = new MutationObserver(() => { if (!host) button(); else mo.disconnect(); });
  mo.observe(document.documentElement, { childList: true, subtree: true });
  setTimeout(() => mo.disconnect(), 120000);
})();
