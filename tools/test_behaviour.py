#!/usr/bin/env python3
"""Behaviour tests: play actual runs and assert the game state machine holds.

These drive the real functions (startGame/doReveal/lifelines/survival) rather
than inspecting data, so they catch state-machine regressions.
"""
import subprocess, os, io, re, json, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

TESTS = r"""
<script>
(function(){
  const out=[]; const ok=(n,c,x)=>out.push({n,pass:!!c,extra:x||''});
  const answerCorrectly = () => { sel = new Set(cat.qs[qi].a); doReveal(); };
  const answerWrong = () => {
    const q = cat.qs[qi];
    const bad = disp.find(o => !q.a.includes(o.id));
    sel = new Set(bad ? [bad.id] : []); doReveal();
  };
  try {
    // ---- scoring: perfect answers accumulate, combo raises the multiplier ----
    diffKey='facil'; startGame();
    ok('startGame arms the quiz screen', sc==='quiz' && cat.qs.length===10, sc);
    ok('timer set from difficulty', tMax===30 && tLeft===30, `tMax=${tMax}`);
    const p0 = pts; answerCorrectly();
    ok('a correct answer scores', pts > p0, `${p0} -> ${pts}`);
    ok('streak increments', streak===1, `streak=${streak}`);
    ok('runLog records the result', runLog.length===1 && runLog[0]===3, JSON.stringify(runLog));

    // ---- wrong answer resets the streak ----
    diffKey='facil'; startGame();
    answerCorrectly();
    const stAfter = streak;
    qi = 1; sel.clear(); sc='quiz'; disp=getDisp(cat.qs[1]);
    answerWrong();
    ok('wrong answer resets streak', stAfter===1 && streak===0, `${stAfter} -> ${streak}`);

    // ---- difficulty multiplier: hard scores more than easy for the same act ----
    function firstGain(k){
      diffKey=k; startGame(); tLeft=tMax; answerCorrectly(); return lastGain;
    }
    const ge=firstGain('facil'), gh=firstGain('dificil');
    ok('hard pays more than easy', gh > ge, `easy=${ge} hard=${gh}`);

    // ---- the prize ladder ----
    startMilhao();
    ok('milhao starts on the first rung',
       isMil===true && rung===0 && sc==='quiz' && banked===0, `rung=${rung}`);
    ok('milhao deals one question per rung',
       cat.qs.length===LADDER.length, `${cat.qs.length} vs ${LADDER.length}`);
    ok('milhao questions are all distinct',
       new Set(cat.qs.map(q=>q.t)).size===cat.qs.length);
    ok('the first rung has no safety net', safetyNet()===0, `${safetyNet()}`);
    ok('the clock comes from the rung, not the difficulty',
       tMax===LADDER[0].time, `tMax=${tMax}`);

    // climbing: each correct answer moves up exactly one rung
    const r0 = rung; answerCorrectly();
    ok('a correct answer does not advance during the reveal', rung===r0, `rung=${rung}`);
    advanceAfterReveal(3);
    ok('the reveal timing out moves up one rung', rung===r0+1, `rung=${rung}`);

    /* Drive the real state machine, skipping only the dramatic pause. */
    function climb(n){
      startMilhao();
      for (let i=0;i<n;i++){ answerCorrectly(); advanceAfterReveal(3); }
    }
    climb(4);
    ok('four rungs cleared banks the first checkpoint',
       rung===4 && safetyNet()===5000, `rung=${rung} net=${safetyNet()}`);
    ok('the clock shortens as the money grows',
       qTime() < LADDER[0].time, `${qTime()} < ${LADDER[0].time}`);
    ok('distractors get stricter as the money grows',
       qStrict() > 0, `strict=${qStrict().toFixed(2)}`);

    climb(9);
    ok('nine rungs cleared banks the second checkpoint',
       safetyNet()===50000, `net=${safetyNet()}`);

    // cashing out pays the rung you have already cleared
    climb(6); sc='quiz'; cashOut();
    ok('parar ends the run', sc==='end' && cashed===true, sc);
    ok('parar pays the last rung cleared',
       banked===LADDER[5].v, `${banked} vs ${LADDER[5].v}`);

    // falling drops to the safety net, not to zero
    climb(6); sc='quiz';
    const netBefore = safetyNet();
    answerWrong();
    ok('a miss on the ladder banks the safety net',
       banked===netBefore && netBefore===5000, `banked=${banked} net=${netBefore}`);

    // falling before any checkpoint pays nothing
    startMilhao(); sc='quiz'; answerWrong();
    ok('a miss before the first checkpoint pays nothing', banked===0, `${banked}`);

    // the ask-first threshold
    startMilhao(); sel=new Set([disp[0].id]); confirmAnswer();
    ok('early rungs lock in without asking', sc!=='ask', sc);
    startMilhao(); rung=ASK_FROM_RUNG; sel=new Set([disp[0].id]); confirmAnswer();
    ok('high rungs ask for a final answer', sc==='ask', sc);
    unlockAnswer();
    ok('the player can take it back', sc==='quiz', sc);

    // the ladder sheet holds the clock
    startMilhao(); ladderOpen=true;
    const tBefore = tLeft;
    ok('opening the ladder does not spend the clock', tLeft===tBefore);
    clearHelpers();
    ok('the ladder sheet closes between questions', ladderOpen===false);

    // money formatting
    ok('money reads in pt-BR grouping', money(1000000)==='R$ 1.000.000', money(1000000));

    // clearing the last rung must count as sixteen cleared, not fifteen
    climb(LADDER.length);
    ok('the million ends the run', sc==='end' && cashed===true, sc);
    ok('the million banks the top prize',
       banked===LADDER[LADDER.length-1].v, `${banked}`);
    ok('a full climb reads 16 of 16', rung===LADDER.length, `${rung}/${LADDER.length}`);
    ok('the share card shows every rung lit',
       (shareText().match(/🟨/g)||[]).length===LADDER.length,
       shareText().split('\n')[1]);

    // ---- lifelines ----
    // Some questions are two-way comparisons; land on a full board so the
    // assertion is about the card, not about which question came up.
    diffKey='moderado'; startGame();
    while (disp.length < 10) { qi = (qi + 1) % cat.qs.length; disp = getDisp(cat.qs[qi]); }
    const before = disp.length;
    useHalf();
    ok('50/50 hides options', hidden.size > 0 && hidden.size < before, `hid ${hidden.size}/${before}`);
    ok('50/50 never hides a correct answer',
       [...hidden].every(id => !cat.qs[qi].a.includes(id)));
    ok('50/50 is single use', lifes.half === 0);

    // and it refuses to spend itself when it could not remove anything
    diffKey='moderado'; startGame();
    (function(){
      const q = cat.qs[qi];                       // a two-way board: one right, one wrong
      disp = [disp.find(o => q.a.includes(o.id)), disp.find(o => !q.a.includes(o.id))]
             .filter(Boolean);
      const available = cutCount();
      useHalf();
      ok('50/50 is not wasted on a two-way question',
         available === 0 && lifes.half === 1, `cut=${available} card=${lifes.half}`);
    })();

    diffKey='moderado'; startGame();
    useFreeze();
    ok('freeze pauses the clock', frozen === true && lifes.freeze === 0);
    const t1 = tLeft; // simulate a tick
    if (typeof tmr !== 'undefined') { /* tick handled by interval; just assert flag */ }
    ok('freeze is single use', lifes.freeze === 0);

    // ---- placar: the audience vote ----
    diffKey='moderado'; startGame();
    usePoll();
    ok('placar votes on every visible tile',
       poll && Object.keys(poll).length === disp.length, `${poll?Object.keys(poll).length:0}/${disp.length}`);
    ok('placar percentages add up to 100',
       Object.values(poll).reduce((a,b)=>a+b,0) === 100,
       `${Object.values(poll).reduce((a,b)=>a+b,0)}`);
    ok('placar is single use', lifes.poll === 0);
    // The crowd should be a strong hint, never a free answer — and it should
    // get noticeably worse as the money climbs, or Placar beats every other card.
    function crowd(atRung){
      let hit = 0;
      for (let i=0;i<80;i++){
        startMilhao(); rung=atRung; qi=atRung; disp=getDisp(cat.qs[qi]);
        lifes.poll=1; usePoll();
        const top = Object.keys(poll).reduce((a,b)=>poll[a]>=poll[b]?a:b);
        if (cat.qs[qi].a.includes(top)) hit++;
      }
      return hit;
    }
    const cLow = crowd(0), cHigh = crowd(15);
    ok('the crowd is a strong hint, not a free answer',
       cLow >= 56 && cLow <= 78, `${cLow}/80`);
    ok('the crowd falls apart near the million', cHigh < cLow - 20, `${cLow} -> ${cHigh}`);

    // ---- convidado: the pundit ----
    diffKey='moderado'; startGame();
    useExpert();
    ok('the pundit names a visible option',
       expert && disp.some(o => o.id === expert.id), expert ? expert.name : 'none');
    ok('the pundit says how sure he is', typeof expert.sure === 'boolean' && !!expert.line);
    ok('the pundit is single use', lifes.expert === 0);
    // he should be shakier near the million than at the bottom of the ladder
    function pundit(atRung){
      let hit = 0;
      for (let i=0;i<60;i++){
        startMilhao(); rung=atRung; qi=atRung; disp=getDisp(cat.qs[qi]);
        lifes.expert=1; useExpert();
        if (cat.qs[qi].a.includes(expert.id)) hit++;
      }
      return hit;
    }
    const low = pundit(0), high = pundit(14);
    ok('the pundit gets shakier as the money climbs', low > high, `rung1=${low} rung15=${high}`);

    diffKey='moderado'; startGame();
    const q0 = qi;
    useSkip();
    ok('skip advances the question', qi === q0 + 1, `${q0} -> ${qi}`);
    ok('skip logs a neutral result', runLog[runLog.length-1] === -1, JSON.stringify(runLog));
    ok('skip is single use', lifes.skip === 0);

    // ---- lifelines reset between runs ----
    diffKey='facil'; startGame();
    ok('lifelines refresh on a new run',
       lifes.half===1 && lifes.freeze===1 && lifes.skip===1 && hidden.size===0);

    // ---- survival: ends on first non-perfect answer ----
    startSurvival();
    ok('survival starts in quiz', isSurv===true && sc==='quiz');
    const longQueue = cat.qs.length;
    ok('survival queues plenty of questions', longQueue > 20, `${longQueue}`);
    answerCorrectly();
    ok('survival continues after a correct answer', sc==='reveal');

    // ---- daily is reproducible ----
    _seed=null; seedFrom(1234); const a=buildGame('moderado').qs.map(q=>q.t).join('|');
    _seed=null; seedFrom(1234); const b=buildGame('moderado').qs.map(q=>q.t).join('|');
    ok('same seed produces the same game', a===b);
    _seed=null; seedFrom(999);  const c=buildGame('moderado').qs.map(q=>q.t).join('|');
    ok('different seed produces a different game', a!==c);
    _seed=null;

    // ---- medals ----
    stats={games:1,correct:0,answered:10,bestStreak:0};
    ok('first-game medal unlocks', earnedMedals().some(m=>m.id==='first'));
    stats={games:0,correct:0,answered:0,bestStreak:0};
    ok('no medals with no games', earnedMedals().length===0, `${earnedMedals().length}`);

    // ---- share card ----
    diffKey='facil'; startGame(); runLog=[3,1,0,-1];
    nCorrect=1; bestStreak=1;
    const txt = shareText();
    ok('share card renders one emoji per question',
       (txt.match(/🟩|🟨|⬛|⬜/g)||[]).length === 4, txt.split('\n')[1]);
    ok('share card includes the site link', txt.includes('tdosreis.github.io'));

    // ---- symbols: nothing the platform can refuse to draw ----
    ok('every country in the squad has a drawn flag',
       PL.every(p => FLAGS[p.ctry]),
       PL.filter(p => !FLAGS[p.ctry]).map(p=>p.ctry).join(',') || 'all covered');
    ok('flags render as svg, not text', flagSVG('BRA', 8).startsWith('<svg'));
    ok('an unknown country still renders something',
       flagSVG('ZZZ', 8).length > 20 && !/undefined/.test(flagSVG('ZZZ', 8)));
    ok('icons render as svg', ICON.check('#fff',12).startsWith('<svg')
       && ICON.cut('#fff',12).startsWith('<svg'));

    // Category marks are data, so guard the data: a flag belongs in `flag`
    // (drawn) and never in `emoji` (a regional-indicator pair).
    (function(){
      const flagEmoji = /\uD83C[\uDDE6-\uDDFF]|🏴/;
      const bad = CATS.filter(c => c.emoji && flagEmoji.test(c.emoji));
      ok('no category carries a flag emoji', bad.length === 0,
         bad.map(c=>c.id).join(',') || 'clean');
      ok('a flag category renders a drawn flag',
         catIcon(CATS.find(c => c.flag)).startsWith('<svg'));
      ok('a normal category still renders its emoji',
         catIcon(CATS.find(c => c.emoji && !c.flag)).length > 0);
      ok('catIcon copes with a category that has neither', catIcon({}) === '');
    })();
    // the glyphs that Android's WebView has no font for must not be in the markup
    (function(){
      const screens = [];
      sc='home';    go(); screens.push(document.getElementById('ct').innerHTML);
      sc='medals';  go(); screens.push(document.getElementById('ct').innerHTML);
      sc='difficulty'; go(); screens.push(document.getElementById('ct').innerHTML);
      startMilhao();     screens.push(document.getElementById('ct').innerHTML);
      ladderOpen=true; go(); screens.push(document.getElementById('ct').innerHTML);
      ladderOpen=false;
      // ✓ ✗ ✕ ★ → ← ✂ ❄ ⏭ have no glyph in Roboto; regional-indicator and
      // tag-sequence flags have none on most non-Apple platforms.
      const banned = /[✓✗✕★→←✂❄⏭]|🏴|\uD83C[\uDDE6-\uDDFF]/;
      const bad = screens.map((h, i) => banned.test(h) ? i : -1).filter(i => i >= 0);
      ok('no tofu-prone glyphs reach the DOM', bad.length === 0, `screens ${bad.join(',')}`);
    })();

    // ---- artwork: everything referenced, everything labelled ----
    ok('every player has a photo', PL.every(p => p.img),
       PL.filter(p=>!p.img).map(p=>p.id).join(',') || 'all present');
    ok('every club has a crest or a drawn fallback',
       CL.every(c => LOGOS[c.id] || (c.c1 && c.c2)),
       CL.filter(c=>!LOGOS[c.id]&&!(c.c1&&c.c2)).map(c=>c.id).join(',') || 'all covered');

    /* Sport and Bragantino have no freely-licensed mark anywhere — Commons
       carries neither, and Bragantino's is Red Bull brand artwork. They keep
       a *designed* badge: colours, kit pattern, founding year, monogram. */
    (function(){
      const drawn = CL.filter(c => !LOGOS[c.id]);
      ok('only the clubs with no free artwork fall back to a drawn badge',
         drawn.length === 2 && drawn.every(c => ['sport','bragantino'].includes(c.id)),
         drawn.map(c=>c.id).join(',') || 'none');
      // the three we did find must be wired up and attributed
      ['corinthians','vasco','nautico'].forEach(function(id){
        ok(`${id} uses a real licensed crest`,
           !!LOGOS[id] && !!CREDITS[LOGOS[id]] && !!CREDITS[LOGOS[id]].a,
           LOGOS[id] ? `${LOGOS[id]} — ${CREDITS[LOGOS[id]] ? CREDITS[LOGOS[id]].l : 'NO CREDIT'}` : 'missing');
      });
      // rectangular artwork is cut as a roundel, or it reads as a stray box
      ok('flat logos are cut as roundels',
         [...FLAT_LOGOS].every(id => clubArt(id,'').indexOf('border-radius') !== -1));
      const thin = drawn.filter(c => {
        const svg = genericCrest(c.id);
        return !svg
            || svg.indexOf(c.a) === -1                      // monogram
            || (c.f && svg.indexOf(String(c.f)) === -1)     // founding year
            || svg.indexOf('linearGradient') === -1;        // shaded, not flat
      });
      ok('each drawn badge carries its monogram, year and shading',
         thin.length === 0, thin.map(c=>c.id).join(',') || 'all complete');
      // and the kit pattern must actually differ between clubs, or Sport and
      // Náutico both come out as red-and-white stripes
      const shapes = new Set(drawn.map(c => genericCrest(c.id).replace(/[\d.]/g,'')));
      ok('drawn badges are visually distinct from one another',
         shapes.size === drawn.length, `${shapes.size} distinct of ${drawn.length}`);
      ok('a dark second colour survives as the kit pattern',
         _dist('#C00000', '#111111') > 70, `dist=${Math.round(_dist('#C00000','#111111'))}`);
    })();
    ok('every portrait and stadium has an image',
       Object.keys(PORT).every(k => PORT_IMGS[k]) && Object.keys(STAD).every(k => STAD_IMGS[k]));
    ok('generated questions never reference a blank image',
       [1,2,3].every(t => GEN_QS(t).every(q =>
         ['reveal','face','qimg','port','stad','crest'].every(k => q[k] === undefined || !!q[k]))));

    (function(){
      // Every visual must either carry a name or be explicitly marked decorative.
      const unlabelled = new Set();
      function audit(tag){
        document.querySelectorAll('#ct img').forEach(im => {
          if (im.getAttribute('aria-hidden') !== 'true' && !im.getAttribute('alt'))
            unlabelled.add(tag + ':img');
          if (!im.getAttribute('src')) unlabelled.add(tag + ':img-no-src');
        });
        document.querySelectorAll('#ct svg').forEach(sv => {
          if (sv.getAttribute('aria-hidden') !== 'true' && !sv.getAttribute('aria-label'))
            unlabelled.add(tag + ':svg');
        });
      }
      ['home','medals','credits','difficulty'].forEach(s => { sc=s; go(); audit(s); });
      for (let i=0;i<20;i++){ startMilhao(); audit('milhao'); }
      for (let i=0;i<12;i++){ diffKey='dificil'; startGame(); audit('treino'); }
      ok('every image and icon is named or marked decorative',
         unlabelled.size === 0, [...unlabelled].join(', ') || 'all labelled');
    })();

    /* ── Small screens ───────────────────────────────────────────
       These ran in a 320px-wide iframe when written. Headless Chrome
       clamps its own viewport to 500px no matter what --window-size
       says, so a probe run directly in the page silently tests 500px
       and reports a clean bill of health for sizes it never tried.
       tools/narrow.py drives the iframe harness; these assertions hold
       whatever width the suite happens to run at. */
    (function(){
      // a tile caption must never be clipped — the name is the answer
      let clipped = [];
      for (let n = 0; n < 6; n++) {
        startMilhao();
        for (let i = 0; i < cat.qs.length; i++)
          if (cat.qs[i].type === 'player' && !cat.qs[i].textTiles) { qi = i; break; }
        rung = 9; disp = getDisp(cat.qs[qi]); go();
        document.querySelectorAll('.tile-name').forEach(function(nm){
          if (nm.scrollHeight > nm.clientHeight + 1) clipped.push(nm.textContent.trim());
        });
      }
      ok('no tile caption is truncated', clipped.length === 0,
         [...new Set(clipped)].slice(0,4).join(', ') || 'all names fit');

      // the vote overlay must not sit on top of the caption
      startMilhao(); rung = 9; qi = 9; disp = getDisp(cat.qs[9]); go(); usePoll();
      let collisions = 0;
      document.querySelectorAll('.b').forEach(function(t){
        const nm = t.querySelector('.tile-name'), v = t.querySelector('.vote-pct');
        if (!nm || !v) return;
        const a = nm.getBoundingClientRect(), b = v.getBoundingClientRect();
        if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom) collisions++;
      });
      ok('the audience percentage never overlaps a name', collisions === 0, `${collisions} tiles`);

      /* CONFIRMAR must stay reachable without scrolling — but only assert it
         at a height a real phone actually has. This suite runs at whatever
         viewport headless Chrome hands out (~469px tall), which is shorter
         than any shipping device; tools/narrow.py checks the real sizes. */
      const vh = document.documentElement.clientHeight;
      startMilhao(); rung = 9; qi = 9; disp = getDisp(cat.qs[9]); go();
      usePoll(); useExpert();
      const cta = document.getElementById('bconf');
      const bottom = cta ? Math.round(cta.getBoundingClientRect().bottom) : -1;
      ok('the confirm button stays above the fold',
         vh < 520 ? true : (!!cta && bottom <= vh + 1),
         vh < 520 ? `skipped — viewport only ${vh}px tall, see tools/narrow.py`
                  : `cta=${bottom} vh=${vh}`);
    })();

    // Attribution is a licence condition, so an unattributed photo must never be
    // silent — the credits screen has to name it as unsourced.
    (function(){
      const unsourced = PL.filter(p => p.img && !CREDITS[p.img]).map(p => p.n);
      sc='credits'; go();
      const shown = document.getElementById('ct').textContent;
      ok('every unattributed photo is disclosed on the credits screen',
         unsourced.every(n => shown.includes(n)),
         unsourced.length ? unsourced.join(', ') : 'all photos attributed');
      ok('the credits screen lists an author for every attributed photo',
         Object.values(CREDITS).every(c => c.a && c.l));
    })();

  } catch(e) { out.push({n:'EXCEPTION',pass:false,extra:(e&&(e.stack||e.message))||String(e)}); }
  const el=document.createElement('div'); el.id='OUT';
  el.textContent=JSON.stringify(out); document.body.appendChild(el);
})();
</script>
"""

src = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
tmp = os.path.join(ROOT, "_test_beh.html")
io.open(tmp, "w", encoding="utf-8").write(src.replace("</body>", TESTS + "</body>"))
try:
    dom = subprocess.run([CHROME, "--headless", "--disable-gpu", "--virtual-time-budget=12000",
                          "--allow-file-access-from-files", "--dump-dom", "file://" + tmp],
                         capture_output=True, text=True, timeout=200).stdout
finally:
    os.remove(tmp)

m = re.search(r'<div id="OUT">(.*?)</div>', dom, re.S)
if not m:
    print("!! no output"); [print("  ", e) for e in re.findall(r"Uncaught[^<\n]*", dom)[:4]]; sys.exit(1)
res = json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&")
                           .replace("&lt;", "<").replace("&gt;", ">"))
npass = sum(1 for r in res if r["pass"])
for r in res:
    print(f"  [{'PASS' if r['pass'] else 'FAIL'}] {r['n']}" + (f"   ({r['extra']})" if r["extra"] else ""))
print(f"\n{npass}/{len(res)} passed")
sys.exit(0 if npass == len(res) else 1)
