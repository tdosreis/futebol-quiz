#!/usr/bin/env python3
"""Credits/attribution screen (CC licences require it) + home-screen polish."""
import re, io, os, sys

P = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
s = io.open(P, encoding="utf-8").read()
if "CREDITS SCREEN" in s:
    print("already patched"); sys.exit(0)

# ── credits screen ────────────────────────────────────────────────────
SCREEN = """
  /* ── CREDITS SCREEN ── */
  if (sc === 'credits') {
    const pairs = {};
    Object.values(typeof CREDITS !== 'undefined' ? CREDITS : {}).forEach(c => {
      const k = (c.a || 'Desconhecido') + '||' + (c.l || '?');
      pairs[k] = (pairs[k] || 0) + 1;
    });
    const rows = Object.keys(pairs).sort().map(k => {
      const [a, l] = k.split('||');
      return `<div style="display:flex;justify-content:space-between;gap:8px;
        padding:5px 0;border-bottom:1px solid rgba(255,255,255,.05);">
        <span style="font-size:10px;color:rgba(255,255,255,.62);flex:1;
          font-family:'Inter',system-ui;line-height:1.35;">${a}</span>
        <span style="font-size:9px;color:rgba(255,215,0,.55);white-space:nowrap;
          font-family:'Inter',system-ui;">${l}</span>
      </div>`;
    }).join('');
    return `
    <div style="display:flex;flex-direction:column;min-height:500px;padding:16px;gap:10px;">
      <div style="display:flex;align-items:center;gap:8px;">
        <button id="bhome" style="background:rgba(255,255,255,.07);border:none;
          color:rgba(255,255,255,.45);font-size:11px;padding:5px 11px;
          border-radius:12px;cursor:pointer;font-family:'Inter',system-ui;">← Início</button>
        <span style="font-size:13px;font-weight:700;color:rgba(255,255,255,.55);
          font-family:'Inter',system-ui;">Créditos das imagens</span>
      </div>
      <p style="font-size:11px;color:rgba(255,255,255,.42);line-height:1.65;margin:0;
        font-family:'Inter',system-ui;">
        As fotos dos jogadores vêm da <strong style="color:rgba(255,255,255,.7);">Wikimedia
        Commons</strong> e são usadas sob licenças livres (CC / domínio público).
        Obrigado a cada autor listado abaixo.<br><br>
        Escudos dos clubes são marcas registradas de seus respectivos clubes, exibidos
        apenas para identificação dentro do quiz.
      </p>
      <div style="flex:1;overflow-y:auto;background:rgba(255,255,255,.03);
        border:1px solid rgba(255,255,255,.07);border-radius:11px;padding:10px 12px;
        max-height:330px;">${rows || '<span style="font-size:11px;color:#888;">—</span>'}</div>
      <p style="font-size:9px;color:rgba(255,255,255,.25);text-align:center;margin:0;
        font-family:'Inter',system-ui;">
        Detalhes completos: commons.wikimedia.org</p>
    </div>`;
  }

"""
anchor = "  /* ── Difficulty Selection ── */"
if anchor not in s: print("ERR difficulty anchor"); sys.exit(1)
s = s.replace(anchor, SCREEN + anchor, 1)

# ── home-screen link ──────────────────────────────────────────────────
old_tail = """    ${stats.games > 0 ? `<div style="font-size:10px;color:rgba(255,255,255,.25);"""
new_tail = """    <button id="bcred" style="background:none;border:none;
      color:rgba(255,255,255,.22);font-size:10px;cursor:pointer;
      font-family:'Inter',system-ui;text-decoration:underline;padding:2px;">
      Créditos das imagens</button>
    ${stats.games > 0 ? `<div style="font-size:10px;color:rgba(255,255,255,.25);"""
if old_tail not in s: print("ERR home tail anchor"); sys.exit(1)
s = s.replace(old_tail, new_tail, 1)

# ── wire it up ────────────────────────────────────────────────────────
s = s.replace("""  document.getElementById('daily-btn')?.addEventListener('click', () => { snd.select(); startDaily(); });""",
"""  document.getElementById('daily-btn')?.addEventListener('click', () => { snd.select(); startDaily(); });
  document.getElementById('bcred')?.addEventListener('click', () => { snd.swipe(); sc='credits'; go(); });""", 1)

io.open(P, "w", encoding="utf-8").write(s)
print("credits screen patched")
