#!/usr/bin/env python3
"""New question mechanics: progressive photo reveal + career path.
Both reuse existing assets, so no new images and no licensing surface."""
import re, io, os, sys

P = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
s = io.open(P, encoding="utf-8").read()
if "PHOTO REVEAL" in s:
    print("already patched"); sys.exit(0)

# ── 1. text-only tiles (so a blurred face can't be matched against thumbnails) ──
old_badge = """function badge(item) {
  const isPlayer = 'img' in item;
  const isSel   = sel.has(item.id);
  const isAns   = sc === 'reveal' && cat.qs[qi].a.includes(item.id);
  const isWrong = sc === 'reveal' && isSel && !isAns;"""
new_badge = """function badge(item) {
  const isPlayer = 'img' in item;
  const isSel   = sel.has(item.id);
  const isAns   = sc === 'reveal' && cat.qs[qi].a.includes(item.id);
  const isWrong = sc === 'reveal' && isSel && !isAns;
  const curQ    = (cat && cat.qs && cat.qs[qi]) || {};"""
if old_badge not in s: print("ERR badge anchor"); sys.exit(1)
s = s.replace(old_badge, new_badge, 1)

old_pl = """  if (isPlayer) {
    return `<div class="${cls}" data-id="${item.id}" style="""
new_pl = """  if (curQ.textTiles) {
    return `<div class="${cls}" data-id="${item.id}" style="
        width:100%;min-height:44px;border-radius:9px;cursor:pointer;
        background:rgba(255,255,255,.06);user-select:none;
        display:flex;align-items:center;justify-content:center;text-align:center;
        padding:6px 4px;transition:transform .12s,box-shadow .12s;${ring}">
      <span style="font-size:10px;font-weight:700;color:rgba(255,255,255,.9);
        font-family:'Inter',system-ui;line-height:1.25;
        text-shadow:0 1px 4px rgba(0,0,0,.9);">${item.n}</span>
    </div>`;
  }

  if (isPlayer) {
    return `<div class="${cls}" data-id="${item.id}" style="""
if old_pl not in s: print("ERR player-tile anchor"); sys.exit(1)
s = s.replace(old_pl, new_pl, 1)

# ── 2. big progressively-unblurring photo on the question screen ──────
old_card = """    <!-- Question card -->"""
new_card = """    <!-- Progressive photo reveal -->
    ${q.reveal ? `
    <div style="display:flex;justify-content:center;padding:2px 0 4px;">
      <div style="width:150px;height:150px;border-radius:14px;overflow:hidden;
        border:2px solid rgba(255,215,0,.28);box-shadow:0 6px 26px rgba(0,0,0,.65);
        position:relative;background:#0b1a0f;">
        <img id="revimg" src="${q.reveal}" alt=""
          style="width:100%;height:100%;object-fit:cover;object-position:top center;
            filter:blur(${sc === 'reveal' ? 0 : (20 * (tLeft / tMax)).toFixed(1)}px);
            transform:scale(1.08);transition:filter .9s linear;" />
      </div>
    </div>` : ''}

    <!-- Question card -->"""
if old_card not in s: print("ERR question-card anchor"); sys.exit(1)
s = s.replace(old_card, new_card, 1)

# keep the blur in sync with the countdown
old_tick = """    if (tLeft <= 0 && sc === 'quiz') doReveal();"""
new_tick = """    const rv = document.getElementById('revimg');
    if (rv && sc === 'quiz') rv.style.filter = 'blur(' + (20 * (tLeft / tMax)).toFixed(1) + 'px)';
    if (tLeft <= 0 && sc === 'quiz') doReveal();"""
if old_tick not in s: print("ERR timer-tick anchor"); sys.exit(1)
s = s.replace(old_tick, new_tick, 1)

# ── 3. the two new generators ─────────────────────────────────────────
NEW_GENS = r"""
  /* ── 9. PHOTO REVEAL: the picture sharpens as the clock runs down ── */
  pick(PL.filter(p => p.img), 8).forEach(p => {
    const others = PL.filter(x => x.id !== p.id);
    out.push({
      t: 'Quem é este jogador? (a foto vai ficando nítida)',
      a: [p.id], type: 'player',
      reveal: p.img,
      textTiles: true,
      pool: others.map(x => x.id),
      d: 2,
    });
  });

  /* ── 10. CAREER PATH: guess the player from the clubs he played for ── */
  pick(PL.filter(p => (p.clubs || []).length >= 3), 8).forEach(p => {
    const path = (p.clubs || []).slice(0, 5).map(clubName).join('  →  ');
    out.push({
      t: `Que jogador seguiu este caminho?\n${path}`,
      a: [p.id], type: 'player',
      textTiles: true,
      pool: PL.filter(x => x.id !== p.id).map(x => x.id),
      d: 3,
    });
  });
"""
m = re.search(r"(\n  return out;\n\}\n)", s)
if not m: print("ERR GEN_QS return anchor"); sys.exit(1)
s = s[:m.start(1)] + NEW_GENS + s[m.start(1):]

# question text may now contain a newline (career path) — render it
s = s.replace("""      <p style="font-size:15px;font-weight:600;color:#fff;line-height:1.48;
        margin:0;flex:1;font-family:'Inter',system-ui;">
        ${q.t}</p>""",
"""      <p style="font-size:15px;font-weight:600;color:#fff;line-height:1.48;
        margin:0;flex:1;font-family:'Inter',system-ui;white-space:pre-line;">
        ${q.t}</p>""", 1)

io.open(P, "w", encoding="utf-8").write(s)
print("photo reveal + career path patched")
