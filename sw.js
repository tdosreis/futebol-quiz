/* ────────────────────────────────────────────────
   Futebol Quiz BR — Service Worker

   Strategy differs by resource, on purpose:
     • HTML document → network-first, so a deploy reaches players
       immediately (the app is a TWA: the web page *is* the update
       channel, there is no Play release to ship).
     • images/icons  → cache-first; filenames are content-hashed so
       they can never go stale.
──────────────────────────────────────────────── */
/* v8: every image became a .webp, so every image URL changed. The old cache
   holds 19MB of .jpg and .png nothing asks for any more; bumping the version
   is what drops them instead of leaving them on the phone for ever.

   v7: the crest set was replaced wholesale when every club moved to its
   official escudo, and 86 players joined. Filenames are content-hashed, so
   nothing stale can be served — but ~40 files no longer referenced by anything
   would have sat in the old cache forever. Bumping the version drops them.

   v9: the album's page turn is now driven by the finger rather than played
   back as an animation, and the leaf is lit differently. Nothing but
   index.html changed, but a cached shell would keep serving the old turn.

   v10: the turning page is sliced and bends now, instead of swinging as one
   rigid plane. index.html again — and v9 has already gone out, so it needs
   its own version or anyone already on v9 keeps the flat one.

   v11: the slices sit in a single 3D context now, because nested preserve-3d
   was the likeliest reason the bend rendered here and not on a real phone.
   And the page-turn sound is one quiet rustle instead of three parts.

   v12: the turn is slower and eased differently — it had been flicking.

   v13: the page trails the thumb now instead of being welded to it.

   v14: the fall is slower again and the sheet bends a little further.

   v15: the curl now catches a highlight as it turns, instead of just
   darkening — paper is shiny enough to throw back light at the fold, and
   without it the page read as flat cardboard mid-turn rather than a
   curving sheet.

   v16: the curl is gone. Six versions of bend, light and drag physics never
   read right on every phone this actually runs on, and a book that turns
   wrong is worse than one that just slides — so the page now slides in from
   the side it was turned towards and nothing more. index.html again, for
   the same reason as every version above it: the shell has to stop serving
   the old turn.

   v17: the figurinhas especiais are printed cards now, on the home screen
   and on their own. index.html again.

   v18: home goes back to the small symbols; the cards live only on their
   own screen, opened on the one you tapped.

   v19: the page is fetched past the HTTP cache, so a deploy shows on the
   next open instead of up to ten minutes later.

   v20: every page of the album is twenty pockets of one shape, on printed
   paper. index.html again.

   v21: a page of the album fits on one screen, arrows in its foot.

   v22: every screen was taller than the phone by the navigation bar, and a
   short screen now fits the album page too.

   v23: 851 new written questions, and the champion tables brought up to
   2025-26.

   v24: a figurinha is held up and turned over, the album has no middle
   line and its pages cross as they turn, and every question has a picture
   framed for its era.

   v25: over a thousand written questions, with rounds kept about a third
   generated. */
const VERSION = 'v26';
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
    // network-first: always try to pick up a new build. Pages sends
    // max-age=600, so without no-cache the browser's own HTTP cache hands
    // back the previous build for ten minutes after a deploy.
    e.respondWith(
      fetch(req, { cache: 'no-cache' })
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
