#!/usr/bin/env python3
"""Medals (achievements) with persistence, plus a Survival mode."""
import re, io, os, sys

P = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
s = io.open(P, encoding="utf-8").read()
if "MEDALS" in s:
    print("already patched"); sys.exit(0)

BLOCK = r"""
/* ═══════════════════════════════════════════════════
   MEDALS — long-run progression
═══════════════════════════════════════════════════ */
const MEDALS = [
  { id:'first',  ic:'⚽', n:'Estreia',        d:'Jogue sua primeira partida',
    t: st => st.games >= 1 },
  { id:'ten',    ic:'🎽', n:'Rodada',         d:'Jogue 10 partidas',
    t: st => st.games >= 10 },
  { id:'perfect',ic:'🎯', n:'Perfeição',      d:'Acerte 100% de uma partida',
    t: st => (st.perfect || 0) >= 1 },
  { id:'streak5',ic:'🔥', n:'Pegando fogo',   d:'Sequência de 5 acertos',
    t: st => (st.bestStreak || 0) >= 5 },
  { id:'streak10',ic:'☄️', n:'Imparável',     d:'Sequência de 10 acertos',
    t: st => (st.bestStreak || 0) >= 10 },
  { id:'hard',   ic:'💀', n:'Cara de pau',    d:'80% ou mais no Difícil',
    t: st => (st.hard80 || 0) >= 1 },
  { id:'c100',   ic:'💯', n:'Centenário',     d:'100 acertos no total',
    t: st => (st.correct || 0) >= 100 },
  { id:'c500',   ic:'🧠', n:'Enciclopédia',   d:'500 acertos no total',
    t: st => (st.correct || 0) >= 500 },
  { id:'daily3', ic:'📅', n:'Rotina',         d:'3 desafios diários seguidos',
    t: st => LS.get('dailyStreak', 0) >= 3 },
  { id:'daily7', ic:'🗓️', n:'Semana cheia',   d:'7 desafios diários seguidos',
    t: st => LS.get('dailyStreak', 0) >= 7 },
  { id:'surv10', ic:'🛡️', n:'Sobrevivente',   d:'10 acertos seguidos no Mata-mata',
    t: st => (st.survBest || 0) >= 10 },
];

function earnedMedals() { return MEDALS.filter(m => { try { return m.t(stats); } catch (e) { return false; } }); }

/* returns medals unlocked by the run that just finished */
function newMedals() {
  const had = new Set(LS.get('medals', []));
  const now = earnedMedals().map(m => m.id);
  LS.set('medals', now);
  return MEDALS.filter(m => now.includes(m.id) && !had.has(m.id));
}

/* ═══════════════════════════════════════════════════
   SURVIVAL — one mistake and the run is over
═══════════════════════════════════════════════════ */
let isSurv = false;

function startSurvival() {
  isSurv = true; isDaily = false; _seed = null;
  diffKey = 'moderado';
  cat = buildGame('moderado');
  cat.name = 'Mata-mata';
  // a long queue; the run ends on the first mistake, not on length
  const extra = buildGame('dificil');
  cat.qs = cat.qs.concat(extra.qs);
  qi = 0; sel.clear(); pts = 0; prevPts = 0; streak = 0;
  nCorrect = 0; nPartial = 0; bestStreak = 0; lastGain = 0; runLog = [];
  resetLifes();
  sc = 'quiz'; tMax = DCFG().time; tLeft = tMax; lastMsg = '';
  disp = getDisp(cat.qs[0]);
  startTmr();
  go();
}
"""
anchor = "/* ═══════════════════════════════════════════════════\n   HELPERS"
if anchor not in s: print("ERR helpers anchor"); sys.exit(1)
s = s.replace(anchor, BLOCK + "\n" + anchor, 1)

# ── track the stats the medals depend on ─────────────────────────────
s = s.replace("""  stats.bestStreak = Math.max(stats.bestStreak || 0, bestStreak);
  LS.set('stats', stats);""",
"""  stats.bestStreak = Math.max(stats.bestStreak || 0, bestStreak);
  const acc = nCorrect / Math.max(1, cat.qs.length);
  if (isSurv) {
    stats.survBest = Math.max(stats.survBest || 0, nCorrect);
  } else {
    if (acc === 1) stats.perfect = (stats.perfect || 0) + 1;
    if (diffKey === 'dificil' && acc >= 0.8) stats.hard80 = (stats.hard80 || 0) + 1;
  }
  LS.set('stats', stats);
  window._newMedals = newMedals();""", 1)

# ── survival: a wrong answer ends the run ────────────────────────────
s = s.replace("""  setTimeout(() => {
    qi++;
    sel.clear();""",
"""  setTimeout(() => {
    if (isSurv && p !== 3) {          // survival: anything short of perfect ends it
      cat.qs = cat.qs.slice(0, qi + 1);
      finishRun();
      go();
      return;
    }
    qi++;
    sel.clear();""", 1)

# survival never runs out of questions before a mistake
s = s.replace("""    if (qi >= cat.qs.length) {
      finishRun();""",
"""    if (isSurv && qi >= cat.qs.length - 2) {
      const more = buildGame(rnd() > .5 ? 'moderado' : 'dificil');
      cat.qs = cat.qs.concat(more.qs);
    }
    if (qi >= cat.qs.length) {
      finishRun();""", 1)

s = s.replace("function startGame() {\n  isDaily = false; _seed = null;",
              "function startGame() {\n  isDaily = false; isSurv = false; _seed = null;", 1)
s = s.replace("function startDaily() {\n  isDaily = true;",
              "function startDaily() {\n  isDaily = true; isSurv = false;", 1)

# ── home: survival button + medal strip ──────────────────────────────
s = s.replace("""    <button id="bcred" style="background:none;border:none;""",
"""    <button id="surv-btn" class="btn-press" style="background:rgba(229,57,53,.12);
      border:1px solid rgba(229,57,53,.45);color:#FF6B68;
      font-size:13px;font-weight:700;padding:9px 22px;border-radius:22px;
      cursor:pointer;font-family:'Inter',system-ui;display:flex;align-items:center;gap:7px;">
      <span style="font-size:15px;">🛡️</span><span>Mata-mata</span>
      ${(stats.survBest || 0) > 0 ? `<span style="background:rgba(229,57,53,.2);
        border-radius:8px;padding:1px 6px;font-size:11px;">${stats.survBest}</span>` : ''}
    </button>
    ${(() => {
      const e = earnedMedals();
      if (!e.length) return '';
      return `<div id="medal-strip" style="display:flex;gap:5px;flex-wrap:wrap;
        justify-content:center;max-width:280px;cursor:pointer;">
        ${e.slice(0, 11).map(m => `<span title="${m.n}" style="font-size:16px;
          filter:drop-shadow(0 2px 5px rgba(0,0,0,.6));">${m.ic}</span>`).join('')}
        ${e.length > 11 ? `<span style="font-size:11px;color:rgba(255,255,255,.35);
          align-self:center;">+${e.length - 11}</span>` : ''}
      </div>`;
    })()}
    <button id="bcred" style="background:none;border:none;""", 1)

# ── medals screen ────────────────────────────────────────────────────
SCREEN = """
  /* ── MEDALS SCREEN ── */
  if (sc === 'medals') {
    const got = new Set(earnedMedals().map(m => m.id));
    return `
    <div style="display:flex;flex-direction:column;min-height:500px;padding:16px;gap:10px;">
      <div style="display:flex;align-items:center;gap:8px;">
        <button id="bhome" style="background:rgba(255,255,255,.07);border:none;
          color:rgba(255,255,255,.45);font-size:11px;padding:5px 11px;
          border-radius:12px;cursor:pointer;font-family:'Inter',system-ui;">← Início</button>
        <span style="font-size:13px;font-weight:700;color:rgba(255,255,255,.55);
          font-family:'Inter',system-ui;">Medalhas · ${got.size}/${MEDALS.length}</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:7px;flex:1;overflow-y:auto;">
        ${MEDALS.map(m => {
          const on = got.has(m.id);
          return `<div style="display:flex;align-items:center;gap:11px;
            background:${on ? 'rgba(255,215,0,.07)' : 'rgba(255,255,255,.025)'};
            border:1px solid ${on ? 'rgba(255,215,0,.28)' : 'rgba(255,255,255,.05)'};
            border-radius:11px;padding:9px 12px;">
            <span style="font-size:22px;filter:${on ? 'none' : 'grayscale(1)'};
              opacity:${on ? 1 : .3};">${m.ic}</span>
            <div style="flex:1;">
              <div style="font-size:13px;font-weight:800;
                color:${on ? '#FFD700' : 'rgba(255,255,255,.45)'};
                font-family:'Inter',system-ui;">${m.n}</div>
              <div style="font-size:10px;color:rgba(255,255,255,.35);
                font-family:'Inter',system-ui;">${m.d}</div>
            </div>
            ${on ? '<span style="font-size:13px;color:#00e676;">✓</span>' : ''}
          </div>`;
        }).join('')}
      </div>
    </div>`;
  }

"""
anch2 = "  /* ── CREDITS SCREEN ── */"
if anch2 not in s: print("ERR credits screen anchor"); sys.exit(1)
s = s.replace(anch2, SCREEN + anch2, 1)

# ── wire buttons ─────────────────────────────────────────────────────
s = s.replace("""  document.getElementById('bcred')?.addEventListener('click', () => { snd.swipe(); sc='credits'; go(); });""",
"""  document.getElementById('bcred')?.addEventListener('click', () => { snd.swipe(); sc='credits'; go(); });
  document.getElementById('surv-btn')?.addEventListener('click', () => { snd.select(); startSurvival(); });
  document.getElementById('medal-strip')?.addEventListener('click', () => { snd.swipe(); sc='medals'; go(); });""", 1)

# ── end screen: newly unlocked medals ────────────────────────────────
s = s.replace("""      <div style="display:flex;gap:3px;margin-top:8px;font-size:15px;letter-spacing:1px;">""",
"""      ${(window._newMedals || []).length ? `<div style="display:flex;flex-direction:column;
        gap:4px;margin-top:8px;align-items:center;">
        ${window._newMedals.map(m => `<div style="display:flex;align-items:center;gap:7px;
          background:rgba(255,215,0,.12);border:1px solid rgba(255,215,0,.4);
          border-radius:20px;padding:4px 13px;">
          <span style="font-size:16px;">${m.ic}</span>
          <span style="font-size:11px;font-weight:800;color:#FFD700;
            font-family:'Inter',system-ui;">Nova medalha: ${m.n}</span>
        </div>`).join('')}
      </div>` : ''}
      <div style="display:flex;gap:3px;margin-top:8px;font-size:15px;letter-spacing:1px;">""", 1)

# survival end screen wording
s = s.replace("""        ${curDiff.emoji} ${curDiff.label.toUpperCase()} · ${cat.qs.length} perguntas</div>""",
"""        ${isSurv ? `🛡️ MATA-MATA · ${nCorrect} ${nCorrect === 1 ? 'acerto' : 'acertos'} seguidos`
                 : `${curDiff.emoji} ${curDiff.label.toUpperCase()} · ${cat.qs.length} perguntas`}</div>""", 1)

io.open(P, "w", encoding="utf-8").write(s)
print("medals + survival patched")
