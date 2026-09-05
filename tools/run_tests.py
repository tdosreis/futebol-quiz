#!/usr/bin/env python3
"""Headless test harness: injects assertions into a copy of index.html,
renders it in Chrome, and reads the results back out of the DOM."""
import subprocess, tempfile, os, sys, io, re, json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

TESTS = r"""
<script>
(function(){
  const out = [];
  const ok  = (n, c, extra) => out.push({n, pass: !!c, extra: extra || ''});

  try {
    // ---- build / sizing ----
    ['facil','moderado','dificil'].forEach(k => {
      diffKey = k;
      const g = buildGame(k);
      const cfg = DIFFS.find(d => d.key === k);
      ok(`buildGame(${k}) returns ${cfg.n} questions`, g.qs.length === cfg.n,
         `got ${g.qs.length}`);
      ok(`buildGame(${k}) questions all have text`, g.qs.every(q => q.t && q.t.length > 3));
      const ids = g.qs.map(q => q.t);
      ok(`buildGame(${k}) has no duplicate questions`, new Set(ids).size === ids.length,
         `${ids.length - new Set(ids).size} dupes`);
      // tier targeting
      const avgTier = g.qs.reduce((s,q)=>s+qTier(q),0)/g.qs.length;
      ok(`buildGame(${k}) avg tier near ${cfg.tier}`, Math.abs(avgTier - cfg.tier) < 1.05,
         `avgTier=${avgTier.toFixed(2)}`);
    });

    // ---- option sets ----
    ['facil','dificil'].forEach(k => {
      diffKey = k;
      const g = buildGame(k);
      let allOk = true, sizeOk = true, dupOk = true;
      g.qs.forEach(q => {
        const d = getDisp(q);
        /* A question with a `fixed` set shows exactly that set — the head-to-head
           "quem teve a carreira mais longa?" is deliberately two tiles, which is
           why the board has a wide layout and Cortar refuses to spend itself on
           it. Everything else fills the ten. */
        /* A `txt` question answers with a word and carries its own choices,
           so like `fixed` it shows exactly them — six reads better than ten
           when every tile is a sentence. */
        const want = q.type === 'txt' ? q.choices.length
                   : q.fixed ? q.fixed.length : 10;
        if (d.length !== want) sizeOk = false;
        const s = new Set(d.map(x=>x.id));
        if (s.size !== d.length) dupOk = false;
        if (!q.a.every(a => s.has(a))) allOk = false;
      });
      ok(`[${k}] every option set is the size it should be`, sizeOk);
      ok(`[${k}] no duplicate tiles`, dupOk);
      /* Two questions with the same answer are the same question as far as one
         round is concerned, however differently they are worded — "qual goleiro
         soviético é o único a ganhar a Bola de Ouro" and "qual goleiro é o
         único a ganhar a Bola de Ouro" are both Yashin. */
      const ansSeen = new Set();
      let ansOk = true;
      g.qs.forEach(q => {
        const key = (q.a || []).slice().sort().join('|');
        if (ansSeen.has(key)) ansOk = false;
        ansSeen.add(key);
      });
      ok(`[${k}] no two questions share an answer`, ansOk);
      ok(`[${k}] correct answers always present`, allOk);
    });

    // ---- what actually makes a level harder ----
    /* A board is harder when the wrong answers are harder to tell from the
       right one, and that now has three separate parts: they play the same
       position, they are closer in time, and the level leans on those more.
       The old single similarity ratio hid all of it — it saturates, so
       moderado and difícil came out equal while feeling very different. */
    function boardStats(k, samples) {
      diffKey = k;
      let sim = 0, n = 0, samePos = 0, spans = [];
      for (let i = 0; i < samples; i++) {
        const g = buildGame(k);
        g.qs.forEach(q => {
          if (q.type !== 'player') return;
          const ref = PL.find(p => p.id === q.a[0]);
          if (!ref) return;
          const d = getDisp(q);
          let worst = 0;
          d.forEach(o => {
            if (q.a.includes(o.id)) return;
            sim += simPlayer(o, ref); n++;
            if (o.pos === ref.pos) samePos++;
            if (ref.era) worst = Math.max(worst, eraGap(o, ref));
          });
          if (ref.era && !q.fixed && !qAllTime(q)) spans.push(worst);
        });
      }
      spans.sort((x, y) => x - y);
      return { sim: sim / n, pos: samePos / n,
               over25: spans.filter(x => x > 25).length / Math.max(1, spans.length),
               p90: spans[Math.floor(spans.length * 0.9)] || 0 };
    }
    const E = boardStats('facil', 14), M = boardStats('moderado', 14), H = boardStats('dificil', 14);

    ok('hard distractors more plausible than easy', H.sim > E.sim * 1.25,
       `easy=${E.sim.toFixed(1)} mod=${M.sim.toFixed(1)} hard=${H.sim.toFixed(1)}`);
    ok('the harder the level, the more often the position matches',
       H.pos > M.pos * 0.95 && M.pos > E.pos * 1.3,
       `easy=${(E.pos*100).toFixed(0)}% mod=${(M.pos*100).toFixed(0)}% hard=${(H.pos*100).toFixed(0)}%`);
    ok('the harder the level, the tighter the era', H.p90 <= M.p90 && M.p90 <= E.p90,
       `p90 era gap: easy=${E.p90} mod=${M.p90} hard=${H.p90}`);

    /* The point of all of it: a question that is not about the whole of
       history must not put a 1958 striker beside a 2022 one, because then the
       answer is whichever name is the right age. */
    ok('moderado never spans the generations', M.over25 === 0, `${(M.over25*100).toFixed(1)}% of boards`);
    ok('dificil never spans the generations',  H.over25 === 0, `${(H.over25*100).toFixed(1)}% of boards`);
    ok('facil rarely spans the generations',   E.over25 <= 0.25, `${(E.over25*100).toFixed(1)}% of boards`);

    /* ...but an all-time question is *about* the span, so it keeps it. */
    (function(){
      diffKey = 'dificil';
      const all = CATS.flatMap(c => c.qs).filter(q => q.type === 'player' && qAllTime(q));
      ok('all-time questions exist', all.length > 0, `${all.length} found`);
      let widest = 0;
      all.forEach(q => {
        const ref = PL.find(p => p.id === q.a[0]);
        if (!ref || !ref.era) return;
        getDisp(q).forEach(o => { if (!q.a.includes(o.id)) widest = Math.max(widest, eraGap(o, ref)); });
      });
      ok('all-time questions may still cross the generations', widest > 25, `widest gap ${widest}y`);
    })();

    // ---- goalkeeper sanity: the '94 keeper question should offer keepers ----
    diffKey = 'dificil';
    const gkQ = CATS.flatMap(c=>c.qs.map(q=>({...q,_cat:c})))
                    .find(q => q.a[0] === 'taffarel');
    if (gkQ) {
      let gkCount = 0, trials = 12;
      for (let i=0;i<trials;i++) {
        const d = getDisp(gkQ);
        gkCount += d.filter(o => o.pos === 'GK').length;
      }
      ok('hard: keeper question surfaces other keepers', gkCount / trials >= 1.0,
         `avg GKs on board = ${(gkCount/trials).toFixed(2)}`);
    }

    // ---- metadata integrity at runtime ----
    ok('all players have pos', PL.every(p => ['GK','DF','MF','FW'].includes(p.pos)));
    ok('all players have era', PL.every(p => Array.isArray(p.era) && p.era[0] < p.era[1]));
    // Cuiabá EC was founded in 2001, so the old "< 2000" bound was an
    // assumption about the squad, not a fact about football clubs.
    ok('all clubs have founded year',
       CL.every(c => c.f > 1850 && c.f <= new Date().getFullYear()),
       CL.filter(c => !(c.f > 1850 && c.f <= new Date().getFullYear())).map(c=>c.id).join(',') || 'all sane');
    ok('clubName resolves all player clubs',
       PL.every(p => (p.clubs||[]).every(c => clubName(c) && clubName(c) !== c)));

  } catch (e) {
    out.push({n:'EXCEPTION', pass:false, extra: e && (e.stack || e.message || String(e))});
  }

  const el = document.createElement('div');
  el.id = 'TESTOUT';
  el.textContent = JSON.stringify(out);
  document.body.appendChild(el);
})();
</script>
"""

def main():
    src = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    if "</body>" not in src:
        print("no </body>"); return 1
    patched = src.replace("</body>", TESTS + "</body>")
    tmp = os.path.join(ROOT, "_test_run.html")
    io.open(tmp, "w", encoding="utf-8").write(patched)
    try:
        dom = subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--virtual-time-budget=8000",
             "--allow-file-access-from-files", "--dump-dom", "file://" + tmp],
            capture_output=True, text=True, timeout=120).stdout
    finally:
        os.remove(tmp)

    m = re.search(r'<div id="TESTOUT">(.*?)</div>', dom, re.S)
    if not m:
        print("!! test harness produced no output (JS error before tests ran?)")
        errs = re.findall(r"Uncaught[^<\n]*", dom)
        for e in errs[:5]: print("   ", e)
        return 1
    results = json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&")
                                   .replace("&lt;", "<").replace("&gt;", ">"))
    npass = sum(1 for r in results if r["pass"])
    for r in results:
        mark = "PASS" if r["pass"] else "FAIL"
        print(f"  [{mark}] {r['n']}" + (f"   ({r['extra']})" if r["extra"] else ""))
    print(f"\n{npass}/{len(results)} passed")
    return 0 if npass == len(results) else 1

sys.exit(main())
