#!/usr/bin/env python3
"""Replace the abstract SVG fallback with a clean, designed club badge.

Five clubs (Vasco, Corinthians, Sport, Bragantino, Náutico) can't ship their
real crest because the only Wikipedia files are non-free. The old fallback drew
abstract shapes that read as random symbols; this draws a proper shield in the
club's own colours with its abbreviation, so it looks deliberate and is legible.
"""
import re, io, os, sys

P = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
s = io.open(P, encoding="utf-8").read()
if "genericCrest" in s:
    print("already patched"); sys.exit(0)

HELPER = r"""
/* ── Designed fallback badge (used when we have no licensed crest file) ── */
function _lum(hex) {
  let h = String(hex).replace('#', '');
  if (h.length === 3) h = h.split('').map(x => x + x).join('');
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
}
function _shade(hex, amt) {
  let h = String(hex).replace('#', '');
  if (h.length === 3) h = h.split('').map(x => x + x).join('');
  const f = v => Math.max(0, Math.min(255, Math.round(v + 255 * amt)));
  const r = f(parseInt(h.slice(0, 2), 16)), g = f(parseInt(h.slice(2, 4), 16)), b = f(parseInt(h.slice(4, 6), 16));
  return '#' + [r, g, b].map(v => v.toString(16).padStart(2, '0')).join('');
}

function genericCrest(id) {
  const c = CL.find(x => x.id === id);
  if (!c) return '';
  const uid  = 'bg' + id.replace(/\W/g, '');
  const dark = _lum(c.c1) < 0.5;
  const ink  = dark ? '#ffffff' : '#111111';
  const trim = _lum(c.c2) > 0.25 ? c.c2 : '#e8e8e8';
  const SHIELD = 'M30 3 L53 11 L53 30 C53 43 42 52 30 57 C18 52 7 43 7 30 L7 11 Z';
  return `
    <defs>
      <linearGradient id="${uid}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%"   stop-color="${_shade(c.c1, 0.10)}"/>
        <stop offset="100%" stop-color="${_shade(c.c1, -0.16)}"/>
      </linearGradient>
    </defs>
    <path d="${SHIELD}" fill="url(#${uid})" stroke="${trim}" stroke-width="2.6"
      stroke-linejoin="round"/>
    <path d="M30 3 L53 11 L53 17 L7 17 L7 11 Z" fill="${trim}" opacity=".92"/>
    <circle cx="30" cy="11" r="3.1" fill="${c.c1}" opacity=".85"/>
    <text x="30" y="41" text-anchor="middle"
      font-family="'Bebas Neue','Arial Black',Impact,sans-serif"
      font-size="19" font-weight="900" letter-spacing="1.2" fill="${ink}">${c.a}</text>
  `;
}
"""

anchor = "function clubArt(id, style) {"
if anchor not in s:
    print("ERR clubArt anchor"); sys.exit(1)
s = s.replace(anchor, HELPER + "\n" + anchor, 1)

# route both fallback paths to the new badge
s = s.replace(
  """  return `<svg viewBox="0 0 60 60" style="${style}" aria-hidden="true">${crest(id)}</svg>`;
}""",
  """  return `<svg viewBox="0 0 60 60" style="${style}" aria-hidden="true">${genericCrest(id)}</svg>`;
}""", 1)
s = s.replace(
  """    img.outerHTML = `<svg viewBox="0 0 60 60" style="${img.getAttribute('style') || ''}"
      aria-hidden="true">${crest(id)}</svg>`;""",
  """    img.outerHTML = `<svg viewBox="0 0 60 60" style="${img.getAttribute('style') || ''}"
      aria-hidden="true">${genericCrest(id)}</svg>`;""", 1)

io.open(P, "w", encoding="utf-8").write(s)
print("designed fallback badge patched")
