#!/usr/bin/env python3
"""Verify BR_CHAMPS / LIB_CHAMPS year by year against Wikipedia.

85 of the app's written questions are generated from these two tables, so one
wrong year is one wrong question shown to players forever. Nothing else checks
them: validate.py only asks whether the club id resolves, not whether the club
actually won that year.

Reads `|campeão =` from each season's own infobox — a single unambiguous value —
rather than parsing the one big prose-heavy list article. ~77 requests, so it is
a separate tool rather than part of run_tests.

  python3 tools/check_champs.py          # exits non-zero if any year is wrong

Verified to work by planting two wrong years and confirming both were caught.
"""
import json, re, os, sys, time, urllib.request, urllib.parse, unicodedata
UA="FutebolQuizBR/1.2 (https://tdosreis.github.io/futebol-quiz/; tiagor.reis@gmail.com)"
ROOT="/Users/tiagodosreis/git/play-store/futebol-quiz"
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA}),timeout=60).read()
def wt(title):
    d=json.loads(get("https://pt.wikipedia.org/w/api.php?format=json&action=query&prop=revisions"
                     "&rvprop=content&rvslots=main&redirects=1&titles="+urllib.parse.quote(title)).decode())
    q=d.get("query",{}); pg=list(q.get("pages",{}).values())[0]
    if "missing" in pg or "revisions" not in pg: return None
    return pg["revisions"][0]["slots"]["main"]["*"]
def fold(x): return ''.join(c for c in unicodedata.normalize('NFD',x.lower()) if unicodedata.category(c)!='Mn')

NAMES = {
 'flamengo':'flamengo','fluminense':'fluminense','vasco':'vasco','botafogo':'botafogo',
 'corinthians':'corinthians','palmeiras':'palmeiras','saopaulo':'sao paulo','santos':'santos',
 'gremio':'gremio','internacional':'internacional','cruzeiro':'cruzeiro',
 'atleticomg':'atletico-mg','atleticopr':'athletico-pr','bahia':'bahia','coritiba':'coritiba',
 'guarani':'guarani','sport':'sport',
}
ALIAS = {'atletico mineiro':'atleticomg','atletico-mg':'atleticomg',
         'athletico paranaense':'atleticopr','athletico-pr':'atleticopr',
         'atletico paranaense':'atleticopr','atletico-pr':'atleticopr',
         'sao paulo':'saopaulo'}
def champ_id(raw):
    f=fold(raw)
    for a,cid in ALIAS.items():
        if a in f: return cid
    best=None
    for cid,pat in NAMES.items():
        if pat in f:
            if best is None or len(pat)>len(NAMES[best]): best=cid
    return best

src=open(os.path.join(ROOT,"index.html")).read()
def table(name):
    blk=re.search(name+r" = \{(.*?)\n\};",src,re.S).group(1)
    return {int(y):c for y,c in re.findall(r"(\d{4}):'(\w+)'",blk)}
BR, LIB = table("const BR_CHAMPS"), table("const LIB_CHAMPS")

def article(kind, y):
    if kind=='BR':
        return ([f"Campeonato Brasileiro de Futebol de {y} - Série A"] if y>=2006
                else []) + [f"Campeonato Brasileiro de Futebol de {y}"]
    return [f"Copa Libertadores da América de {y}"]

def verify(kind, tbl):
    print(f"\n===== {kind} — {len(tbl)} years =====")
    bad, unknown = [], []
    for y in sorted(tbl, reverse=True):
        got = None; raw = ''
        for t in article(kind, y):
            x = wt(t)
            if not x: continue
            m = re.search(r"\|\s*campe[aã]o\s*=\s*(.+)", x)
            if m: raw = m.group(1).strip(); got = champ_id(raw); break
        ours = tbl[y]
        if got is None:
            unknown.append((y, ours, raw[:60])); mark = '  ?'
        elif got != ours:
            bad.append((y, ours, got, raw[:60])); mark = ' !!'
        else:
            mark = ''
        if mark: print(f"  {y}  ours={ours:14s} wiki={got}   {raw[:56]}{mark}")
        time.sleep(0.25)
    print(f"  -> {len(tbl)-len(bad)-len(unknown)} confirmed, {len(bad)} WRONG, {len(unknown)} unresolved")
    return bad, unknown

bb, bu = verify('BR', BR)
lb, lu = verify('LIB', LIB)
bad = bb + lb
unknown = bu + lu
print(f"\n{len(BR)+len(LIB)-len(bad)-len(unknown)} of {len(BR)+len(LIB)} years confirmed against Wikipedia")
if unknown:
    print("  could not resolve (check by hand):")
    for y, ours, raw in unknown: print(f"    {y}  ours={ours}  raw={raw!r}")
if bad:
    print("  WRONG:")
    for y, ours, got, raw in bad: print(f"    {y}  ours={ours}  wikipedia={got}")
sys.exit(1 if bad else 0)
