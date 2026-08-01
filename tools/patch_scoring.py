#!/usr/bin/env python3
"""Streak multipliers, speed bonus, persistent records, richer end screen."""
import re, io, os, sys

P = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
s = io.open(P, encoding="utf-8").read()
if "COMBO SCORING" in s:
    print("already patched"); sys.exit(0)

# ── 1. per-difficulty points multiplier ───────────────────────────────
s = s.replace("time:30, strict:0.00, opts:10, tier:1 },", "time:30, strict:0.00, opts:10, tier:1, pmul:1   },")
s = s.replace("time:25, strict:0.55, opts:10, tier:2 },", "time:25, strict:0.55, opts:10, tier:2, pmul:1.5 },")
s = s.replace("time:20, strict:1.00, opts:10, tier:3 },", "time:20, strict:1.00, opts:10, tier:3, pmul:2   },")

# ── 2. persistent storage + richer run state ──────────────────────────
old_state = "let scores   = {};"
new_state = """/* ═══════════════════════════════════════════════════
   COMBO SCORING + PERSISTENCE
═══════════════════════════════════════════════════ */
const LS = {
  get(k, d) { try { const v = localStorage.getItem('fqbr_' + k);
                    return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem('fqbr_' + k, JSON.stringify(v)); } catch (e) {} },
};
let scores     = LS.get('scores', {});      // best points per difficulty
let stats      = LS.get('stats', { games:0, correct:0, answered:0, bestStreak:0 });
let nCorrect   = 0;   // perfect answers this run
let nPartial   = 0;
let bestStreak = 0;
let lastGain   = 0;
let runLog     = [];  // per-question 3/1/0, for the share card

/* points for one answer, with speed + combo + difficulty multipliers */
function scoreAnswer(base) {
  if (base <= 0) return { gained:0, mult:1, speed:0 };
  const frac  = tMax ? tLeft / tMax : 0;
  const speed = base === 3 ? (frac > 0.6 ? 2 : frac > 0.3 ? 1 : 0) : 0;
  const mult  = streak >= 6 ? 3 : streak >= 3 ? 2 : 1;
  return { gained: Math.round((base + speed) * mult * DCFG().pmul), mult, speed };
}"""
if old_state not in s: print("ERR: state anchor missing"); sys.exit(1)
s = s.replace(old_state, new_state, 1)

# ── 3. new scoring inside doReveal ────────────────────────────────────
old_score = """  prevPts = pts;
  pts    += p;
  p === 3 ? streak++ : (streak = 0);

  if      (p === 3) snd.correct();
  else if (p === 1) snd.almost();
  else              snd.wrong();

  lastMsg = p === 3
    ? `<span style="font-size:15px;font-weight:800;color:#00e676;
        font-family:'Inter',system-ui;">✓ Perfeito! +3 pontos</span>`
    : p === 1
    ? `<span style="font-size:15px;font-weight:800;color:#FFD700;
        font-family:'Inter',system-ui;">~ Quase! +1 ponto</span>`
    : `<span style="font-size:15px;font-weight:800;color:#f44336;
        font-family:'Inter',system-ui;">✗ Errou! +0 pontos</span>`;"""

new_score = """  prevPts = pts;
  if (p === 3) streak++; else streak = 0;
  bestStreak = Math.max(bestStreak, streak);

  const { gained, mult, speed } = scoreAnswer(p);
  pts += gained;
  lastGain = gained;
  if (p === 3) nCorrect++; else if (p === 1) nPartial++;
  runLog.push(p);

  if      (p === 3) snd.correct();
  else if (p === 1) snd.almost();
  else              snd.wrong();

  const chip = (txt, col) => `<span style="display:inline-block;background:${col}22;
      border:1px solid ${col}44;color:${col};border-radius:9px;padding:1px 7px;
      font-size:10px;font-weight:700;margin-left:4px;
      font-family:'Inter',system-ui;">${txt}</span>`;
  const bonuses = (speed ? chip('⚡ rápido +' + speed, '#4FC3F7') : '')
                + (mult > 1 ? chip('🔥 combo ×' + mult, '#FF7700') : '')
                + (DCFG().pmul > 1 ? chip(DCFG().emoji + ' ×' + DCFG().pmul, DCFG().col) : '');

  lastMsg = p === 3
    ? `<span style="font-size:15px;font-weight:800;color:#00e676;
        font-family:'Inter',system-ui;">✓ Perfeito! +${gained}</span>${bonuses}`
    : p === 1
    ? `<span style="font-size:15px;font-weight:800;color:#FFD700;
        font-family:'Inter',system-ui;">~ Quase! +${gained}</span>${bonuses}`
    : `<span style="font-size:15px;font-weight:800;color:#f44336;
        font-family:'Inter',system-ui;">✗ Errou!</span>`;"""
if old_score not in s: print("ERR: scoring block not matched"); sys.exit(1)
s = s.replace(old_score, new_score, 1)

# ── 4. reset run counters on a new game ───────────────────────────────
s = s.replace("qi = 0; sel.clear(); pts = 0; prevPts = 0; streak = 0;",
              "qi = 0; sel.clear(); pts = 0; prevPts = 0; streak = 0;\n"
              "  nCorrect = 0; nPartial = 0; bestStreak = 0; lastGain = 0; runLog = [];")

# ── 5. persist records at the end of a run ────────────────────────────
old_end = """      sc = 'end';
      if (scores[diffKey] === undefined || pts > scores[diffKey]) scores[diffKey] = pts;"""
new_end = """      sc = 'end';
      if (scores[diffKey] === undefined || pts > scores[diffKey]) {
        scores[diffKey] = pts;
        LS.set('scores', scores);
      }
      stats.games    += 1;
      stats.correct  += nCorrect;
      stats.answered += cat.qs.length;
      stats.bestStreak = Math.max(stats.bestStreak || 0, bestStreak);
      LS.set('stats', stats);"""
if old_end not in s: print("ERR: end-persist anchor missing"); sys.exit(1)
s = s.replace(old_end, new_end, 1)

# ── 6. end screen: accuracy-based, with combo + record info ───────────
old_hdr = """    const max = cat.qs.length * 3;
    const pct = Math.round(pts / max * 100);
    const [em, msg] = pct >= 80 ? ['🏆','Craque!'] : pct >= 50 ? ['⚽','Boa jogada!'] : ['😅','Treina mais!'];
    const isRecord = scores[diffKey] !== undefined && pts === scores[diffKey] && pts > 0;"""
new_hdr = """    const total = cat.qs.length;
    const pct = Math.round(nCorrect / total * 100);
    const [em, msg] = pct >= 80 ? ['🏆','Craque!'] : pct >= 50 ? ['⚽','Boa jogada!'] : ['😅','Treina mais!'];
    const isRecord = scores[diffKey] !== undefined && pts === scores[diffKey] && pts > 0;"""
if old_hdr not in s: print("ERR: end header anchor missing"); sys.exit(1)
s = s.replace(old_hdr, new_hdr, 1)

s = s.replace("""      <div style="font-size:13px;color:rgba(255,255,255,.35);font-family:'Inter',system-ui;">
        de ${max} pontos · ${pct}%</div>""",
"""      <div style="font-size:13px;color:rgba(255,255,255,.35);font-family:'Inter',system-ui;">
        pontos · ${nCorrect}/${total} acertos (${pct}%)</div>
      ${bestStreak >= 3 ? `<div style="font-size:12px;color:#FF7700;font-weight:700;
        font-family:'Inter',system-ui;">🔥 melhor sequência: ${bestStreak}</div>` : ''}""", 1)

io.open(P, "w", encoding="utf-8").write(s)
print("scoring patched")
