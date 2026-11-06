/* Radarak - filters for the static pages (jobs by country/role, companies, juniors, salaries).
   Every list is plain HTML (so it works without JavaScript and search engines can read it). This script
   filters, sorts and pages through it. Markup contract:
     <div data-filters data-page="25">                       one filterable block
       <input|select data-f="KEY" data-mode="eq|has|text|flag">  a control; matches item attribute data-KEY
       <select data-sort>  options "KEY:asc|desc|num" </select>
       <span data-count data-tpl="Showing {n} jobs">           result count
       <ol data-list> <li data-KEY="..."> ... </ol>           the items
       <p data-empty hidden>  <button data-more hidden>  <button data-clear hidden>
   Filters are kept in the address (#f=...) so a filtered page can be shared. */
(() => {
  "use strict";
  const norm = (s) => String(s || "").trim().toLowerCase();
  const num = (n) => Number(n).toLocaleString("en-US");

  function setup(root, index) {
    const list = root.querySelector("[data-list]");
    if (!list) return;
    const items = [...list.children];
    const controls = [...root.querySelectorAll("[data-f]")];
    const sortEl = root.querySelector("[data-sort]");
    const countEl = root.querySelector("[data-count]");
    const more = root.querySelector("[data-more]");
    const empty = root.querySelector("[data-empty]");
    const clear = root.querySelector("[data-clear]");
    const page = Number(root.dataset.page) || 0;
    const key = "f" + (index || "");
    let shown = page;

    const value = (c) => (c.type === "checkbox" ? (c.checked ? "1" : "") : norm(c.value));
    const test = (item, f, mode, v) => {
      const d = norm(item.dataset[f]);
      if (mode === "text") return v.split(/\s+/).every((w) => d.includes(w));
      if (mode === "has") return d.split("|").includes(v);
      if (mode === "flag") return d === "1";
      return d === v;
    };

    function readHash() {
      const h = new URLSearchParams(location.hash.slice(1)).get(key);
      if (!h) return;
      const state = new URLSearchParams(h);
      controls.forEach((c) => {
        if (!state.has(c.dataset.f)) return;
        if (c.type === "checkbox") c.checked = state.get(c.dataset.f) === "1";
        else c.value = [...(c.options || [])].find((o) => norm(o.value) === state.get(c.dataset.f))?.value ?? state.get(c.dataset.f);
      });
      if (sortEl && state.has("sort")) sortEl.value = state.get("sort");
    }
    function writeHash(active) {
      const state = new URLSearchParams();
      active.forEach(([f, , v]) => state.set(f, v));
      if (sortEl && sortEl.selectedIndex > 0) state.set("sort", sortEl.value);
      const h = new URLSearchParams(location.hash.slice(1));
      if ([...state].length) h.set(key, state.toString()); else h.delete(key);
      const s = h.toString();
      history.replaceState(null, "", s ? "#" + s : location.pathname + location.search);
    }

    function apply(resetPage) {
      if (resetPage) shown = page;
      const active = controls.map((c) => [c.dataset.f, c.dataset.mode || "eq", value(c)]).filter((x) => x[2]);
      let visible = items.filter((it) => active.every(([f, mode, v]) => test(it, f, mode, v)));
      if (sortEl && sortEl.value) {
        const [f, dir] = sortEl.value.split(":");
        const val = (it) => it.dataset[f] || "";
        visible.sort((a, b) => {
          const x = val(a), y = val(b);
          if (dir === "num") return (y === "" ? -1e12 : +y) - (x === "" ? -1e12 : +x);   // biggest first, blanks last
          const c = x.localeCompare(y);
          return dir === "desc" ? -c : c;
        });
      }
      const set = new Set(visible);
      items.forEach((it) => { if (!set.has(it)) it.hidden = true; });
      visible.forEach((it, i) => { list.appendChild(it); it.hidden = page > 0 && i >= shown; });
      if (countEl) countEl.textContent = countEl.dataset.tpl.replace("{n}", num(visible.length)).replace("{t}", num(items.length));
      if (more) {
        more.hidden = !page || visible.length <= shown;
        more.textContent = more.dataset.tpl.replace("{n}", num(Math.min(page, visible.length - shown)));
      }
      if (empty) empty.hidden = visible.length > 0;
      if (clear) clear.hidden = !active.length;
      writeHash(active);
    }

    controls.forEach((c) => c.addEventListener(c.tagName === "INPUT" && c.type !== "checkbox" ? "input" : "change", () => apply(true)));
    if (sortEl) sortEl.addEventListener("change", () => apply(true));
    if (more) more.addEventListener("click", () => { shown += page; apply(false); });
    if (clear) clear.addEventListener("click", () => {
      controls.forEach((c) => { if (c.type === "checkbox") c.checked = false; else c.value = ""; });
      if (sortEl) sortEl.selectedIndex = 0;
      apply(true);
    });
    // phones: the extra filters fold behind a "Filters" button (open if any of them is in use)
    const toggle = root.querySelector("[data-ftoggle]"), bar = root.querySelector(".fbar");
    const syncToggle = () => {
      const used = controls.some((c) => c.dataset.f !== "t" && value(c)) || (sortEl && sortEl.selectedIndex > 0);
      if (toggle) toggle.classList.toggle("on", used);
    };
    if (toggle) toggle.addEventListener("click", () => {
      const open = !bar.classList.contains("open");
      bar.classList.toggle("open", open); toggle.setAttribute("aria-expanded", String(open));
    });
    controls.forEach((c) => c.addEventListener("change", syncToggle));
    readHash();
    syncToggle();
    root.classList.add("js-on");
    apply(true);
  }

  document.querySelectorAll("[data-filters]").forEach((root, i) => setup(root, i));
  // place switcher (salaries): pick a place, go to its page
  document.querySelectorAll("[data-goto]").forEach((sel) => sel.addEventListener("change", () => { if (sel.value) location.href = sel.value; }));
})();
