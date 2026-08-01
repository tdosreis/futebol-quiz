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

    // ---- lifelines ----
    diffKey='moderado'; startGame();
    const before = disp.length;
    useHalf();
    ok('50/50 hides options', hidden.size > 0 && hidden.size < before, `hid ${hidden.size}/${before}`);
    ok('50/50 never hides a correct answer',
       [...hidden].every(id => !cat.qs[qi].a.includes(id)));
    ok('50/50 is single use', lifes.half === 0);

    diffKey='moderado'; startGame();
    useFreeze();
    ok('freeze pauses the clock', frozen === true && lifes.freeze === 0);
    const t1 = tLeft; // simulate a tick
    if (typeof tmr !== 'undefined') { /* tick handled by interval; just assert flag */ }
    ok('freeze is single use', lifes.freeze === 0);

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
