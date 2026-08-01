#!/usr/bin/env python3
"""Add template-based question generators + richer option control to getDisp."""
import re, io, os, sys

P = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
s = io.open(P, encoding="utf-8").read()
if "QUESTION GENERATORS" in s:
    print("already patched"); sys.exit(0)

# ── 1. teach getDisp about fixed sets / custom pools ──────────────────
old = re.search(r"function getDisp\(q\) \{.*?\n\}\n", s, re.S)
if not old: print("ERR getDisp not found"); sys.exit(1)

NEW_DISP = """function getDisp(q) {
  const isPlayer = q.type === 'player';
  const pool0 = isPlayer ? PL : CL;
  const sim   = isPlayer ? simPlayer : simClub;
  const cfg   = DCFG();
  const strict = (q.strict !== undefined) ? q.strict : cfg.strict;
  const nOpts  = q.opts || cfg.opts;

  // `fixed` = show exactly these tiles (comparison questions)
  if (q.fixed) return shuf(q.fixed.map(id => pool0.find(x => x.id === id)).filter(Boolean));

  const right = q.a.map(id => pool0.find(x => x.id === id)).filter(Boolean);

  // `pool` = explicit list of ids allowed as wrong answers
  let wrong;
  if (q.pool) {
    const allow = new Set(q.pool);
    wrong = pool0.filter(x => allow.has(x.id) && !q.a.includes(x.id));
  } else {
    const skip = new Set([...(q.excl || []), ...q.a]);
    wrong = pool0.filter(x => !skip.has(x.id));
  }

  const ref = right[0];
  if (ref && strict > 0 && wrong.length > nOpts) {
    const jitter = 14 * (1 - strict) + 6;
    wrong = wrong
      .map(x => ({ x, s: sim(x, ref) + Math.random() * jitter }))
      .sort((a, b) => b.s - a.s)
      .map(o => o.x);
    const need = nOpts - right.length;
    const band = Math.max(need + 2, Math.round(wrong.length * (1 - strict * 0.72)));
    wrong = wrong.slice(0, band);
  }

  wrong = shuf(wrong);
  return shuf([...right, ...wrong.slice(0, Math.max(0, nOpts - right.length))]);
}
"""
s = s[:old.start()] + NEW_DISP + s[old.end():]

# ── 2. the generators ─────────────────────────────────────────────────
GEN = r"""
/* ═══════════════════════════════════════════════════
   QUESTION GENERATORS
   Build fresh questions from the structured data so the
   pool never runs dry and distractors are correct by design.
═══════════════════════════════════════════════════ */
function GEN_QS(tier) {
  const out  = [];
  const CIDS = new Set(CL.map(c => c.id));
  const rnd  = a => a[Math.floor(Math.random() * a.length)];
  const pick = (a, n) => shuf(a).slice(0, n);

  /* ── 1. Which Brazilian club did this player turn out for? ── */
  const withBr = PL.filter(p => (p.clubs || []).some(c => CIDS.has(c)));
  pick(withBr, 26).forEach(p => {
    const mine = (p.clubs || []).filter(c => CIDS.has(c));
    out.push({
      t: `Por qual destes clubes ${p.n} jogou?`,
      a: [rnd(mine)],
      pool: CL.filter(c => !(p.clubs || []).includes(c.id)).map(c => c.id),
      face: p.img,
      d: p.ctry === 'BRA' ? 2 : 3,
    });
  });

  /* ── 2. Position recognition ── */
  ['GK', 'DF', 'MF'].forEach(pos => {
    const same   = PL.filter(p => p.pos === pos);
    const others = PL.filter(p => p.pos !== pos);
    if (same.length < 2 || others.length < 9) return;
    pick(same, 4).forEach(p => {
      out.push({
        t: `Qual destes jogadores atuava como ${POS_NAME[pos].toLowerCase()}?`,
        a: [p.id], type: 'player',
        pool: others.map(x => x.id),
        d: pos === 'GK' ? 1 : 2,
      });
    });
  });

  /* ── 3. Nationality ── */
  const byCtry = {};
  PL.forEach(p => { (byCtry[p.ctry] = byCtry[p.ctry] || []).push(p); });
  Object.keys(byCtry).filter(c => c !== 'BRA' && byCtry[c].length >= 1).forEach(c => {
    const p = rnd(byCtry[c]);
    out.push({
      t: `Qual destes jogadores defendeu a seleção de ${CTRY_NAME[c] || c}?`,
      a: [p.id], type: 'player',
      pool: PL.filter(x => x.ctry !== c).map(x => x.id),
      d: 2,
    });
  });

  /* ── 4. Oldest club (comparison, exact 10 tiles) ── */
  for (let i = 0; i < 4; i++) {
    const set = pick(CL, 10);
    const oldest = set.reduce((a, b) => (a.f <= b.f ? a : b));
    if (set.filter(c => c.f === oldest.f).length > 1) continue;   // avoid ties
    out.push({ t: 'Qual destes clubes foi fundado primeiro?',
               a: [oldest.id], fixed: set.map(c => c.id), d: 3 });
  }

  /* ── 5. Most Brasileirão titles ── */
  for (let i = 0; i < 4; i++) {
    const set = pick(CL, 10);
    const top = set.reduce((a, b) => (a.br >= b.br ? a : b));
    if (top.br === 0 || set.filter(c => c.br === top.br).length > 1) continue;
    out.push({ t: 'Qual destes clubes tem mais títulos do Brasileirão?',
               a: [top.id], fixed: set.map(c => c.id), d: 2 });
  }

  /* ── 6. Libertadores winners (multi-select) ── */
  for (let i = 0; i < 3; i++) {
    const champs = pick(CL.filter(c => c.lib > 0), 3);
    const rest   = pick(CL.filter(c => c.lib === 0), 7);
    if (champs.length < 3 || rest.length < 7) break;
    out.push({ t: 'Selecione os clubes que JÁ venceram a Libertadores',
               a: champs.map(c => c.id),
               fixed: champs.concat(rest).map(c => c.id), d: 2 });
  }

  /* ── 7. Team-mates: who also played for this club? ── */
  const clubPlayers = {};
  PL.forEach(p => (p.clubs || []).forEach(c => {
    if (CIDS.has(c)) (clubPlayers[c] = clubPlayers[c] || []).push(p);
  }));
  pick(Object.keys(clubPlayers).filter(c => clubPlayers[c].length >= 2), 6).forEach(c => {
    const yes = pick(clubPlayers[c], 2);
    const no  = PL.filter(p => !(p.clubs || []).includes(c));
    out.push({
      t: `Selecione os 2 jogadores que passaram pelo ${clubName(c)}`,
      a: yes.map(p => p.id), type: 'player',
      pool: no.map(p => p.id),
      crest: c,
      d: 3,
    });
  });

  /* ── 8. Era placement ── */
  pick(PL.filter(p => p.era && p.era[0] >= 1990), 6).forEach(p => {
    const dec = Math.floor(p.era[0] / 10) * 10;
    const others = PL.filter(x => x.era && Math.floor(x.era[0] / 10) * 10 !== dec);
    if (others.length < 9) return;
    out.push({
      t: `Qual destes jogadores começou a carreira nos anos ${dec}?`,
      a: [p.id], type: 'player',
      pool: others.map(x => x.id),
      d: 3,
    });
  });

  return out;
}
"""
anchor = "/* ═══════════════════════════════════════════════════\n   GAME STATE"
if anchor not in s:
    print("ERR: anchor not found"); sys.exit(1)
s = s.replace(anchor, GEN + "\n" + anchor, 1)

# ── 3. render support: circular player face + club crest in question card ──
old_q = """  const qimgEl = q.qimg"""
new_q = """  const faceEl = q.face
    ? `<div style="flex-shrink:0;width:56px;height:56px;border-radius:50%;overflow:hidden;
        border:2px solid rgba(255,255,255,.2);box-shadow:0 2px 12px rgba(0,0,0,.55);">
        <img src="${q.face}" alt=""
          style="width:100%;height:100%;object-fit:cover;object-position:top center;"
          onerror="this.parentElement.style.display='none'" /></div>` : '';
  const crestEl = q.crest
    ? `<div style="flex-shrink:0;width:52px;height:52px;display:flex;align-items:center;justify-content:center;">
        <img src="${LOGOS[q.crest]}" alt=""
          style="max-width:100%;max-height:100%;object-fit:contain;"
          onerror="this.parentElement.style.display='none'" /></div>` : '';
  const qimgEl = q.qimg"""
if old_q in s:
    s = s.replace(old_q, new_q, 1)
    s = s.replace("${portSVG}${stadSVG}${qimgEl}", "${portSVG}${stadSVG}${faceEl}${crestEl}${qimgEl}", 1)
else:
    print("WARN: could not add face/crest rendering")

io.open(P, "w", encoding="utf-8").write(s)
print("generators patched")
