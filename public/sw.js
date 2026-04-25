/**
 * Service Worker for Dummar Project Management PWA.
 *
 * Strategy: Network-first with offline fallback cache.
 * - API requests: network only (never cache mutable data)
 * - Static assets (JS, CSS, images): cache after first fetch, serve from cache when offline
 * - Navigation requests: network-first, fallback to cached shell
 */

// CACHE_NAME is bumped whenever the SW logic changes OR when stale assets
// from a previous deploy must be evicted on the next page load. Chrome
// aggressively keeps the previous SW + cache; bumping the name forces the
// activate-handler below to delete every cache that doesn't match.
//
// v3: previous versions cached EVERY navigation/static response including
// non-OK ones (502/503/504 HTML error pages from upstream). When such a
// response was cached, subsequent offline navigations would serve the
// cached error page back to the user. v3 caches only `response.ok === true`
// responses and evicts the v2 cache on activate.
const CACHE_NAME = 'dummar-pwa-v3';

// Static assets to pre-cache during install
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/manifest.json',
];

// ── Install: pre-cache shell ──
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_URLS);
    })
  );
  // Activate immediately without waiting for old SW to finish
  self.skipWaiting();
});

// ── Activate: clean up old caches ──
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  // Take control of all clients immediately
  self.clients.claim();
});

// ── Fetch: network-first for navigation, cache-first for static assets ──
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip API/backend requests — never cache mutable data
  if (
    url.pathname.startsWith('/api') ||
    url.pathname.startsWith('/auth') ||
    url.pathname.startsWith('/uploads') ||
    url.pathname.startsWith('/health') ||
    url.hostname !== self.location.hostname
  ) {
    return;
  }

  // Navigation requests: network-first, fallback to cache.
  // IMPORTANT: only cache OK responses — never cache 502/503/504 HTML error
  // pages, otherwise an offline navigation could serve a stale error page
  // back to the user.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => caches.match('/index.html'))
    );
    return;
  }

  // Static assets: stale-while-revalidate.
  // Same rule as navigation: never cache non-OK responses.
  if (
    url.pathname.endsWith('.js') ||
    url.pathname.endsWith('.css') ||
    url.pathname.endsWith('.png') ||
    url.pathname.endsWith('.svg') ||
    url.pathname.endsWith('.woff2') ||
    url.pathname.endsWith('.woff') ||
    url.pathname.endsWith('.ico')
  ) {
    event.respondWith(
      caches.match(request).then((cached) => {
        const fetchPromise = fetch(request).then((response) => {
          if (response && response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        });
        return cached || fetchPromise;
      })
    );
    return;
  }
});
