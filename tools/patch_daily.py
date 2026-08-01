#!/usr/bin/env python3
"""Seeded RNG + Daily Challenge + Wordle-style share card."""
import re, io, os, sys

P = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
s = io.open(P, encoding="utf-8").read()
if "DAILY CHALLENGE" in s:
    print("already patched"); sys.exit(0)

# ── 1. seedable RNG so a given day is identical for everyone ──────────
old_shuf = """function shuf(a) {
  a = a.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}"""
new_shuf = """/* Seedable PRNG — when _seed is set the sequence is reproducible, which is
   what makes the Daily Challenge identical for every player. */
let _seed = null;
function rnd() {
  if (_seed === null) return Math.random();
  _seed = (_seed + 0x6D2B79F5) | 0;
  let t = Math.imul(_seed ^ (_seed >>> 15), 1 | _seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function seedFrom(n) { _seed = (n * 2654435761) | 0; }

function shuf(a) {
  a = a.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/* days since 2024-01-01 — the daily puzzle number */
function dayIndex(d) {
  const n = d || new Date();
  return Math.floor((Date.UTC(n.getFullYear(), n.getMonth(), n.getDate())
                     - Date.UTC(2024, 0, 1)) / 86400000);
}"""
if old_shuf not in s: print("ERR shuf anchor"); sys.exit(1)
s = s.replace(old_shuf, new_shuf, 1)

# all game randomness must go through rnd() for the daily to be reproducible
s = s.replace("Math.random() * jitter", "rnd() * jitter")
s = s.replace("Math.random() * 4", "rnd() * 4")
s = s.replace("const rnd  = a => a[Math.floor(Math.random() * a.length)];",
              "const rndOf = a => a[Math.floor(rnd() * a.length)];")
# inside GEN_QS the local helper was named rnd -> rename uses
gen = re.search(r"function GEN_QS\(tier\) \{.*?\n\}\n", s, re.S)
if gen:
    body = gen.group(0)
    nb = re.sub(r"\brnd\((\w+)\)", r"rndOf(\1)", body)
    s = s[:gen.start()] + nb + s[gen.end():]

# ── 2. daily state + share card ───────────────────────────────────────
DAILY = r"""
/* ═══════════════════════════════════════════════════
   DAILY CHALLENGE
   One identical 10-question run per day for everybody,
   plus a Wordle-style card that is easy to paste in WhatsApp.
═══════════════════════════════════════════════════ */
let isDaily = false;

function dailyDone() { return LS.get('dailyDay', -1) === dayIndex(); }
function dailyInfo() { return LS.get('dailyRes', null); }

function dailyStreakNow() {
  const last = LS.get('dailyDay', -1);
  const st   = LS.get('dailyStreak', 0);
  const today = dayIndex();
  if (last === today || last === today - 1) return st;
  return 0;                       // streak broken
}

function saveDaily() {
  const today = dayIndex(), last = LS.get('dailyDay', -1);
  let st = LS.get('dailyStreak', 0);
  st = (last === today - 1) ? st + 1 : (last === today ? st : 1);
  LS.set('dailyDay', today);
  LS.set('dailyStreak', st);
  LS.set('dailyRes', { pts, nCorrect, total: cat.qs.length, log: runLog, streak: st });
}

function shareText() {
  const res  = isDaily ? null : null;
  const grid = runLog.map(p => p === 3 ? '🟩' : p === 1 ? '🟨' : '⬛').join('');
  const head = isDaily ? `Futebol Quiz BR ⚽ Desafio #${dayIndex()}`
                       : `Futebol Quiz BR ⚽ ${DCFG().label}`;
  const strk = bestStreak >= 3 ? `  🔥${bestStreak}` : '';
  return `${head}\n${grid}\n${nCorrect}/${cat.qs.length} acertos · ${pts} pts${strk}\n`
       + `https://tdosreis.github.io/futebol-quiz/`;
}

function doShare() {
  const txt = shareText();
  if (navigator.share) {
    navigator.share({ text: txt }).catch(() => {});
  } else if (navigator.clipboard) {
    navigator.clipboard.writeText(txt).then(() => {
      const b = document.getElementById('bshare');
      if (b) { b.textContent = 'COPIADO!'; setTimeout(() => { b.textContent = 'COMPARTILHAR'; }, 1600); }
    }).catch(() => {});
  }
}

function startDaily() {
  isDaily = true;
  diffKey = 'moderado';
  seedFrom(dayIndex());
  cat = buildGame('moderado');
  cat.qs = cat.qs.slice(0, 10);
  cat.name = 'Desafio Diário';
  qi = 0; sel.clear(); pts = 0; prevPts = 0; streak = 0;
  nCorrect = 0; nPartial = 0; bestStreak = 0; lastGain = 0; runLog = [];
  sc = 'quiz'; tMax = DCFG().time; tLeft = tMax; lastMsg = '';
  disp = getDisp(cat.qs[0]);
  startTmr();
  go();
}
"""
anchor = "/* ═══════════════════════════════════════════════════\n   HELPERS"
if anchor not in s: print("ERR helpers anchor"); sys.exit(1)
s = s.replace(anchor, DAILY + "\n" + anchor, 1)

# ── 3. normal games are unseeded; daily runs stay seeded ──────────────
s = s.replace("function startGame() {\n  cat = buildGame(diffKey);",
              "function startGame() {\n  isDaily = false; _seed = null;\n  cat = buildGame(diffKey);")

# ── 4. persist the daily result when a daily run ends ─────────────────
s = s.replace("      stats.games    += 1;",
              "      if (isDaily) saveDaily();\n      stats.games    += 1;")

# ── 5. home screen: daily challenge button ────────────────────────────
old_cta = """    <button id="cta-btn" style="margin-top:6px;background:#FFD700;color:#060e08;
      font-size:18px;font-weight:900;padding:13px 50px;border-radius:28px;
      border:none;cursor:pointer;
      font-family:'Bebas Neue','Impact',sans-serif;
      letter-spacing:3px;">JOGAR AGORA</button>"""
new_cta = """    <button id="cta-btn" style="margin-top:6px;background:#FFD700;color:#060e08;
      font-size:18px;font-weight:900;padding:13px 50px;border-radius:28px;
      border:none;cursor:pointer;
      font-family:'Bebas Neue','Impact',sans-serif;
      letter-spacing:3px;">JOGAR AGORA</button>
    ${(() => {
      const done = dailyDone(), st = dailyStreakNow(), r = dailyInfo();
      return `<button id="daily-btn" style="background:${done ? 'rgba(255,255,255,.06)' : 'rgba(255,215,0,.12)'};
        border:1px solid ${done ? 'rgba(255,255,255,.14)' : 'rgba(255,215,0,.45)'};
        color:${done ? 'rgba(255,255,255,.55)' : '#FFD700'};
        font-size:13px;font-weight:700;padding:9px 22px;border-radius:22px;
        cursor:pointer;font-family:'Inter',system-ui;display:flex;
        align-items:center;gap:7px;">
        <span style="font-size:15px;">📅</span>
        <span>${done ? `Desafio de hoje: ${r ? r.nCorrect + '/' + r.total : 'feito'}`
                     : 'Desafio Diário #' + dayIndex()}</span>
        ${st > 0 ? `<span style="background:rgba(255,119,0,.18);border-radius:8px;
            padding:1px 6px;font-size:11px;color:#FF7700;">🔥${st}</span>` : ''}
      </button>`;
    })()}
    ${stats.games > 0 ? `<div style="font-size:10px;color:rgba(255,255,255,.25);
      font-family:'Inter',system-ui;">${stats.games} ${stats.games === 1 ? 'partida' : 'partidas'}
      · ${Math.round(stats.correct / Math.max(1, stats.answered) * 100)}% de acerto
      ${stats.bestStreak >= 3 ? ' · 🔥 ' + stats.bestStreak : ''}</div>` : ''}"""
if old_cta not in s: print("ERR cta anchor"); sys.exit(1)
s = s.replace(old_cta, new_cta, 1)

# ── 6. wire the daily button + share button ───────────────────────────
s = s.replace("""  document.getElementById('cta-btn')?.addEventListener('click', () => { snd.swipe(); sc='difficulty'; go(); });""",
"""  document.getElementById('cta-btn')?.addEventListener('click', () => { snd.swipe(); sc='difficulty'; go(); });
  document.getElementById('daily-btn')?.addEventListener('click', () => { snd.select(); startDaily(); });
  document.getElementById('bshare')?.addEventListener('click', () => { snd.tap(); doShare(); });""", 1)

# ── 7. share button + emoji grid on the end screen ────────────────────
old_btns = """      <div style="display:flex;gap:10px;margin-top:12px;flex-wrap:wrap;justify-content:center;">
        <button id="brep" """
new_btns = """      <div style="display:flex;gap:3px;margin-top:8px;font-size:15px;letter-spacing:1px;">
        ${runLog.map(p => p === 3 ? '🟩' : p === 1 ? '🟨' : '⬛').join('')}</div>
      <div style="display:flex;gap:10px;margin-top:12px;flex-wrap:wrap;justify-content:center;">
        <button id="bshare" style="background:#25D366;color:#fff;font-size:13px;
          font-weight:900;padding:10px 22px;border-radius:20px;border:none;cursor:pointer;
          font-family:'Bebas Neue','Impact',sans-serif;letter-spacing:2px;">COMPARTILHAR</button>
        <button id="brep" """
if old_btns not in s: print("ERR end-buttons anchor"); sys.exit(1)
s = s.replace(old_btns, new_btns, 1)

io.open(P, "w", encoding="utf-8").write(s)
print("daily challenge + share patched")
