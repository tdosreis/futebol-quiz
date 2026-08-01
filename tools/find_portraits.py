#!/usr/bin/env python3
"""List well-shaped, freely-licensed portrait candidates for specific players.

Prefers files from the player's own Commons category (so we don't grab a photo
of a different person with the same name), scored on how close to square the
image is, since the tiles crop to a circle.
"""
import json, urllib.request, urllib.parse, time, sys

UA = "FutebolQuizBR/1.1 (https://tdosreis.github.io/futebol-quiz/; tiagor.reis@gmail.com)"

TARGETS = {
 "julio_cesar": ["Category:Júlio César (footballer, born 1979)", "Júlio César Soares Espíndola"],
 "totti":       ["Category:Francesco Totti", "Francesco Totti"],
 "muller_sp":   ["Category:Müller (footballer, born 1966)", "Müller footballer Brazil"],
 "zico":        ["Category:Zico", "Zico footballer"],
 "leao":        ["Category:Émerson Leão", "Emerson Leão"],
}

def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=30).read()

def api(params):
    return json.loads(get("https://commons.wikimedia.org/w/api.php?format=json&" +
                          urllib.parse.urlencode(params)))

def files_in_category(cat):
    try:
        d = api({"action": "query", "list": "categorymembers", "cmtitle": cat,
                 "cmtype": "file", "cmlimit": "60"})
        return [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
    except Exception:
        return []

def files_by_search(q):
    try:
        d = api({"action": "query", "list": "search", "srsearch": q,
                 "srnamespace": "6", "srlimit": "40"})
        return [m["title"] for m in d.get("query", {}).get("search", [])]
    except Exception:
        return []

def info(titles):
    out = []
    for i in range(0, len(titles), 20):
        chunk = titles[i:i+20]
        try:
            d = api({"action": "query", "titles": "|".join(chunk),
                     "prop": "imageinfo", "iiprop": "url|size|extmetadata",
                     "iiurlwidth": "400"})
            for _, p in d.get("query", {}).get("pages", {}).items():
                ii = (p.get("imageinfo") or [{}])[0]
                if not ii.get("width"): continue
                md = ii.get("extmetadata", {})
                out.append({
                    "title": p["title"],
                    "w": ii["width"], "h": ii["height"],
                    "ar": round(ii["width"] / ii["height"], 2),
                    "thumb": ii.get("thumburl", ""),
                    "lic": md.get("LicenseShortName", {}).get("value", "?"),
                    "author": __import__("re").sub(r"<[^>]+>", "",
                              md.get("Artist", {}).get("value", ""))[:40],
                })
        except Exception as e:
            print("   info err", str(e)[:50])
        time.sleep(0.8)
    return out

BAD = ("logo", "signature", "coat of arms", "stadium", "map", "flag", "trophy",
       "kit", "shirt", ".svg", "career", "statistics", "autograph")

for pid, queries in TARGETS.items():
    print(f"\n=== {pid} ===")
    titles = []
    for q in queries:
        titles = files_in_category(q) if q.startswith("Category:") else files_by_search(q)
        if titles: break
        time.sleep(0.8)
    titles = [t for t in titles if not any(b in t.lower() for b in BAD)]
    if not titles:
        print("   no candidates"); continue
    cands = info(titles[:24])
    # closest to square, decent resolution, free licence
    cands = [c for c in cands if c["w"] >= 200 and c["h"] >= 200]
    cands.sort(key=lambda c: (abs(c["ar"] - 0.85), -c["w"]))
    for c in cands[:5]:
        print(f"   ar={c['ar']:<5} {c['w']}x{c['h']:<6} [{c['lic'][:16]}] {c['title'][6:60]}")
