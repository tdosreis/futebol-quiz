#!/usr/bin/env python3
"""Check every written question in tools/questions/*.json against its source.

Each row carries src = [lang, article, [terms]]: the Wikipedia article that
settles it and the words that must all appear there. The article is read as its
plain text *and* its wikitext, because the facts a quiz asks about — a final's
score, a top scorer, a founding year — live in tables and infoboxes that the
plain-text extract leaves out.

It cannot prove a question right. It does catch the usual way a written
question goes wrong: a year, a name or a club that the article does not carry.

  SCRATCH=/some/dir python3 tools/check_questions.py [file.json ...]

Articles are cached in $SCRATCH/wiki, so a re-run only fetches what changed.
"""
import glob, hashlib, io, json, os, sys, time, unicodedata, urllib.parse, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UA = "FutebolQuizBR/1.3 (https://tdosreis.github.io/futebol-quiz/; tiagor.reis@gmail.com)"
CACHE = os.path.join(os.environ.get("SCRATCH") or sys.exit("set SCRATCH"), "wiki")
os.makedirs(CACHE, exist_ok=True)


def fold(x):
    x = unicodedata.normalize("NFD", str(x).lower())
    return "".join(c for c in x if unicodedata.category(c) != "Mn")


def api(lang, params):
    u = f"https://{lang}.wikipedia.org/w/api.php?format=json&formatversion=2&redirects=1&" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
        except Exception:
            time.sleep(2 + attempt * 3)
    return {}


def article(lang, title):
    key = hashlib.sha1(f"{lang}:{title}".encode()).hexdigest()[:20]
    path = os.path.join(CACHE, key + ".txt")
    if os.path.exists(path):
        return io.open(path, encoding="utf-8").read()
    d = api(lang, {"action": "query", "titles": title, "prop": "extracts|revisions",
                   "explaintext": 1, "rvprop": "content", "rvslots": "main"})
    pages = (d.get("query") or {}).get("pages") or [{}]
    pg = pages[0]
    text = (pg.get("extract") or "") + "\n" + \
        ((pg.get("revisions") or [{}])[0].get("slots", {}).get("main", {}).get("content") or "")
    if pg.get("missing") or not text.strip():
        text = ""
    io.open(path, "w", encoding="utf-8").write(text)
    time.sleep(0.25)
    return text


def main():
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, "tools", "questions", "*.json")))
    bad = total = 0
    for f in files:
        cat = json.load(io.open(f, encoding="utf-8"))
        for i, q in enumerate(cat["qs"]):
            total += 1
            lang, title, terms = q["src"]
            body = fold(article(lang, title))
            where = f"{os.path.basename(f)}#{i + 1}"
            if not body:
                bad += 1
                print(f"  ?? {where}: article not found ({lang}:{title}) :: {q['t'][:70]}")
                continue
            miss = [x for x in terms + q.get("xs", []) if fold(x) not in body]
            if q.get("xsrc"):
                l2, t2, te2 = q["xsrc"]
                b2 = fold(article(l2, t2))
                miss += [f"{x} ({t2})" for x in te2 if fold(x) not in b2]
            if miss:
                bad += 1
                print(f"  ?? {where}: {miss} not in {lang}:{title} :: {q['t'][:70]}")
    print(f"\n{total - bad} of {total} questions confirmed against their article")
    sys.exit(1 if bad else 0)


main()
