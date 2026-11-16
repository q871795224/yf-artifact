/* Cache only the pinned runtime. Game rules and saves always use their own versions. */
const runtimePrefix = new URL("vendor/pyodide/", self.registration.scope).href;
const cachePrefix = `yf-artifact-runtime:${self.registration.scope}:`;
const cacheName = cachePrefix + "__RUNTIME_VERSION__";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    try {
      for (const key of await caches.keys()) {
        if (key.startsWith(cachePrefix) && key !== cacheName) await caches.delete(key);
      }
    } catch { /* Restricted browser storage must not prevent play. */ }
    await self.clients.claim();
  })());
});
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET" || !event.request.url.startsWith(runtimePrefix)) return;
  event.respondWith((async () => {
    let cache;
    try {
      cache = await caches.open(cacheName);
      const hit = await cache.match(event.request);
      if (hit) return hit;
    } catch { /* Continue through the network if storage is unavailable. */ }
    const response = await fetch(event.request);
    if (cache && response.ok) {
      event.waitUntil(cache.put(event.request, response.clone()).catch(() => {}));
    }
    return response;
  })());
});
