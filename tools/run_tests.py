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
        const want = q.fixed ? q.fixed.length : 10;
        if (d.length !== want) sizeOk = false;
        const s = new Set(d.map(x=>x.id));
        if (s.size !== d.length) dupOk = false;
        if (!q.a.every(a => s.has(a))) allOk = false;
      });
      ok(`[${k}] every option set is the size it should be`, sizeOk);
      ok(`[${k}] no duplicate tiles`, dupOk);
      ok(`[${k}] correct answers always present`, allOk);
    });

    // ---- THE key test: hard distractors must be more similar than easy ----
    function avgSim(k, samples) {
      diffKey = k;
      let tot = 0, n = 0;
      for (let i = 0; i < samples; i++) {
        const g = buildGame(k);
        g.qs.forEach(q => {
          if (q.type !== 'player') return;
          const ref = PL.find(p => p.id === q.a[0]);
          if (!ref) return;
          getDisp(q).forEach(o => {
            if (q.a.includes(o.id)) return;
            tot += simPlayer(o, ref); n++;
          });
        });
      }
      return n ? tot / n : 0;
    }
    /* Six rounds each was too few: the easy figure swung by five points run to
       run, so this assertion failed on noise rather than on a change. */
    const easy = avgSim('facil', 16), hard = avgSim('dificil', 16), mod = avgSim('moderado', 16);
    /* This used to demand 1.5x, from when fácil drew its wrong answers at
       random. It no longer does: the clue quota runs at every level, because a
       question that names a nationality and then shows one player of it is
       unfair rather than easy, and that puts a floor under fácil's similarity
       (~20 -> ~29). Hard is still half again as plausible, which is what the
       assertion is actually for; 1.35 leaves room for sampling spread without
       letting a real collapse through. */
    ok('hard distractors more plausible than easy', hard > easy * 1.35,
       `easy=${easy.toFixed(1)} mod=${mod.toFixed(1)} hard=${hard.toFixed(1)} ratio=${(hard/easy).toFixed(2)}`);
    ok('moderate sits between easy and hard', mod > easy && mod < hard,
       `easy=${easy.toFixed(1)} mod=${mod.toFixed(1)} hard=${hard.toFixed(1)}`);

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
