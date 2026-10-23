// Lost & Found Desk service worker.
// Keeps the app's own files on the phone so it opens fast, and shows an offline screen with no signal.
// Never stores API answers or photos: those are private and must always come fresh from the server.

const VERSION = "lf-v1";   // change this when the files below change, so phones fetch the new set
const SHELL = ["/", "/app.js", "/help", "/offline.html", "/manifest.webmanifest",
               "/icons/icon-192.png", "/icons/icon-512.png", "/icons/apple-touch-icon.png"];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  // private or sign-in traffic: always straight to the network, never stored
  if (/^\/(api|photos|login|logout|auth|dev-login)(\/|$)/.test(url.pathname)) return;

  if (req.mode === "navigate") {
    // pages: try the network first so people see the latest version; fall back to the saved copy, then offline
    event.respondWith(
      fetch(req)
        .then(res => { const copy = res.clone(); if (res.ok) caches.open(VERSION).then(c => c.put(req, copy)); return res; })
        .catch(() => caches.match(req).then(hit => hit || caches.match("/offline.html")))
    );
    return;
  }
  // the app's own files: saved copy first, refreshed in the background
  event.respondWith(
    caches.match(req).then(hit => {
      const fresh = fetch(req).then(res => {
        if (res.ok) { const copy = res.clone(); caches.open(VERSION).then(c => c.put(req, copy)); }
        return res;
      }).catch(() => hit);
      return hit || fresh;
    })
  );
});
