const CACHE = "kz-ai-shell-v3";
const SHELL = ["/", "/dashboard", "/login", "/register", "/icons/kz-ai.svg", "/manifest.webmanifest"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then(async (cache) => {
        // Cache each shell route independently: one unavailable route must not
        // prevent the updated service worker from installing.
        await Promise.all(SHELL.map(async (path) => {
          try {
            const response = await fetch(path, { cache: "reload" });
            if (response.ok && response.type === "basic") {
              await cache.put(path, response);
            }
          } catch {
            // Offline at install time: the worker still installs successfully.
          }
        }));
      })
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key.startsWith("kz-ai-shell-") && key !== CACHE)
        .map((key) => caches.delete(key)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (
    request.method !== "GET" ||
    url.origin !== self.location.origin ||
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/_next/") ||
    url.pathname === "/health"
  ) {
    return;
  }

  // Always fetch page navigations from the live deployment. Replaying cached
  // HTML after a new release can mismatch its JavaScript chunks and show a
  // white screen in an installed Home Screen shortcut.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(async () => {
        const cached = await caches.match(request, { ignoreSearch: true });
        if (cached) return cached;
        return new Response(
          "<!doctype html><html lang=\"en\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>King Zarry AI offline</title><body style=\"background:#030916;color:#c8e6f5;font:16px system-ui;padding:2rem\"><h1>King Zarry AI is offline</h1><p>Reconnect to the internet and reopen the app.</p></body></html>",
          { headers: { "Content-Type": "text/html; charset=utf-8" }, status: 503 }
        );
      })
    );
    return;
  }

  // Cache only known install assets. Do not cache arbitrary HTML or Next.js
  // runtime responses that can become incompatible after deployment.
  if (!SHELL.includes(url.pathname)) return;

  event.respondWith(
    fetch(request).then((response) => {
      if (response.ok && response.type === "basic") {
        const copy = response.clone();
        event.waitUntil(caches.open(CACHE).then((cache) => cache.put(url.pathname, copy)));
      }
      return response;
    }).catch(async () => {
      const cached = await caches.match(url.pathname);
      return cached || new Response("Offline", { status: 503 });
    })
  );
});
