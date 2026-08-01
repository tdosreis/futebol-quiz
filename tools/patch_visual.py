#!/usr/bin/env python3
"""Visual polish: ambient depth, staggered tiles, floating score, confetti."""
import re, io, os, sys

P = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
s = io.open(P, encoding="utf-8").read()
if "VISUAL POLISH" in s:
    print("already patched"); sys.exit(0)

CSS = """
    /* ══════════ VISUAL POLISH ══════════ */

    /* Ambient stadium glow behind everything (adds depth to the flat panel) */
    #qz::before {
      content: '';
      position: absolute;
      left: -25%; right: -25%; top: -30%;
      height: 78%;
      background: radial-gradient(ellipse at 50% 0%,
        rgba(255,215,0,.075), rgba(26,140,58,.05) 42%, transparent 68%);
      pointer-events: none;
      z-index: 0;
    }
    #qz::after {
      content: '';
      position: absolute;
      left: 0; right: 0; bottom: 0; height: 34%;
      background: linear-gradient(to top, rgba(0,0,0,.35), transparent);
      pointer-events: none;
      z-index: 0;
    }

    /* Option tiles fade in with a slight stagger */
    @keyframes tileIn {
      from { opacity: 0; transform: translateY(9px) scale(.94); }
      to   { opacity: 1; transform: translateY(0)   scale(1); }
    }
    .b { animation: tileIn .3s cubic-bezier(.2,.8,.3,1) backwards; }

    /* Points that float up off the score when you gain */
    @keyframes floatUp {
      0%   { opacity: 0; transform: translate(-50%, 4px)   scale(.8); }
      18%  { opacity: 1; transform: translate(-50%, -4px)  scale(1.15); }
      100% { opacity: 0; transform: translate(-50%, -42px) scale(1); }
    }
    .gain {
      position: absolute; left: 50%; top: 0;
      font-family: 'Bebas Neue','Impact',sans-serif;
      font-size: 22px; font-weight: 900; color: #00e676;
      text-shadow: 0 2px 12px rgba(0,230,118,.6);
      pointer-events: none; z-index: 40;
      animation: floatUp 1.05s ease-out forwards;
    }

    /* Confetti for a strong finish */
    @keyframes confFall {
      0%   { opacity: 1; transform: translate3d(0,-24px,0) rotate(0deg); }
      100% { opacity: .15; transform: translate3d(var(--dx,0px), 105vh, 0) rotate(var(--rot,720deg)); }
    }
    .conf {
      position: fixed; top: -24px;
      width: 8px; height: 13px; border-radius: 2px;
      pointer-events: none; z-index: 999;
      animation: confFall linear forwards;
    }

    /* Progress dots */
    .pdot {
      width: 5px; height: 5px; border-radius: 50%;
      background: rgba(255,255,255,.16);
      transition: background .25s, transform .25s;
      flex-shrink: 0;
    }
    .pdot-on   { background: #FFD700; }
    .pdot-cur  { background: #fff; transform: scale(1.55); box-shadow: 0 0 8px rgba(255,255,255,.7); }
    .pdot-miss { background: rgba(244,67,54,.75); }

    /* Timer bar gets a moving sheen so it reads as "live" */
    @keyframes sheen { to { background-position: 240% 0; } }
    .tf-live {
      background-image: linear-gradient(100deg,
        rgba(255,255,255,0) 34%, rgba(255,255,255,.5) 50%, rgba(255,255,255,0) 66%);
      background-size: 240% 100%;
      animation: sheen 1.9s linear infinite;
    }

    /* Home ball idle bounce */
    @keyframes ballIdle {
      0%,100% { transform: translateY(0) rotate(-4deg); }
      50%     { transform: translateY(-9px) rotate(4deg); }
    }
    .ball-idle { animation: ballIdle 2.8s ease-in-out infinite; display: inline-block; }

    /* Gold gradient wordmark */
    .goldgrad {
      background: linear-gradient(175deg, #FFF3B0 4%, #FFD700 42%, #E0A800 96%);
      -webkit-background-clip: text; background-clip: text;
      -webkit-text-fill-color: transparent; color: transparent;
      filter: drop-shadow(0 3px 18px rgba(255,215,0,.32));
    }

    /* Primary buttons get depth + a press response */
    .btn-press { transition: transform .12s, box-shadow .12s, filter .12s; }
    .btn-press:active { transform: scale(.955); filter: brightness(1.08); }
"""
s = s.replace("    /* ── Misc ── */", CSS + "\n    /* ── Misc ── */", 1)

# ── staggered tiles: pass the index through to badge() ───────────────
s = s.replace("${disp.map(c => badge(c)).join('')}", "${disp.map((c, i) => badge(c, i)).join('')}", 1)
s = s.replace("function badge(item) {", "function badge(item, idx) {", 1)
# give each tile its delay
s = s.replace("""  const curQ    = (cat && cat.qs && cat.qs[qi]) || {};""",
              """  const curQ    = (cat && cat.qs && cat.qs[qi]) || {};
  const delay   = `animation-delay:${Math.min(9, idx || 0) * 32}ms;`;""", 1)
for old in ["""        width:100%;min-height:44px;border-radius:9px;cursor:pointer;""",
            """        width:100%;aspect-ratio:1;border-radius:9px;cursor:pointer;""",
            """      width:100%;aspect-ratio:1;border-radius:9px;cursor:pointer;"""]:
    s = s.replace(old, "${delay}" + old, 1)

# ── floating +points on the score ────────────────────────────────────
s = s.replace("""        <div id="score-disp" class="${scoreChanged ? 'score-up' : ''}\"""",
              """        <div id="score-disp" class="${scoreChanged ? 'score-up' : ''}" style="position:relative\"""", 1)
s = s.replace("""            font-family:'Bebas Neue','Impact',sans-serif;letter-spacing:1px;">${pts}""",
              """            font-family:'Bebas Neue','Impact',sans-serif;letter-spacing:1px;">${
          sc === 'reveal' && lastGain > 0 ? `<span class="gain">+${lastGain}</span>` : ''}${pts}""", 1)

# ── progress dots replace the bare "3/10" counter ────────────────────
s = s.replace("""        <div style="font-size:11px;color:rgba(255,255,255,.32);font-family:'Inter',system-ui;">${qi+1}/${cat.qs.length}</div>""",
"""        <div style="display:flex;align-items:center;gap:3px;max-width:104px;flex-wrap:wrap;
          justify-content:flex-end;">
          ${cat.qs.length <= 20 ? cat.qs.map((_, i) => {
              const cls = i < runLog.length ? (runLog[i] === 3 ? 'pdot pdot-on'
                        : runLog[i] === 0 ? 'pdot pdot-miss' : 'pdot pdot-on')
                        : (i === qi ? 'pdot pdot-cur' : 'pdot');
              return `<span class="${cls}"></span>`;
            }).join('')
          : `<span style="font-size:11px;color:rgba(255,255,255,.32);
               font-family:'Inter',system-ui;">${qi+1}/${cat.qs.length}</span>`}
        </div>""", 1)

# ── live sheen on the timer bar ──────────────────────────────────────
s = s.replace("""      <div id="tf" class="${timerCls}" style="height:100%;width:${tpct}%;background:${tc};""",
              """      <div id="tf" class="${timerCls} ${sc === 'quiz' ? 'tf-live' : ''}" style="height:100%;width:${tpct}%;background-color:${tc};""", 1)

# ── home screen: animated ball + gradient wordmark + button press ────
s = s.replace("""    <div style="font-size:52px;filter:drop-shadow(0 4px 16px rgba(255,215,0,.3));">⚽</div>""",
              """    <div class="ball-idle" style="font-size:56px;filter:drop-shadow(0 6px 20px rgba(255,215,0,.35));">⚽</div>""", 1)
s = s.replace("""      <div style="font-size:42px;font-weight:900;color:#FFD700;
        font-family:'Bebas Neue','Impact',sans-serif;
        letter-spacing:4px;line-height:1.05;
        text-shadow:0 2px 20px rgba(255,215,0,.35);">FUTEBOL<br>QUIZ BR</div>""",
              """      <div class="goldgrad" style="font-size:44px;font-weight:900;
        font-family:'Bebas Neue','Impact',sans-serif;
        letter-spacing:4px;line-height:1.04;">FUTEBOL<br>QUIZ BR</div>""", 1)
s = s.replace("""    <button id="cta-btn" style="margin-top:6px;background:#FFD700;""",
              """    <button id="cta-btn" class="btn-press" style="margin-top:6px;
      background:linear-gradient(180deg,#FFE469,#FFD700 45%,#E8B400);""", 1)

# ── confetti on a strong finish ──────────────────────────────────────
CONF = """
/* ── Confetti (pure DOM, no library) ── */
function burst(n) {
  const cols = ['#FFD700','#00e676','#4FC3F7','#FF7043','#FFFFFF','#AB47BC'];
  const frag = document.createDocumentFragment();
  for (let i = 0; i < n; i++) {
    const d = document.createElement('div');
    d.className = 'conf';
    d.style.left = (Math.random() * 100) + 'vw';
    d.style.background = cols[(Math.random() * cols.length) | 0];
    d.style.setProperty('--dx', ((Math.random() * 160) - 80).toFixed(0) + 'px');
    d.style.setProperty('--rot', ((Math.random() * 900) + 360).toFixed(0) + 'deg');
    d.style.animationDuration = (1.9 + Math.random() * 1.5).toFixed(2) + 's';
    d.style.animationDelay = (Math.random() * 0.5).toFixed(2) + 's';
    if (Math.random() > .6) d.style.borderRadius = '50%';
    frag.appendChild(d);
  }
  document.body.appendChild(frag);
  setTimeout(() => document.querySelectorAll('.conf').forEach(e => e.remove()), 4200);
}
"""
s = s.replace("/* ═══════════════════════════════════════════════════\n   RENDER + EVENT BINDING",
              CONF + "\n/* ═══════════════════════════════════════════════════\n   RENDER + EVENT BINDING", 1)

# fire it when the end screen renders a good result
s = s.replace("""  document.getElementById('bcred')?.addEventListener('click', () => { snd.swipe(); sc='credits'; go(); });""",
"""  document.getElementById('bcred')?.addEventListener('click', () => { snd.swipe(); sc='credits'; go(); });

  if (sc === 'end' && !window._celebrated) {
    const acc = nCorrect / Math.max(1, cat.qs.length);
    if (acc >= 0.7) { window._celebrated = true; burst(acc >= 0.9 ? 70 : 42); }
  }
  if (sc !== 'end') window._celebrated = false;""", 1)

io.open(P, "w", encoding="utf-8").write(s)
print("visual polish patched")
