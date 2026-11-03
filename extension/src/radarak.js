/* On radarak.online: copy the Apply kit into the extension, and remember which job you clicked "Apply" on
 * (its company, title, the CV that fits it best and the filled cover letter), so the application form
 * gets the right CV and letter. Everything stays in this browser. */
(() => {
  const { store } = globalThis.RA;
  const root = document.documentElement;

  // The page sends its kit (and the CV files) with window.postMessage when asked, and again whenever it
  // changes. Files arrive as Blobs and are kept here as data: URLs.
  const toDataUrl = (blob) => new Promise((ok) => { const fr = new FileReader(); fr.onload = () => ok(String(fr.result)); fr.onerror = () => ok(null); fr.readAsDataURL(blob); });
  async function save(msg) {
    const files = {};
    for (const f of msg.files || []) {
      if (f && f.id && f.blob) files[f.id] = { data: await toDataUrl(f.blob), fileName: f.fileName, type: f.type };
    }
    await store.set({ kit: msg.kit || null, files, synced: Date.now() });
  }
  window.addEventListener("message", (e) => {
    if (e.source !== window || !e.data || e.data.type !== "radarak-kit-data") return;
    save(e.data);
  });
  const sync = () => window.postMessage({ type: "radarak-ext-hello" }, location.origin);

  // the site can show "extension connected"
  root.dataset.radarakExt = "1";
  document.dispatchEvent(new CustomEvent("radarak-ext"));

  sync();
  document.addEventListener("visibilitychange", () => { if (!document.hidden) sync(); });

  // "Open on ... / Apply on the company site" in a job's details: remember this job for the form
  document.addEventListener("click", (e) => {
    const a = e.target.closest && e.target.closest("#drawerBody a.apply");
    if (!a) return;
    const body = document.getElementById("drawerBody");
    const letter = document.getElementById("dLetterText");
    const pending = {
      at: Date.now(), url: a.href,
      title: (body.querySelector("#drawerTitle") || {}).textContent || "",
      company: (body.querySelector(".dhead .where b") || {}).textContent || "",
      cvId: a.dataset.cv || "", letter: letter ? letter.value : "",
    };
    store.set({ pending });
  }, true);
})();
