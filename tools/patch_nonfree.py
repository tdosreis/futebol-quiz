#!/usr/bin/env python3
"""Remove every non-free (Wikipedia fair-use) image from the bundle.

5 club crests fall back to the app's own hand-drawn SVG crest artwork,
which already covers all 25 clubs. 1 decorative news photo is dropped.
"""
import re, io, os, json, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
P = os.path.join(ROOT, "index.html")
s = io.open(P, encoding="utf-8").read()
credits = json.load(io.open(os.path.join(ROOT, "data", "credits.json"), encoding="utf-8"))
nonfree = {k for k, v in credits.items() if v.get("license") == "NON-FREE"}
if not nonfree:
    print("no non-free images"); sys.exit(0)
print(f"{len(nonfree)} non-free images to remove")

if "clubArt" not in s:
    # ── 1. helper: real crest if we have a free one, else our own SVG ──
    HELPER = """
/* Club artwork: use the licensed crest image when we have one, otherwise fall
   back to the app's own hand-drawn SVG crest (see crest() above). This keeps
   the bundle free of non-free Wikipedia files. */
function clubArt(id, style) {
  if (LOGOS[id]) {
    return `<img src="${LOGOS[id]}" alt="" style="${style}"
      onerror="this.style.opacity='.3'" />`;
  }
  return `<svg viewBox="0 0 60 60" style="${style}" aria-hidden="true">${crest(id)}</svg>`;
}
"""
    anchor = "/* ═══════════════════════════════════════════════════\n   BADGE"
    if anchor not in s: print("ERR badge anchor"); sys.exit(1)
    s = s.replace(anchor, HELPER + "\n" + anchor, 1)

    # ── 2. route both render sites through it ──
    s = s.replace("""    <img src="${LOGOS[item.id]}" alt="${item.n}"
      style="width:78%;height:78%;object-fit:contain;pointer-events:none;flex-shrink:0;"
      onerror="this.style.opacity='.3'" />""",
    """    ${clubArt(item.id, 'width:78%;height:78%;object-fit:contain;pointer-events:none;flex-shrink:0;')}""", 1)

    s = s.replace("""        <img src="${LOGOS[q.crest]}" alt=""
          style="max-width:100%;max-height:100%;object-fit:contain;"
          onerror="this.parentElement.style.display='none'" />""",
    """        ${clubArt(q.crest, 'max-width:100%;max-height:100%;object-fit:contain;')}""", 1)

# ── 3. drop the non-free entries ──────────────────────────────────────
removed = []
for fn in sorted(nonfree):
    # LOGOS entry -> delete the line so clubArt falls back to SVG
    m = re.search(r"\n\s*(\w+):\s*'" + re.escape(fn) + r"',", s)
    if m:
        removed.append(("crest", m.group(1)))
        s = s[:m.start()] + s[m.end():]
        continue
    # question image -> strip the attribute
    m2 = re.search(r",\s*qimg:'" + re.escape(fn) + r"'", s)
    if m2:
        removed.append(("qimg", fn))
        s = s[:m2.start()] + s[m2.end():]

io.open(P, "w", encoding="utf-8").write(s)

# ── 4. delete the files and their credit entries ──────────────────────
for fn in nonfree:
    fp = os.path.join(ROOT, fn)
    if os.path.exists(fp): os.remove(fp)
    credits.pop(fn, None)
json.dump(credits, io.open(os.path.join(ROOT, "data", "credits.json"), "w"),
          ensure_ascii=False, indent=1)

for kind, what in removed: print(f"  removed {kind}: {what}")
print(f"deleted {len(nonfree)} files; credits now {len(credits)} entries (all free)")
