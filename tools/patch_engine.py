#!/usr/bin/env python3
"""Replace the random-distractor engine with a difficulty-aware similarity engine."""
import re, io, os, sys

P = os.path.join(os.path.dirname(__file__), "..", "index.html")
s = io.open(P, encoding="utf-8").read()

if "SMART DISTRACTOR ENGINE" in s:
    print("already patched"); sys.exit(0)

# ── 1. difficulty config ────────────────────────────────────────────────
old_diffs = re.search(r"const DIFFS = \[.*?\n\];", s, re.S)
if not old_diffs: print("ERR: DIFFS not found"); sys.exit(1)

NEW_DIFFS = """const DIFFS = [
  { key:'facil',    label:'Fácil',    emoji:'😊', n:10, col:'#43A047',
    desc:'Alternativas variadas · 30s',
    time:30, strict:0.00, opts:10, tier:1 },
  { key:'moderado', label:'Moderado', emoji:'⚽', n:15, col:'#FF9800',
    desc:'Alternativas parecidas · 25s',
    time:25, strict:0.55, opts:10, tier:2 },
  { key:'dificil',  label:'Difícil',  emoji:'🔥', n:20, col:'#E53935',
    desc:'Mesma posição e era · 20s',
    time:20, strict:1.00, opts:10, tier:3 },
];
const DCFG = () => DIFFS.find(d => d.key === diffKey) || DIFFS[0];

/* ═══════════════════════════════════════════════════
   SMART DISTRACTOR ENGINE
   Wrong answers are scored for plausibility instead of
   being drawn at random, so harder levels really are harder.
═══════════════════════════════════════════════════ */
function shuf(a) {
  a = a.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function eraOverlap(a, b) {
  if (!a.era || !b.era) return 0;
  return Math.max(0, Math.min(a.era[1], b.era[1]) - Math.max(a.era[0], b.era[0]));
}

/* How confusable is `cand` with the correct player `ref`? 0-100 */
function simPlayer(cand, ref) {
  let sc = 0;
  if (cand.pos  === ref.pos)  sc += 38;           // same position
  if (cand.ctry === ref.ctry) sc += 22;           // same country
  sc += Math.min(26, eraOverlap(cand, ref) * 1.8); // contemporaries
  const shared = (cand.clubs || []).filter(c => (ref.clubs || []).includes(c)).length;
  sc += Math.min(14, shared * 7);                 // shared clubs
  return sc;
}

/* Confusability between clubs */
function simClub(cand, ref) {
  let sc = 0;
  if (cand.s === ref.s) sc += 42;                              // same state
  sc += Math.max(0, 22 - Math.abs((cand.f||1900) - (ref.f||1900)) / 2);
  if ((cand.lib > 0) === (ref.lib > 0)) sc += 20;              // both/neither Libertadores
  if ((cand.br  > 0) === (ref.br  > 0)) sc += 16;              // both/neither Brasileirão
  return sc;
}

function getDisp(q) {
  const isPlayer = q.type === 'player';
  const pool = isPlayer ? PL : CL;
  const sim  = isPlayer ? simPlayer : simClub;
  const cfg  = DCFG();
  const strict = (q.strict !== undefined) ? q.strict : cfg.strict;
  const nOpts  = q.opts || cfg.opts;

  const right = q.a.map(id => pool.find(x => x.id === id)).filter(Boolean);
  let wrong = pool.filter(x => !q.a.includes(x.id));

  const ref = right[0];
  if (ref && strict > 0 && wrong.length > nOpts) {
    // rank by plausibility (with jitter so repeats still feel fresh)
    const jitter = 14 * (1 - strict) + 6;
    wrong = wrong
      .map(x => ({ x, s: sim(x, ref) + Math.random() * jitter }))
      .sort((a, b) => b.s - a.s)
      .map(o => o.x);
    // keep only the most confusable band; tighter as strictness rises
    const need = nOpts - right.length;
    const band = Math.max(need + 2, Math.round(wrong.length * (1 - strict * 0.72)));
    wrong = wrong.slice(0, band);
  }

  wrong = shuf(wrong);
  return shuf([...right, ...wrong.slice(0, Math.max(0, nOpts - right.length))]);
}

/* ═══════════════════════════════════════════════════
   QUESTION DIFFICULTY RATING
═══════════════════════════════════════════════════ */
const FAMOUS = new Set(['pele','messi','cr7','ronaldo','ronaldinho','neymar',
  'maradona','zidane','romario','garrincha','zico','kaka','mbappe','vinicius','gabigol']);

function qTier(q) {
  if (q.d) return q.d;                       // explicit override
  const cid = (q._cat && q._cat.id) || '';
  if (cid === 'estados')  return 1;
  if (cid === 'estadios') return 2;
  if (cid === 'lendas')   return 2;
  if (cid === 'libertadores' || cid === 'brasileirao') {
    const m = /\\b(19|20)\\d{2}\\b/.exec(q.t);
    const y = m ? parseInt(m[0], 10) : 2000;
    return y >= 2015 ? 1 : y >= 2005 ? 2 : 3;
  }
  if (cid === 'craques') {
    return q.a.some(id => FAMOUS.has(id)) ? 2 : 3;
  }
  return 2;
}"""
s = s[:old_diffs.start()] + NEW_DIFFS + s[old_diffs.end():]

# ── 2. game builder: pick questions matching the chosen tier ────────────
old_build = re.search(r"function buildMixedGame\(n\) \{.*?\n\}", s, re.S)
if not old_build: print("ERR: buildMixedGame not found"); sys.exit(1)

NEW_BUILD = """function buildGame(key) {
  const cfg = DIFFS.find(d => d.key === key) || DIFFS[0];
  let all = CATS.flatMap(c => c.qs.map(q => ({ ...q, _cat: c })));
  if (typeof GEN_QS === 'function') all = all.concat(GEN_QS(cfg.tier));
  all.forEach(q => { q._d = qTier(q); });

  // prefer questions at the requested tier, then nearest tiers
  const scored = shuf(all).map(q => ({ q, w: -Math.abs(q._d - cfg.tier) * 10 + Math.random() * 4 }));
  scored.sort((a, b) => b.w - a.w);
  const qs = scored.slice(0, Math.min(cfg.n, scored.length)).map(o => o.q);

  return {
    id: 'mixed', name: 'Futebol Quiz BR', emoji: '⚽',
    tag: 'Perguntas misturadas', col: '#FFD700', diff: cfg.label,
    qs: shuf(qs),
  };
}"""
s = s[:old_build.start()] + NEW_BUILD + s[old_build.end():]

# ── 3. remove the now-duplicated old getDisp ───────────────────────────
old_disp = re.search(r"/\* ═+\n   HELPERS\n═+ \*/\nfunction getDisp\(q\) \{.*?\n\}\n", s, re.S)
if old_disp:
    s = s[:old_disp.start()] + "/* ═══════════════════════════════════════════════════\n   HELPERS\n═══════════════════════════════════════════════════ */\n" + s[old_disp.end():]
else:
    print("WARN: old getDisp block not matched")

# ── 4. dynamic timer instead of hard-coded 30s ─────────────────────────
s = s.replace("let tLeft    = 30;", "let tLeft    = 30;\nlet tMax     = 30;")
s = s.replace("const tpct = (tLeft / 30) * 100;", "const tpct = (tLeft / tMax) * 100;")
s = s.replace("tf.style.width      = (tLeft / 30 * 100) + '%';",
              "tf.style.width      = (tLeft / tMax * 100) + '%';")
# startGame + next-question both reset the clock
s = s.replace("sc = 'quiz'; tLeft = 30; lastMsg = '';",
              "sc = 'quiz'; tMax = DCFG().time; tLeft = tMax; lastMsg = '';")
s = s.replace("      sc    = 'quiz';\n      tLeft = 30;",
              "      sc    = 'quiz';\n      tMax  = DCFG().time;\n      tLeft = tMax;")

# ── 5. startGame uses the new builder ──────────────────────────────────
s = s.replace("cat = buildMixedGame(numQs);", "cat = buildGame(diffKey);")

# ── 6. difficulty picker: store key, not just count ────────────────────
s = s.replace("""    numQs   = parseInt(d.dataset.n);
    diffKey = d.dataset.key;""",
              """    diffKey = d.dataset.key;
    numQs   = parseInt(d.dataset.n);""")

io.open(P, "w", encoding="utf-8").write(s)
print("engine patched")
