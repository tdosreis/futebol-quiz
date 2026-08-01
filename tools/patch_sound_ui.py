#!/usr/bin/env python3
"""Persisted mute toggle + clearer reveal feedback (name the right answer)."""
import re, io, os, sys

P = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
s = io.open(P, encoding="utf-8").read()
if "MUTE" in s:
    print("already patched"); sys.exit(0)

# ── 1. mute flag honoured inside beep() ──────────────────────────────
s = s.replace("""function beep(freq, dur, type='sine', vol=0.18, freqEnd=null) {""",
"""/* MUTE — read straight from storage so it survives a reload */
let muted = (() => { try { return localStorage.getItem('fqbr_muted') === 'true'; }
                     catch (e) { return false; } })();
function setMuted(v) {
  muted = v;
  try { localStorage.setItem('fqbr_muted', String(v)); } catch (e) {}
}

function beep(freq, dur, type='sine', vol=0.18, freqEnd=null) {
  if (muted) return;""", 1)

# ── 2. toggle button on the home screen ──────────────────────────────
s = s.replace("""    <button id="bcred" style="background:none;border:none;""",
"""    <div style="display:flex;gap:14px;align-items:center;">
      <button id="bmute" style="background:none;border:none;cursor:pointer;
        font-size:15px;opacity:.55;padding:2px;" title="Som">${muted ? '🔇' : '🔊'}</button>
      <button id="bmed" style="background:none;border:none;
        color:rgba(255,255,255,.22);font-size:10px;cursor:pointer;
        font-family:'Inter',system-ui;text-decoration:underline;padding:2px;">
        Medalhas</button>
    </div>
    <button id="bcred" style="background:none;border:none;""", 1)

s = s.replace("""  document.getElementById('surv-btn')?.addEventListener('click', () => { snd.select(); startSurvival(); });""",
"""  document.getElementById('surv-btn')?.addEventListener('click', () => { snd.select(); startSurvival(); });
  document.getElementById('bmed')?.addEventListener('click',  () => { snd.swipe(); sc='medals'; go(); });
  document.getElementById('bmute')?.addEventListener('click', () => { setMuted(!muted); snd.tap(); go(); });""", 1)

# ── 3. when you miss, say what the right answer was ──────────────────
s = s.replace("""    : `<span style="font-size:15px;font-weight:800;color:#f44336;
        font-family:'Inter',system-ui;">✗ Errou!</span>`;""",
"""    : `<span style="font-size:15px;font-weight:800;color:#f44336;
        font-family:'Inter',system-ui;">✗ Errou!</span>
       <div style="font-size:11px;color:rgba(255,255,255,.55);margin-top:3px;
        font-family:'Inter',system-ui;">Resposta: <strong style="color:#00e676;">${
          q.a.map(id => {
            const pool = q.type === 'player' ? PL : CL;
            const hit = pool.find(x => x.id === id);
            return hit ? hit.n : id;
          }).join(', ')}</strong></div>`;""", 1)

io.open(P, "w", encoding="utf-8").write(s)
print("mute toggle + reveal feedback patched")
