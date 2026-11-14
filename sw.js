/* Radarak service worker: makes the site installable and quick on weak mobile data.
   - Pages, code and job data: network first (always fresh when online), the last copy when offline or slow.
   - Fonts, icons and libraries: from the cache first (they rarely change).
   Only this site's own files are handled; analytics and other sites go straight to the network. */
const CACHE = "radarak-v2";   // v2: new colors and icons (Oct 2026)
const SHELL = ["./", "index.html", "style.css", "app.js", "manifest.webmanifest", "icons/icon-192.png",
  "fonts/bricolage-grotesque-latin-700-normal.woff2", "fonts/ibm-plex-sans-arabic-latin-400-normal.woff2"];
const SLOW_MS = 4000;   // on a slow connection, show the saved copy instead of waiting

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

function networkFirst(req) {
  return caches.open(CACHE).then((cache) => {
    const net = fetch(req).then((res) => { if (res.ok) cache.put(req, res.clone()); return res; });
    const slow = new Promise((resolve) => setTimeout(resolve, SLOW_MS)).then(() => cache.match(req, { ignoreSearch: true }));
    return Promise.race([net.catch(() => null), slow]).then((hit) => hit || net)
      .catch(() => cache.match(req, { ignoreSearch: true }).then((hit) => hit || cache.match("index.html")));
  });
}
function cacheFirst(req) {
  return caches.match(req).then((hit) => hit || fetch(req).then((res) => {
    if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
    return res;
  }));
}

self.addEventListener("fetch", (e) => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  if (/\/(fonts|icons|vendor)\//.test(url.pathname)) { e.respondWith(cacheFirst(req)); return; }
  e.respondWith(networkFirst(req));
});

// "My alerts" notifications (only after the visitor turns them on in the installed app): about twice a day the
// browser wakes this worker; if the site has a newer day of data than the visitor last saw, show one short note.
// The worker only reads this site's own meta.json; nothing about the visitor is sent anywhere.
const STATE = "radarak-state";
async function checkNewJobs() {
  const state = await caches.open(STATE);
  const seen = await state.match("seen-day").then((r) => (r ? r.text() : ""));
  const notified = await state.match("notified-day").then((r) => (r ? r.text() : ""));
  const meta = await fetch("data/meta.json", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const day = meta && (meta.generated_at || "").slice(0, 10);
  if (!day || day <= seen || day === notified) return;
  await state.put("notified-day", new Response(day));
  const ar = (self.navigator.language || "").startsWith("ar");
  await self.registration.showNotification(ar ? "وظايف جديدة على رادارك" : "New jobs on Radarak", {
    body: ar ? "وظايف النهارده نزلت. افتح رادارك وشوف الجديد في تنبيهاتك." : "Today's jobs are in. Open Radarak to see what's new for your alerts.",
    icon: "icons/icon-192.png", badge: "icons/icon-192.png", tag: "radarak-new-jobs", data: { url: "./" },
  });
  if (self.navigator.setAppBadge) self.navigator.setAppBadge().catch(() => {});
}
self.addEventListener("periodicsync", (e) => {
  if (e.tag === "radarak-new-jobs") e.waitUntil(checkNewJobs());
});
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
    const open = list.find((c) => "focus" in c);
    return open ? open.focus() : self.clients.openWindow((e.notification.data && e.notification.data.url) || "./");
  }));
});
