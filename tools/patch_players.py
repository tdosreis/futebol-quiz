#!/usr/bin/env python3
"""Merge data/players_extra.json into index.html (PL + PL_META + CREDITS)."""
import json, io, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
P = os.path.join(ROOT, "index.html")
s = io.open(P, encoding="utf-8").read()
players = json.load(io.open(os.path.join(ROOT, "data", "players_extra.json"), encoding="utf-8"))
credits = json.load(io.open(os.path.join(ROOT, "data", "credits.json"), encoding="utf-8"))

if "EXPANDED SQUAD" in s:
    print("already patched"); sys.exit(0)

existing = set(re.findall(r"\{ *id:'([\w_]+)'", re.search(r"const PL = \[(.*?)\n\];", s, re.S).group(1)))
new = {k: v for k, v in players.items() if k not in existing}
print(f"adding {len(new)} players (pool {len(existing)} -> {len(existing)+len(new)})")

# verify images exist
missing = [v["img"] for v in new.values() if not os.path.exists(os.path.join(ROOT, v["img"]))]
if missing:
    print("ERROR missing image files:", missing[:5]); sys.exit(1)

def esc(x): return x.replace("\\", "\\\\").replace("'", "\\'")

# ── 1. PL entries ──
rows = ["\n  /* ── EXPANDED SQUAD (Wikimedia Commons, freely licensed) ── */"]
for k, v in sorted(new.items(), key=lambda kv: (kv[1]["pos"], kv[1]["n"])):
    rows.append(f"  {{ id:'{k}', n:'{esc(v['n'])}', nat:'{v['nat']}', img:'{v['img']}' }},")
pl_m = re.search(r"(const PL = \[.*?)(\n\];)", s, re.S)
s = s[:pl_m.end(1)] + "\n" + "\n".join(rows) + s[pl_m.end(1):]

# ── 2. PL_META entries ──
metas = ["\n  /* ── expanded squad ── */"]
for k, v in sorted(new.items(), key=lambda kv: (kv[1]["pos"], kv[1]["n"])):
    clubs = ",".join(f"'{c}'" for c in v["clubs"])
    metas.append(f"  {k}: {{ pos:'{v['pos']}', era:[{v['era'][0]},{v['era'][1]}], "
                 f"ctry:'{v['ctry']}', clubs:[{clubs}] }},")
mt = re.search(r"(const PL_META = \{.*?)(\n\};)", s, re.S)
s = s[:mt.end(1)] + "\n" + "\n".join(metas) + s[mt.end(1):]

# ── 3. club display names for any new club ids ──
known = set(re.findall(r"^\s*(\w+):'", re.search(r"const CLUB_NAMES = \{(.*?)\n\};", s, re.S).group(1), re.M))
known |= set(re.findall(r"\{ *id:'([\w_]+)'", re.search(r"const CL = \[(.*?)\n\];", s, re.S).group(1)))
EXTRA = {
 'liverpool':'Liverpool','schalke':'Schalke 04','karlsruher':'Karlsruher','brondby':'Brøndby',
 'rennes':'Rennes','genk':'Genk','atletico':'Atlético de Madrid','dinamomoscow':'Dínamo de Moscou',
 'celtic':'Celtic','southampton':'Southampton','stuttgart':'Stuttgart','sparta':'Sparta Praga',
 'villarreal':'Villarreal','vissel':'Vissel Kobe','nycfc':'New York City FC','westham':'West Ham',
 'palermo':'Palermo','basel':'Basel','salzburg':'RB Salzburg','independiente':'Independiente',
 'mallorca':'Mallorca','dynamokyiv':'Dínamo de Kiev','padova':'Padova','sydney':'Sydney FC',
 'dcunited':'D.C. United','newcastle':'Newcastle','honved':'Honvéd','millonarios':'Millonarios',
 'espanyol':'Espanyol','fortlauderdale':'Fort Lauderdale','prestonne':'Preston North End',
 'alsadd':'Al-Sadd','leverkusen':'Bayer Leverkusen','panathinaikos':'Panathinaikos',
 'pescara':'Pescara','wolfsburg':'Wolfsburg','zenit':'Zenit','fiorentina':'Fiorentina',
}
need = set()
for v in players.values():
    for c in v["clubs"]:
        if c not in known: need.add(c)
add = {c: EXTRA.get(c) for c in sorted(need)}
unknown = [c for c, n in add.items() if not n]
if unknown:
    print("WARN no display name for:", unknown)
lines = "".join(f"\n  {c}:'{esc(n)}'," for c, n in add.items() if n)
if lines:
    cm = re.search(r"(const CLUB_NAMES = \{.*?)(\n\};)", s, re.S)
    s = s[:cm.end(1)] + lines + s[cm.end(1):]
    print(f"added {len([1 for n in add.values() if n])} club display names")

# ── 4. image credits (CC BY-SA requires attribution) ──
cred_js = ["\n/* ═══════════════════════════════════════════════════",
           "   IMAGE CREDITS — Wikimedia Commons",
           "   CC licences require attribution; shown on the Créditos screen.",
           "═══════════════════════════════════════════════════ */",
           "const CREDITS = {"]
for fn, c in sorted(credits.items()):
    author = re.sub(r"\s+", " ", c.get("author", ""))[:80]
    cred_js.append(f"  '{fn}': {{ a:'{esc(author)}', l:'{esc(c.get('license',''))}' }},")
cred_js.append("};")
anchor = "/* ═══════════════════════════════════════════════════\n   MIXED GAME BUILDER"
s = s.replace(anchor, "\n".join(cred_js) + "\n\n" + anchor, 1)

io.open(P, "w", encoding="utf-8").write(s)
print("patched index.html")
