#!/usr/bin/env python3
"""Recover author/licence metadata for the images downloaded before we started
capturing it. The original Wikimedia URLs still live in git history, and the
local filename is sha1(url)[:16], so the mapping is recomputable."""
import subprocess, hashlib, os, io, json, re, time, urllib.request, urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UA = "FutebolQuizBR/1.1 (https://tdosreis.github.io/futebol-quiz/; tiagor.reis@gmail.com)"
cred_path = os.path.join(ROOT, "data", "credits.json")
credits = json.load(io.open(cred_path, encoding="utf-8")) if os.path.exists(cred_path) else {}

log = subprocess.run(["git", "log", "--all", "-p", "--", "index.html"],
                     cwd=ROOT, capture_output=True, text=True).stdout
urls = sorted(set(re.findall(r"https://upload\.wikimedia\.org/[^\s\"')]+", log)))
print(f"{len(urls)} historical image URLs found")

def get(u):
    return urllib.request.urlopen(
        urllib.request.Request(u, headers={"User-Agent": UA}), timeout=30).read()

def lic(url):
    m = re.search(r"/commons/(?:thumb/)?[0-9a-f]/[0-9a-f]{2}/([^/]+)", url)
    if not m: return None
    fname = urllib.parse.unquote(m.group(1))
    api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
           "&prop=imageinfo&iiprop=extmetadata&titles=" + urllib.parse.quote("File:" + fname))
    d = json.loads(get(api))
    for _, pg in d.get("query", {}).get("pages", {}).items():
        ii = (pg.get("imageinfo") or [{}])[0].get("extmetadata", {})
        v = lambda k: re.sub(r"<[^>]+>", "", ii.get(k, {}).get("value", "")).strip()
        return {"file": fname, "author": v("Artist") or "Desconhecido",
                "license": v("LicenseShortName") or "?"}
    return None

added = nonfree = skipped = 0
for u in urls:
    ext = os.path.splitext(u)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg"): ext = ".png"
    fn = "img/" + hashlib.sha1(u.encode()).hexdigest()[:16] + ext
    if not os.path.exists(os.path.join(ROOT, fn)):
        continue                                  # not one of the files we kept
    if fn in credits:
        skipped += 1; continue
    if "/wikipedia/commons/" not in u:
        credits[fn] = {"file": u.rsplit("/", 1)[-1], "author": "Wikipedia (uso não-livre)",
                       "license": "NON-FREE"}
        nonfree += 1
        print(f"  !! NON-FREE {fn}  {u.rsplit('/',1)[-1][:50]}")
        continue
    try:
        info = lic(u)
        if info:
            credits[fn] = info
            added += 1
            print(f"  ok {fn}  [{info['license']}]  {info['author'][:38]}")
    except Exception as e:
        print(f"  !! {fn}: {str(e)[:60]}")
    time.sleep(1.1)

json.dump(credits, io.open(cred_path, "w"), ensure_ascii=False, indent=1)
print(f"\nadded={added} already-had={skipped} non-free={nonfree} total={len(credits)}")
