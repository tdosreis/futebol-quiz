#!/usr/bin/env python3
"""Cross-check the written questions' specifics against their subjects' articles.

The generated questions are correct by construction — they are derived from
PL_META, so they cannot assert something the data does not hold. The written
ones are prose somebody typed, and a quiz that is confidently wrong is worse
than one that is plain.

Heuristic on purpose: it pulls the full pt.wikipedia article for each answer and
asks whether the years and counts the question asserts appear there at all. It
cannot prove a question right, and it produces false positives when the search
lands on the wrong article — but it turns ~190 questions into a shortlist of
about twenty, which is a reviewable number.

  SCRATCH=/tmp python3 tools/audit_questions.py

Needs prose.json in $SCRATCH: see the extraction step in the session notes, or
regenerate it by dumping CATS from a headless page.
Last full run: 170/189 clean, 19 flagged, all 19 confirmed correct by hand.
"""
import json, re, os, time, unicodedata, urllib.request, urllib.parse
UA="FutebolQuizBR/1.2 (https://tdosreis.github.io/futebol-quiz/; tiagor.reis@gmail.com)"
S=os.environ["SCRATCH"]
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA}),timeout=60).read()
def japi(u): return json.loads(get(u).decode())
def fold(x): return ''.join(c for c in unicodedata.normalize('NFD',str(x).lower()) if unicodedata.category(c)!='Mn')

CACHE={}
def article_text(name):
    """Full plaintext of the best-matching pt.wikipedia article for a name."""
    key=fold(name)
    if key in CACHE: return CACHE[key]
    txt=""
    try:
        d=japi("https://pt.wikipedia.org/w/api.php?format=json&action=query&list=search&srlimit=1&srsearch="
               +urllib.parse.quote(name+" futebol"))
        hits=d.get("query",{}).get("search",[])
        if hits:
            t=hits[0]["title"]
            d2=japi("https://pt.wikipedia.org/w/api.php?format=json&action=query&prop=extracts&explaintext=1"
                    "&redirects=1&titles="+urllib.parse.quote(t))
            pg=list(d2["query"]["pages"].values())[0]
            txt=pg.get("extract","") or ""
    except Exception as e:
        txt=""
    CACHE[key]=txt
    time.sleep(0.25)
    return txt

data=json.load(open(S+"/prose.json"))
risky=[d for d in data if re.search(r'\b(19|20)\d\d\b|\b\d+ gols?\b|\b\d+ t[íi]tul', d['t'], re.I)]
print(f"checking {len(risky)} questions that assert a year or a count\n")
flagged=[]
for i,d in enumerate(risky):
    subject=d['names'][0] if d['names'] else ''
    if d['type']=='txt':
        # the answer is a word; the subject worth reading is the answer itself
        subject=d['a'][0]
    txt=fold(article_text(subject))
    if not txt:
        flagged.append((d,'no article found for "%s"'%subject)); continue
    years=set(re.findall(r'\b(?:19|20)\d\d\b', d['t']))
    counts=set(re.findall(r'\b(\d+) (?:gols?|t[íi]tulos?|Copas?|Bolas? de Ouro)\b', d['t'], re.I))
    miss=[y for y in years if y not in txt]
    missc=[c for c in counts if not re.search(r'\b'+c+r'\b', txt)]
    if miss or missc:
        flagged.append((d, 'not in article: ' + ', '.join(miss+missc)))
    if (i+1)%25==0: print(f"  ...{i+1}/{len(risky)}", flush=True)

print(f"\n{len(risky)-len(flagged)} questions had every year and count present in their subject's article")
print(f"{len(flagged)} need a look:\n")
for d,why in flagged:
    print(f"  [{d['cat']:9s}] {d['t'][:78]}")
    print(f"      answer: {', '.join(d['names'])}   —   {why}")
json.dump([{'q':d,'why':w} for d,w in flagged], open(S+"/flagged.json","w"), ensure_ascii=False, indent=1)
