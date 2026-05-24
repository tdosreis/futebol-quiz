/* ────────────────────────────────────────────────
   Futebol Quiz BR — Service Worker
   Cache-first strategy with background refresh
──────────────────────────────────────────────── */
const CACHE  = 'futebol-quiz-v1';
const ASSETS = [
  '/futebol-quiz/',
  '/futebol-quiz/index.html',
  '/futebol-quiz/manifest.json',
  '/futebol-quiz/icons/icon-72.png',
  '/futebol-quiz/icons/icon-96.png',
  '/futebol-quiz/icons/icon-128.png',
  '/futebol-quiz/icons/icon-144.png',
  '/futebol-quiz/icons/icon-152.png',
  '/futebol-quiz/icons/icon-192.png',
  '/futebol-quiz/icons/icon-384.png',
  '/futebol-quiz/icons/icon-512.png',
];

/* ── Install: precache all assets ── */
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

/* ── Activate: delete old caches ── */
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

/* ── Fetch: cache-first, fallback to network ── */
self.addEventListener('fetch', e => {
  // Only handle same-origin + Google Fonts
  const url = new URL(e.request.url);
  const isSameOrigin = url.origin === self.location.origin;
  const isFonts = url.hostname === 'fonts.googleapis.com'
               || url.hostname === 'fonts.gstatic.com';

  if (!isSameOrigin && !isFonts) return;

  e.respondWith(
    caches.match(e.request).then(cached => {
      const networkFetch = fetch(e.request).then(res => {
        if (res && res.status === 200) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      }).catch(() => null);

      return cached || networkFetch;
    })
  );
});
