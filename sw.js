/* ────────────────────────────────────────────────
   Futebol Quiz BR — Service Worker

   Strategy differs by resource, on purpose:
     • HTML document → network-first, so a deploy reaches players
       immediately (the app is a TWA: the web page *is* the update
       channel, there is no Play release to ship).
     • images/icons  → cache-first; filenames are content-hashed so
       they can never go stale.
──────────────────────────────────────────────── */
const VERSION = 'v6';
const CACHE   = 'futebol-quiz-' + VERSION;

const SHELL = [
  '/futebol-quiz/',
  '/futebol-quiz/index.html',
  '/futebol-quiz/manifest.json',
  '/futebol-quiz/icons/icon-192.png',
  '/futebol-quiz/icons/icon-512.png',
];

/* ── Install: precache the shell, take over right away ── */
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(SHELL).catch(() => {}))   // a 404 must not block install
      .then(() => self.skipWaiting())
  );
});

/* ── Activate: drop every previous version ── */
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

/* ── Fetch ── */
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;
  const isFonts = url.hostname === 'fonts.googleapis.com'
               || url.hostname === 'fonts.gstatic.com';
  if (!sameOrigin && !isFonts) return;

  const isDoc = req.mode === 'navigate'
             || req.destination === 'document'
             || url.pathname.endsWith('.html')
             || url.pathname.endsWith('/');

  if (isDoc) {
    // network-first: always try to pick up a new build
    e.respondWith(
      fetch(req)
        .then(res => {
          if (res && res.status === 200) {
            const clone = res.clone();
            caches.open(CACHE).then(c => c.put(req, clone));
          }
          return res;
        })
        .catch(() => caches.match(req).then(r => r || caches.match('/futebol-quiz/index.html')))
    );
    return;
  }

  // everything else: cache-first with background fill
  e.respondWith(
    caches.match(req).then(cached => {
      if (cached) return cached;
      return fetch(req).then(res => {
        if (res && res.status === 200) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(req, clone));
        }
        return res;
      }).catch(() => cached);
    })
  );
});
