#!/usr/bin/env python3
"""Game-show lifelines: 50/50, freeze the clock, skip. Limited uses per run."""
import re, io, os, sys

P = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
s = io.open(P, encoding="utf-8").read()
if "LIFELINES" in s:
    print("already patched"); sys.exit(0)

STATE = """
/* ═══════════════════════════════════════════════════
   LIFELINES
   Three single-use helpers per run. They cost nothing but
   the speed bonus, so using one is a real trade-off.
═══════════════════════════════════════════════════ */
let lifes  = { half: 1, freeze: 1, skip: 1 };
let hidden = new Set();   // tiles removed by 50/50
let frozen = false;       // clock paused for this question

function resetLifes() {
  lifes  = { half: 1, freeze: 1, skip: 1 };
  hidden = new Set();
  frozen = false;
}

function useHalf() {
  if (!lifes.half || sc !== 'quiz') return;
  const q = cat.qs[qi];
  const wrong = disp.filter(o => !q.a.includes(o.id)).map(o => o.id);
  // remove half of the wrong options, keeping the board readable
  const drop = shuf(wrong).slice(0, Math.floor(wrong.length / 2));
  drop.forEach(id => { hidden.add(id); sel.delete(id); });
  lifes.half = 0;
  snd.select();
  go();
}

function useFreeze() {
  if (!lifes.freeze || sc !== 'quiz') return;
  lifes.freeze = 0;
  frozen = true;
  snd.select();
  go();
}

function useSkip() {
  if (!lifes.skip || sc !== 'quiz') return;
  lifes.skip = 0;
  clearInterval(tmr);
  snd.swipe();
  runLog.push(-1);                 // neither right nor wrong
  qi++;
  sel.clear(); hidden = new Set(); frozen = false; lastMsg = '';
  if (qi >= cat.qs.length) { finishRun(); }
  else {
    sc = 'quiz'; tMax = DCFG().time; tLeft = tMax;
    disp = getDisp(cat.qs[qi]);
    startTmr();
  }
  go();
}
"""
anchor = "/* ═══════════════════════════════════════════════════\n   HELPERS"
if anchor not in s: print("ERR helpers anchor"); sys.exit(1)
s = s.replace(anchor, STATE + "\n" + anchor, 1)

# ── the clock respects "frozen" ──────────────────────────────────────
s = s.replace("""  tmr = setInterval(() => {
    tLeft = Math.max(0, tLeft - 1);""",
              """  tmr = setInterval(() => {
    if (frozen) return;
    tLeft = Math.max(0, tLeft - 1);""", 1)

# ── reset per run and per question ───────────────────────────────────
s = s.replace("  nCorrect = 0; nPartial = 0; bestStreak = 0; lastGain = 0; runLog = [];",
              "  nCorrect = 0; nPartial = 0; bestStreak = 0; lastGain = 0; runLog = [];\n  resetLifes();", 1)
s = s.replace("""    qi++;
    sel.clear();
    lastMsg = '';""",
              """    qi++;
    sel.clear();
    hidden = new Set();
    frozen = false;
    lastMsg = '';""", 1)

# ── hidden tiles are dimmed out of play ──────────────────────────────
s = s.replace("""  const curQ    = (cat && cat.qs && cat.qs[qi]) || {};
  const delay   = `animation-delay:${Math.min(9, idx || 0) * 32}ms;`;""",
              """  const curQ    = (cat && cat.qs && cat.qs[qi]) || {};
  const delay   = `animation-delay:${Math.min(9, idx || 0) * 32}ms;`;
  if (hidden.has(item.id) && sc === 'quiz') {
    return `<div style="${delay}width:100%;${curQ.textTiles ? 'min-height:44px' : 'aspect-ratio:1'};
      border-radius:9px;background:rgba(255,255,255,.02);opacity:.25;
      border:1px dashed rgba(255,255,255,.08);"></div>`;
  }""", 1)

# ── lifeline bar above the confirm button ────────────────────────────
old_footer = """    <div style="display:flex;flex-direction:column;align-items:center;gap:5px;padding-top:2px;">
      <p style="font-size:10px;color:rgba(255,255,255,.24);margin:0;"""
new_footer = """    <div style="display:flex;flex-direction:column;align-items:center;gap:5px;padding-top:2px;">
      <div style="display:flex;gap:7px;margin-bottom:1px;">
        ${[['bhalf','50:50','✂️',lifes.half],
           ['bfreeze','Congelar','❄️',lifes.freeze],
           ['bskip','Pular','⏭️',lifes.skip]].map(([id,lbl,ic,on]) => `
          <button id="${id}" ${on ? '' : 'disabled'} class="btn-press" style="
            background:${on ? 'rgba(255,255,255,.07)' : 'rgba(255,255,255,.02)'};
            border:1px solid ${on ? 'rgba(255,215,0,.3)' : 'rgba(255,255,255,.05)'};
            color:${on ? 'rgba(255,255,255,.82)' : 'rgba(255,255,255,.18)'};
            border-radius:14px;padding:4px 10px;font-size:10px;font-weight:700;
            cursor:${on ? 'pointer' : 'default'};font-family:'Inter',system-ui;
            display:flex;align-items:center;gap:4px;">
            <span style="font-size:11px;">${ic}</span>${lbl}</button>`).join('')}
      </div>
      ${frozen ? `<div style="font-size:10px;color:#4FC3F7;font-weight:700;
        font-family:'Inter',system-ui;">❄️ Tempo congelado nesta pergunta</div>` : ''}
      <p style="font-size:10px;color:rgba(255,255,255,.24);margin:0;"""
if old_footer not in s: print("ERR footer anchor"); sys.exit(1)
s = s.replace(old_footer, new_footer, 1)

# ── wire the buttons ─────────────────────────────────────────────────
s = s.replace("""  document.getElementById('bconf')?.addEventListener('click', () => { if (sel.size > 0) doReveal(); });""",
"""  document.getElementById('bconf')?.addEventListener('click', () => { if (sel.size > 0) doReveal(); });
  document.getElementById('bhalf')?.addEventListener('click',   () => useHalf());
  document.getElementById('bfreeze')?.addEventListener('click', () => useFreeze());
  document.getElementById('bskip')?.addEventListener('click',   () => useSkip());""", 1)

# ── extract the end-of-run bookkeeping so skip can reuse it ──────────
old_finish = """      sc = 'end';
      if (scores[diffKey] === undefined || pts > scores[diffKey]) {
        scores[diffKey] = pts;
        LS.set('scores', scores);
      }
      if (isDaily) saveDaily();
      stats.games    += 1;
      stats.correct  += nCorrect;
      stats.answered += cat.qs.length;
      stats.bestStreak = Math.max(stats.bestStreak || 0, bestStreak);
      LS.set('stats', stats);"""
new_finish = """      finishRun();"""
if old_finish not in s: print("ERR finish anchor"); sys.exit(1)
s = s.replace(old_finish, new_finish, 1)

FINISH = """
function finishRun() {
  clearInterval(tmr);
  sc = 'end';
  if (scores[diffKey] === undefined || pts > scores[diffKey]) {
    scores[diffKey] = pts;
    LS.set('scores', scores);
  }
  if (isDaily) saveDaily();
  stats.games    += 1;
  stats.correct  += nCorrect;
  stats.answered += cat.qs.length;
  stats.bestStreak = Math.max(stats.bestStreak || 0, bestStreak);
  LS.set('stats', stats);
}
"""
s = s.replace("function startTmr() {", FINISH + "\nfunction startTmr() {", 1)

# skipped questions shouldn't count as a miss on the emoji card
s = s.replace("${runLog.map(p => p === 3 ? '🟩' : p === 1 ? '🟨' : '⬛').join('')}",
              "${runLog.map(p => p === 3 ? '🟩' : p === 1 ? '🟨' : p === -1 ? '⬜' : '⬛').join('')}", 1)
s = s.replace("const grid = runLog.map(p => p === 3 ? '🟩' : p === 1 ? '🟨' : '⬛').join('');",
              "const grid = runLog.map(p => p === 3 ? '🟩' : p === 1 ? '🟨' : p === -1 ? '⬜' : '⬛').join('');", 1)

io.open(P, "w", encoding="utf-8").write(s)
print("lifelines patched")
