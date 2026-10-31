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
