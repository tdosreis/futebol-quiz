#!/usr/bin/env python3
"""Correctness tests for the generated-question pipeline.

The danger with generators is silently producing questions with a wrong or
ambiguous answer, so these assertions are about semantics, not plumbing.
"""
import subprocess, os, sys, io, re, json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

TESTS = r"""
<script>
(function(){
  const out = [];
  const ok = (n,c,x) => out.push({n, pass: !!c, extra: x||''});
  try {
    const CIDS = new Set(CL.map(c=>c.id));
    const P = id => PL.find(p=>p.id===id);
    const C = id => CL.find(c=>c.id===id);

    let gen = [];
    for (let i=0;i<8;i++) gen = gen.concat(GEN_QS(2));
    ok('generators produce questions', gen.length > 100, `${gen.length} generated`);
    ok('all generated have text + answers',
       gen.every(q => q.t && q.t.length>5 && Array.isArray(q.a) && q.a.length>0));

    // every answer id must resolve in the right pool
    ok('generated answers resolve',
       gen.every(q => q.a.every(id => (q.type==='player'? P(id): C(id)))),
       'unresolvable answer id');

    // --- semantic check: "por qual clube X jogou" ---
    const cq = gen.filter(q => /Por qual destes clubes/.test(q.t));
    let clubBad = 0, clubDistractorBad = 0;
    cq.forEach(q => {
      const name = q.t.match(/clubes (.+?) jogou/)[1];
      const p = PL.find(x => x.n === name);
      if (!p) { clubBad++; return; }
      if (!p.clubs.includes(q.a[0])) clubBad++;           // answer must be a real club of his
      diffKey='dificil';
      getDisp(q).forEach(o => {                            // no distractor may also be his club
        if (!q.a.includes(o.id) && p.clubs.includes(o.id)) clubDistractorBad++;
      });
    });
    ok('club questions: answer is a real club of the player', clubBad === 0, `${clubBad} bad`);
    ok('club questions: no distractor is also a club of his',
       clubDistractorBad === 0, `${clubDistractorBad} ambiguous tiles`);

    // --- semantic check: position questions ---
    const pq = gen.filter(q => /atuava como/.test(q.t));
    let posBad = 0;
    pq.forEach(q => {
      const want = /goleiro/.test(q.t)?'GK': /defensor/.test(q.t)?'DF': /meia/.test(q.t)?'MF':'FW';
      if (P(q.a[0]).pos !== want) posBad++;
      diffKey='dificil';
      getDisp(q).forEach(o => { if (!q.a.includes(o.id) && o.pos === want) posBad++; });
    });
    ok('position questions have exactly one valid position match', posBad === 0, `${posBad} bad`);

    // --- semantic check: nationality ---
    const nq = gen.filter(q => /defendeu a seleção/.test(q.t));
    let natBad = 0;
    nq.forEach(q => {
      diffKey='dificil';
      const want = P(q.a[0]).ctry;
      getDisp(q).forEach(o => { if (!q.a.includes(o.id) && o.ctry === want) natBad++; });
    });
    ok('nationality questions have no duplicate-country distractors', natBad===0, `${natBad} bad`);

    // --- comparison questions must have a unique answer among the fixed set ---
    const oq = gen.filter(q => /fundado primeiro/.test(q.t));
    let foundedBad = 0;
    oq.forEach(q => {
      const set = q.fixed.map(C);
      const min = Math.min(...set.map(c=>c.f));
      if (set.filter(c=>c.f===min).length !== 1) foundedBad++;
      if (C(q.a[0]).f !== min) foundedBad++;
    });
    ok('"founded first" has a unique correct club', foundedBad===0, `${foundedBad} bad / ${oq.length}`);

    const tq = gen.filter(q => /mais títulos do Brasileirão/.test(q.t));
    let titleBad = 0;
    tq.forEach(q => {
      const set = q.fixed.map(C);
      const mx = Math.max(...set.map(c=>c.br));
      if (set.filter(c=>c.br===mx).length !== 1) titleBad++;
      if (C(q.a[0]).br !== mx) titleBad++;
    });
    ok('"most titles" has a unique correct club', titleBad===0, `${titleBad} bad / ${tq.length}`);

    const lq = gen.filter(q => /JÁ venceram a Libertadores/.test(q.t));
    let libBad = 0;
    lq.forEach(q => {
      const set = q.fixed.map(C);
      const winners = set.filter(c=>c.lib>0).map(c=>c.id).sort().join();
      if (winners !== q.a.slice().sort().join()) libBad++;
    });
    ok('Libertadores multi-select lists every winner shown', libBad===0, `${libBad} bad / ${lq.length}`);

    const mq = gen.filter(q => /passaram pelo/.test(q.t));
    let mateBad = 0;
    mq.forEach(q => {
      const club = Object.keys(CLUB_NAMES).concat(CL.map(c=>c.id))
                     .find(id => clubName(id) === q.t.match(/passaram pelo (.+)$/)[1]);
      if (!club) { mateBad++; return; }
      if (!q.a.every(id => P(id).clubs.includes(club))) mateBad++;
      diffKey='dificil';
      getDisp(q).forEach(o => {
        if (!q.a.includes(o.id) && P(o.id).clubs.includes(club)) mateBad++;
      });
    });
    ok('team-mate questions: only listed players match the club', mateBad===0, `${mateBad} bad`);


    // ---- GEN2 templates ----
    const oddq = gen.filter(q => /NÃO era/.test(q.t));
    let oddBad = 0;
    oddq.forEach(q => {
      const want = /goleiro/.test(q.t)?'GK': /defensor/.test(q.t)?'DF': /meia/.test(q.t)?'MF':'FW';
      const set = q.fixed.map(P);
      if (set.filter(p => p.pos !== want).length !== 1) oddBad++;
      if (P(q.a[0]).pos === want) oddBad++;
    });
    ok('"odd one out" has exactly one non-matching player', oddBad===0, `${oddBad} bad / ${oddq.length}`);

    const longq = gen.filter(q => /carreira mais longa/.test(q.t));
    let longBad = 0;
    longq.forEach(q => {
      const set = q.fixed.map(P);
      const span = p => p.era[1]-p.era[0];
      const mx = Math.max(...set.map(span));
      if (set.filter(p=>span(p)===mx).length !== 1) longBad++;
      if (span(P(q.a[0])) !== mx) longBad++;
    });
    ok('"longest career" answer really is the longest', longBad===0, `${longBad} bad / ${longq.length}`);

    const contq = gen.filter(q => /mesma época que/.test(q.t));
    let contBad = 0;
    contq.forEach(q => {
      const subj = PL.find(x => q.face === x.img && q.t.indexOf(x.n) !== -1);
      if (!subj) { contBad++; return; }
      const ov = x => Math.min(x.era[1],subj.era[1]) - Math.max(x.era[0],subj.era[0]) >= 5;
      const set = q.fixed.map(P);
      if (set.filter(ov).length !== 1) contBad++;
      if (!ov(P(q.a[0]))) contBad++;
    });
    ok('"same era" has exactly one contemporary', contBad===0, `${contBad} bad / ${contq.length}`);

    const stateq = gen.filter(q => / é de /.test(q.t));
    let stBad = 0;
    stateq.forEach(q => {
      const st = C(q.a[0]).s;
      diffKey='dificil';
      getDisp(q).forEach(o => { if (!q.a.includes(o.id) && o.s === st) stBad++; });
    });
    ok('state questions have no same-state distractor', stBad===0, `${stBad} bad / ${stateq.length}`);

    const libq = gen.filter(q => /mais títulos da Libertadores/.test(q.t));
    let libBad2 = 0;
    libq.forEach(q => {
      const set = q.fixed.map(C);
      const mx = Math.max(...set.map(c=>c.lib));
      if (set.filter(c=>c.lib===mx).length !== 1) libBad2++;
      if (C(q.a[0]).lib !== mx) libBad2++;
    });
    ok('"most Libertadores" has a unique winner', libBad2===0, `${libBad2} bad / ${libq.length}`);

    const multiNat = gen.filter(q => /Selecione os 2 jogadores de/.test(q.t));
    let mnBad = 0;
    multiNat.forEach(q => {
      const ctry = P(q.a[0]).ctry;
      const set = q.fixed.map(P);
      if (set.filter(p=>p.ctry===ctry).length !== q.a.length) mnBad++;
    });
    ok('country multi-select lists every match shown', mnBad===0, `${mnBad} bad / ${multiNat.length}`);

    const stadq = gen.filter(q => /manda seus jogos/.test(q.t));
    let sdBad = 0;
    stadq.forEach(q => { if (!C(q.a[0])) sdBad++; });
    ok('stadium questions resolve to a real club', sdBad===0, `${sdBad} bad / ${stadq.length}`);

    // --- fixed sets always render 10 tiles ---
    let fixedBad = 0;
    gen.filter(q=>q.fixed).forEach(q => { if (getDisp(q).length !== q.fixed.length) fixedBad++; });
    ok('fixed-set questions render the exact tile set', fixedBad===0, `${fixedBad} bad`);

    // --- integration: full games still build with generators on ---
    ['facil','moderado','dificil'].forEach(k => {
      diffKey = k;
      const g = buildGame(k);
      const cfg = DIFFS.find(d=>d.key===k);
      ok(`[${k}] game builds with generators`, g.qs.length === cfg.n, `${g.qs.length}`);
      let bad = 0;
      g.qs.forEach(q => {
        const d = getDisp(q);
        if (!q.a.every(a => d.some(o=>o.id===a))) bad++;
        if (new Set(d.map(o=>o.id)).size !== d.length) bad++;
      });
      ok(`[${k}] all rendered boards are valid`, bad===0, `${bad} bad boards`);
    });

    const g = buildGame('dificil');
    const genShare = g.qs.filter(q=>q.face||q.fixed||q.pool).length;
    ok('hard games actually include generated questions', genShare > 0, `${genShare}/${g.qs.length}`);

  } catch(e) { out.push({n:'EXCEPTION', pass:false, extra:(e&&(e.stack||e.message))||String(e)}); }
  const el=document.createElement('div'); el.id='TESTOUT';
  el.textContent=JSON.stringify(out); document.body.appendChild(el);
})();
</script>
"""

src = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
tmp = os.path.join(ROOT, "_test_gen.html")
io.open(tmp, "w", encoding="utf-8").write(src.replace("</body>", TESTS + "</body>"))
try:
    dom = subprocess.run([CHROME, "--headless", "--disable-gpu", "--virtual-time-budget=12000",
                          "--allow-file-access-from-files", "--dump-dom", "file://" + tmp],
                         capture_output=True, text=True, timeout=180).stdout
finally:
    os.remove(tmp)

m = re.search(r'<div id="TESTOUT">(.*?)</div>', dom, re.S)
if not m:
    print("!! no test output");
    for e in re.findall(r"Uncaught[^<\n]*", dom)[:5]: print("   ", e)
    sys.exit(1)
res = json.loads(m.group(1).replace("&quot;",'"').replace("&amp;","&").replace("&lt;","<").replace("&gt;",">"))
npass = sum(1 for r in res if r["pass"])
for r in res:
    print(f"  [{'PASS' if r['pass'] else 'FAIL'}] {r['n']}" + (f"   ({r['extra']})" if r["extra"] else ""))
print(f"\n{npass}/{len(res)} passed")
sys.exit(0 if npass == len(res) else 1)
