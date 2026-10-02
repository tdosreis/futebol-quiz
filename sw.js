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
   generated.

   v36: a written answer carries its crest, flag, face or ground, the
   question cards' drawings are repainted, and flags are printed ones.

   v37: clubs with no crest file wear their colours on a drawn badge.

   v38: the page is measured against the phone's real screen, so a reveal
   never has to be scrolled to reach Próxima.

   v39: the body is held to the real screen as well as the sheet.

   v40: a figurinha turned over in the zoom is as wide as its front.

   v41: a zoomed figurinha's band and club fit whole, "da Bahia", a map
   that is Brazil, and a terrace you can read.

   v42: a question is pictured by its topic — the Bola de Ouro, the scorer's
   boot, the keeper's gloves — and a board's band clears its number tab.

   v43: Antony's card is drawn; his "photo" was a church in Antony, France.

   v44: every question picture is a photograph.

   v45: 1,003 new questions: who-am-I (players, coaches, clubs, legends),
        odd-one-out, rules, years, women's football, derbies.

   v46: sticker names keep their accents; album pockets fill the page; the
        light theme gets light album pages; one-row progress; the trophy
        photo framed on the cup.

   v47: four who-am-I clues that the 2026 World Cup could have made stale
        are worded so they stay true.

   v48: pictures keep a cache of their own across updates and are retried
        once before a card gives up; a country-hidden band says ANOS 90;
        the Inter clue no longer names Milan.

   v49: a question about a player shows his face, cropped clear of the
        shirt when the shirt could answer it; names in the text are matched
        as proper nouns; ambiguous or self-revealing nicknames are gone.

   v50: mascots are Fluent Emoji 3D figures on the club's colours; ten
        missing nationality words (argelina…); no decoy crest on a
        which-club question; position words fixed; flags on nationality
        questions.

   v51: no question answers itself — the ground question drops the Arena do
        Grêmio and the cities that name their club, "na Vila Belmiro" and
        "no Rio de Janeiro" take their article, and six written questions
        that said their own answer are reworded; the answer is no longer the
        only long option on four boards; four questions that sat in both
        curiosos and feminino are down to one copy each; a club takes its own
        article — "a camisa da Juventus", "companheiro na Portuguesa",
        "Fundação da Chapecoense" — and the Inter is at last a Inter.

   v52: the album opens again after a run that earned a figurinha. It threw
        on the way in — movedScreen was a const inside go(), read from
        html(), which go() calls but does not contain — so the screen never
        rendered and the button did nothing, for anyone who had just won a
        sticker and only for them. It also does now what it was written to
        do: open on the spread that sticker is in, with the sticker marked.

   v53: the icons are the question mark now, not the football — the same
        picture as the Play listing, drawn by tools/make_icons.py. /icons/ is
        in the versioned cache, so this bump is what replaces them.

   v54: 1,037 new questions, every question and answer pictured, in new
        formats: placar (guess the missing side of a scoreline), escalação
        (a line-up with one gap), duelo (two options), duplas (mark both),
        linha do tempo with faces and flags, quem sou eu with written clues,
        and ache o intruso.

   v55: figurinhas are printed copies now — comum, prata, holográfica or
        ouro, autografadas and misprints, graded and numbered, a check code
        and a guilloché seal on the back. Runs end in a packet to tear open,
        the vitrine shows the best ones off, complete teams print a gold
        team photo, and a great player's birthday prints a one-day edition.
        Adds the Mr Dafoe font for the autographs.

   v56: the zoomed figurinha is drawn at its real size instead of a pocket
        stretched 4x (it was blurry), the turn is lighter (no backdrop blur,
        no drop-shadow filters, the foil sweep moves by transform, the tilt
        only restyles the foil), and the seleções are shield badges with a
        star per World Cup won.

   v57: every picture is repainted — players and scenes as layered brush
        paintings (tools/paint), crests and mascots as gouache, flags as
        painted cloth — and the drawn flags, badges and mascots carry the
        same folds and brush tooth. The picture cache is renamed so phones
        drop the old photographs instead of keeping them for good.

   v58: back to the original photographs — the filter paintings were not
        close enough to hand-painted work. The picture cache is renamed
        again so phones drop the painted copies. tools/paint stays.

   v59: a card tapped on the packet's summary zoomed behind the packet and
        left a blank pocket; the zoom now sits above it. Alex's career gains
        Flamengo and Parma (and runs to 2014), so neither can be offered as
        a wrong answer.

   v60: 135 real crests for clubs that were only initials (Leicester,
        CSKA, Toulouse, Nantes, Rennes, Estrela Vermelha…, in img/crests);
        the clubs still without one are drawn as shields in their colours;
        and every written answer now has a picture — a dated stamp for a
        year, a scoreboard, a formation on a pitch, a medallion, a portrait
        silhouette, an illuminated initial. 
   v61: 291 player portraits repainted by hand-style gouache and watercolour
        (Gemini, tools/gemini); the six that failed or drifted keep their
        photograph. The picture cache is renamed so phones fetch them. 
   v62: the atelier — every screen painted to match the portraits: night
        paper by default (cream by day), watercolour washes, gold and green
        brushstroke buttons, painted cards for tiles, lifelines and panels,
        dabs of paint for the icons. Materials in img/atelier.
   v63: the cover is a magazine cover — a painted portrait full bleed, the
        title over its foot, the modes as a contents list, the album as a fan
        of stickers; answers are ivory paper slips dealt on the page, painted
        gold when chosen, green or red at the verdict. Washes feathered.
   v64: the details — opaque paper cards instead of streaky translucent ones,
        the quiz header as lettering, the question photo mounted as a print,
        the verdict on a torn sheet, the end numbers set as a table, paint
        dabs for the round log, a gold wash behind the trophy.
   v65: sound and effects — a room reverb on every cue; a kalimba that climbs
        with each answer of a streak, the crowd cheering a streak and
        groaning a miss, a referee's whistle at time-out and full time,
        clock ticks in the last five seconds, a counting scoreboard; right
        answers splash green paint around the slip with the points rising
        in gold, misses bleed red, streaks warm the page's edges, and wins
        rain painted flecks.
   v66: the album and the vitrine in the atelier — deckled era pages with a
        lettered title over a brushstroke of the era's colour, the index as
        flags with a gold stroke under the open one; the vitrine with a
        title, paint swatches for the four stocks, a painted cabinet and the
        collections as a contents list.
   v67: the zoomed figurinha hangs in a gallery — a dark painted wall lit
        behind the card in the colour of its stock, a museum label (number,
        name, stock, serial, grade), brushstroke actions, a dab to close.
   v68: fixes — a long question no longer runs under the header and the
        board; clubs with no crest get a shield in their colours instead of
        the whole board turning to letters; "Derby del Sole" is not a man;
        boards of "Derby della…" print the letter that tells them apart;
        "não é do Ceará" (and five more) show the state on the map; the
        question's flag is mounted like a print; pictures a size larger.
   v69: Marseille's crest was Inter's (the source had it wrong) — a redrawn
        OM badge; "Lionel Messi" finds the album's Messi; a question naming a
        club shows its crest (Atlético, Liverpool, Santos) rather than a flag
        or a stadium; men with no photo are a sepia bust, coaches in a suit;
        the line-up on a painted pitch with names on slips; the scoreboard
        on dark paper.
   v70: the figurinha in the atelier — printed on cold-press paper, the
        painting on a mat with a hairline, the country in small capitals over
        a brushstroke of its colours, the name in the serif, the club in
        italic; numbers on paper labels; the verdict's card back on a slip;
        busts that differ by hairline, suit and tie.
   v71: a board of coaches is found by its verbs too ("dirigi a Seleção"),
        a one-word coach (Tite) is a bust, not a letter; a man the album has
        painted keeps his portrait on a board of busts (Zidane, Cruyff,
        Zagallo…); "El Clásico" is not a man.
   v72: "logo depois" is not a logo (the Bundesliga board gets its crests);
        Pelé and Cruyff keep their faces beside modern players; grounds,
        cities, leagues and matches are never busts; ready for painted
        portraits of people outside the album and painted mascots.
   v73: a board of players is busts even for one-word names (Mazinho,
        Viola); trophies and tournaments are never busts; decades read
        "Anos 2000" on a calendar stamp; an audit of the bank fixed facts
        that had drifted (Klose's record, Atlético's 1937 title, lineups).
   v74: answers that are not men or clubs are drawn as what they are — the
        dribble as a move, the derby as two shields, a ground, a cup, a city,
        a pitch with the spot lit, a mascot, a shirt in its colour; women get
        their own busts; small round portraits zoom onto the face; "Quem sou
        eu?" opens on a mystery portrait, rules on a chalkboard; Antony's
        card waits for its portrait in ink.
   v75: governing bodies are seals in their own colours (no longer six
        identical globes); questions about them open on a drawn globe; the
        1958 final question no longer has two right answers (Pelé and Vavá
        both scored twice). */
const VERSION = 'v75';
const CACHE   = 'futebol-quiz-' + VERSION;
/* Photos, crests and flags never change under the same name (each file is
   named by its content), so they live in a cache of their own that survives
   updates. Wiping them with every version meant the first game after an
   update re-downloaded every picture, and on a weak signal cards came up
   blank. */
const IMG_CACHE = 'futebol-quiz-img-3';

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
      .then(keys => Promise.all(keys.filter(k => k !== CACHE && k !== IMG_CACHE).map(k => caches.delete(k))))
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

  // pictures: cache-first from the lasting cache, one retry on the network
  if (sameOrigin && url.pathname.includes('/img/')) {
    const key = url.origin + url.pathname;
    const get = () => fetch(key);
    e.respondWith(
      caches.open(IMG_CACHE).then(c => c.match(key).then(hit => hit ||
        get().catch(() => new Promise(r => setTimeout(r, 600)).then(get)).then(res => {
          if (res && res.status === 200) c.put(key, res.clone());
          return res;
        })))
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
