#!/usr/bin/env python3
"""Replace 5 badly-cropped player photos with squarer, freely-licensed ones."""
import json, io, os, re, time, hashlib, urllib.request, urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UA = "FutebolQuizBR/1.1 (https://tdosreis.github.io/futebol-quiz/; tiagor.reis@gmail.com)"

# player id -> Commons file title (verified to be the right person)
SWAP = {
  "leao":        "Émerson Leão (1970).jpg",
   }

def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=40).read()

def fileinfo(title):
    api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
           "&prop=imageinfo&iiprop=url|size|extmetadata&iiurlwidth=420&titles="
           + urllib.parse.quote("File:" + title))
    d = json.loads(get(api))
    for _, p in d.get("query", {}).get("pages", {}).items():
        ii = (p.get("imageinfo") or [{}])[0]
        if not ii.get("thumburl"): return None
        md = ii.get("extmetadata", {})
        clean = lambda k: re.sub(r"<[^>]+>", "", md.get(k, {}).get("value", "")).strip()
        return {"url": ii["thumburl"], "w": ii["width"], "h": ii["height"],
                "author": clean("Artist") or "Desconhecido",
                "license": clean("LicenseShortName") or "?"}
    return None

s = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
credits = json.load(io.open(os.path.join(ROOT, "data", "credits.json"), encoding="utf-8"))

for pid, title in SWAP.items():
    m = re.search(r"(\{ id:'" + pid + r"'[^}]*img:')(img/[^']+)(')", s)
    if not m:
        print(f"  !! {pid}: not found in PL"); continue
    old_fn = m.group(2)
    info = fileinfo(title)
    if not info:
        print(f"  !! {pid}: could not resolve '{title}'"); time.sleep(1.2); continue
    if "/wikipedia/commons/" not in info["url"]:
        print(f"  XX {pid}: not a Commons file, skipped"); time.sleep(1.2); continue

    ext = os.path.splitext(info["url"])[1].lower()
    if ext not in (".jpg", ".jpeg", ".png"): ext = ".jpg"
    new_fn = "img/" + hashlib.sha1(info["url"].encode()).hexdigest()[:16] + ext
    fp = os.path.join(ROOT, new_fn)
    if not os.path.exists(fp):
        io.open(fp, "wb").write(get(info["url"]))

    s = s[:m.start(2)] + new_fn + s[m.end(2):]
    credits[new_fn] = {"file": title, "author": info["author"], "license": info["license"]}

    # drop the old file if nothing else references it
    if old_fn not in s:
        op = os.path.join(ROOT, old_fn)
        if os.path.exists(op): os.remove(op)
        credits.pop(old_fn, None)
    ar = round(info["w"] / info["h"], 2)
    print(f"  ok {pid:12s} ar={ar:<5} {info['w']}x{info['h']}  [{info['license']}]  -> {new_fn}")
    time.sleep(1.2)

io.open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(s)
json.dump(credits, io.open(os.path.join(ROOT, "data", "credits.json"), "w"),
          ensure_ascii=False, indent=1)
print(f"\ncredits now {len(credits)} entries")
