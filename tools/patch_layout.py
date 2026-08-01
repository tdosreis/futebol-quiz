#!/usr/bin/env python3
"""Two-column layout for name tiles + category badges for generated questions."""
import re, io, os, sys

P = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
s = io.open(P, encoding="utf-8").read()
if "GENCAT" in s:
    print("already patched"); sys.exit(0)

# ── 1. name tiles need wider cells than crest tiles ───────────────────
old = """    <!-- Club grid: 5×2 -->
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:7px;">"""
new = """    <!-- Option grid — 2 wide columns for name tiles, 5 for crest/face tiles -->
    <div style="display:grid;grid-template-columns:repeat(${q.textTiles ? 2 : 5},1fr);gap:7px;">"""
if old not in s: print("ERR grid anchor"); sys.exit(1)
s = s.replace(old, new, 1)

# ── 2. label generated questions so the header chip isn't generic ─────
GENCAT = """  /* GENCAT — badge shown in the quiz header for generated questions */
  const GC = {
    club:  { id:'g_club',  name:'Carreira',  emoji:'🧭', col:'#26A69A' },
    pos:   { id:'g_pos',   name:'Posição',   emoji:'🎯', col:'#7E57C2' },
    nat:   { id:'g_nat',   name:'Seleções',  emoji:'🌎', col:'#42A5F5' },
    hist:  { id:'g_hist',  name:'História',  emoji:'📚', col:'#C8A400' },
    squad: { id:'g_squad', name:'Elenco',    emoji:'👥', col:'#66BB6A' },
    era:   { id:'g_era',   name:'Época',     emoji:'⏳', col:'#FFA726' },
    photo: { id:'g_photo', name:'Foto',      emoji:'📸', col:'#EC407A' },
    path:  { id:'g_path',  name:'Caminho',   emoji:'🗺️', col:'#26C6DA' },
  };
"""
m = re.search(r"(function GEN_QS\(tier\) \{\n)", s)
if not m: print("ERR GEN_QS anchor"); sys.exit(1)
s = s[:m.end(1)] + GENCAT + s[m.end(1):]

# attach the right badge to each generator's output
subs = [
 ("      face: p.img,\n      d: p.ctry === 'BRA' ? 2 : 3,",
  "      face: p.img, _cat: GC.club,\n      d: p.ctry === 'BRA' ? 2 : 3,"),
 ("        pool: others.map(x => x.id),\n        d: pos === 'GK' ? 1 : 2,",
  "        pool: others.map(x => x.id), _cat: GC.pos,\n        d: pos === 'GK' ? 1 : 2,"),
 ("      pool: PL.filter(x => x.ctry !== c).map(x => x.id),\n      d: 2,",
  "      pool: PL.filter(x => x.ctry !== c).map(x => x.id), _cat: GC.nat,\n      d: 2,"),
 ("    out.push({ t: 'Qual destes clubes foi fundado primeiro?',\n               a: [oldest.id], fixed: set.map(c => c.id), d: 3 });",
  "    out.push({ t: 'Qual destes clubes foi fundado primeiro?',\n               a: [oldest.id], fixed: set.map(c => c.id), _cat: GC.hist, d: 3 });"),
 ("    out.push({ t: 'Qual destes clubes tem mais títulos do Brasileirão?',\n               a: [top.id], fixed: set.map(c => c.id), d: 2 });",
  "    out.push({ t: 'Qual destes clubes tem mais títulos do Brasileirão?',\n               a: [top.id], fixed: set.map(c => c.id), _cat: GC.hist, d: 2 });"),
 ("               fixed: champs.concat(rest).map(c => c.id), d: 2 });",
  "               fixed: champs.concat(rest).map(c => c.id), _cat: GC.hist, d: 2 });"),
 ("      crest: c,\n      d: 3,", "      crest: c, _cat: GC.squad,\n      d: 3,"),
 ("      pool: others.map(x => x.id),\n      d: 3,\n    });\n  });\n\n  /* ── 9.",
  "      pool: others.map(x => x.id), _cat: GC.era,\n      d: 3,\n    });\n  });\n\n  /* ── 9."),
 ("      pool: others.map(x => x.id),\n      d: 2,\n    });\n  });\n\n  /* ── 10.",
  "      pool: others.map(x => x.id), _cat: GC.photo,\n      d: 2,\n    });\n  });\n\n  /* ── 10."),
 ("      pool: PL.filter(x => x.id !== p.id).map(x => x.id),\n      d: 3,",
  "      pool: PL.filter(x => x.id !== p.id).map(x => x.id), _cat: GC.path,\n      d: 3,"),
]
miss = 0
for a, b in subs:
    if a in s: s = s.replace(a, b, 1)
    else: miss += 1; print("  warn: no match ->", a.strip().splitlines()[0][:60])
print(f"{len(subs)-miss}/{len(subs)} generator badges attached")

io.open(P, "w", encoding="utf-8").write(s)
print("layout patched")
