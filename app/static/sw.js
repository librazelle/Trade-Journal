const CACHE_NAME = "trade-lens-shell-v2";
const APP_SHELL = [
  "/",
  "/static/style.css",
  "/static/app.js",
  "/static/manifest.webmanifest",
  "/static/trade-lens-icon.svg"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key.startsWith("trade-lens-shell-") && key !== CACHE_NAME).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;

  // Do not cache API responses, streaming news, or changing server data.
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/stream/")) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).then(response => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
        }
        return response;
      }).catch(async () => {
        const exact = await caches.match(request);
        if (exact) return exact;
        const root = await caches.match("/");
        if (root) return root;
        return new Response("Trade-Lens offline. Buka aplikasi saat online sekali agar halaman tersimpan.", {
          status: 503,
          headers: { "Content-Type": "text/plain; charset=utf-8" }
        });
      })
    );
    return;
  }

  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(request).then(cached => {
        const network = fetch(request).then(response => {
          if (response.ok) caches.open(CACHE_NAME).then(cache => cache.put(request, response.clone()));
          return response;
        }).catch(() => cached);
        return cached || network;
      })
    );
  }
});
