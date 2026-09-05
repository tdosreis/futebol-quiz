#!/usr/bin/env python3
"""Find freely-licensed club crests and stadium photos on Wikimedia Commons.

Only licences we may actually redistribute inside a shipped app are accepted —
public domain, CC0, CC BY and CC BY-SA. Anything marked fair use or non-free is
dropped on the floor, which is why several Brazilian crests will simply come
back empty and keep the app's drawn badge instead.

Files land in img/ named sha1(source-url)[:16], the same scheme the rest of the
artwork uses, and the author + licence for every one is printed so it can go
straight into CREDITS. Nothing is written into index.html by this script.

  python3 tools/fetch_club_art.py crests   > /tmp/crests.json
  python3 tools/fetch_club_art.py stadiums > /tmp/stadiums.json
"""
import json, urllib.request, urllib.parse, hashlib, os, sys, re, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IMG  = os.path.join(ROOT, "img")
UA   = "FutebolQuizBR/1.2 (https://tdosreis.github.io/futebol-quiz/; tiagor.reis@gmail.com)"

FREE = re.compile(r"(public domain|^cc0|^cc[ -]by)", re.I)
BAD  = re.compile(r"(fair use|non-free|nonfree|copyright)", re.I)

# club id -> Commons file titles to try, best first
CRESTS = {
    "goias":        ["File:Goiás Esporte Clube logo.svg"],
    "atleticogo":   ["File:Atlético Clube Goianiense logo.svg"],
    "cuiaba":       ["File:Cuiabá Esporte Clube.png", "File:Cuiabá EC.svg"],
    "juventude":    ["File:EC Juventude.svg", "File:EC Juventude crest.png"],
    "chapecoense":  ["File:Logo Associação Chapecoense de Futebol.svg"],
    "avai":         ["File:Avaí Futebol Clube logo.svg"],
    "figueirense":  ["File:Figueirense Futebol Clube (old logo).svg"],
    "paysandu":     ["File:Paysandu-1914-1970-logo.png"],
    "remo":         ["File:Clube do Remo.svg"],
    "portuguesa":   ["File:Associação Portuguesa de Desportos.svg"],
    "csa":          ["File:Centro Sportivo Alagoano.svg", "File:CSA logo.png"],
    "santacruz":    ["File:Santa Cruz Futebol Clube logo.svg"],
    "abc":          ["File:ABC FC - RN.svg"],
    "crb":          ["File:CRB logo.svg"],
    # The .svg under this name is the club flag, not the crest; the .png is the
    # crest itself, so it goes first.
    "sampaio":      ["File:Sampaio Corrêa FC.png"],
    # Likewise for these two: the file named plainly after the club is a flag.
    "vasco":        ["File:Escudo Vasco 1903.png", "File:Escudo Vasco 1920.png"],
    "nautico":      ["File:Náutico logo (1995-2006).png", "File:Náutico Logo (2006-2008).png"],
    "mirassol":     ["File:Mirassol Futebol Clube logo.svg"],
    "botafogosp":   ["File:Botafogo Futebol Clube (Ribeirão Preto) logo.svg"],
}

# stadium id -> Commons file titles to try
STADIUMS = {
    "morumbi":      ["File:Estádio do Morumbi.jpg", "File:Morumbi Stadium.jpg"],
    "fontenova":    ["File:Arena Fonte Nova.jpg", "File:Itaipava Arena Fonte Nova.jpg"],
    "castelao_ce":  ["File:Estádio Castelão (Fortaleza).jpg", "File:Arena Castelao.jpg"],
    "baixada":      ["File:Arena da Baixada.jpg", "File:Estádio Joaquim Américo Guimarães.jpg"],
    "couto":        ["File:Estádio Couto Pereira.jpg", "File:Couto Pereira.jpg"],
    "serradourada": ["File:Estádio Serra Dourada.jpg", "File:Serra Dourada.jpg"],
    "engenhao":     ["File:Estádio Nilton Santos.jpg", "File:Engenhão.jpg"],
    "ilhadoretiro": ["File:Estádio Ilha do Retiro.jpg", "File:Ilha do Retiro.jpg"],
    "arruda":       ["File:Estádio do Arruda.jpg", "File:Arruda.jpg"],
    "arena_mrv":    ["File:Arena MRV.jpg"],
}


def get(url, timeout=45):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout).read()


def api(params):
    return json.loads(get("https://commons.wikimedia.org/w/api.php?format=json&" +
                          urllib.parse.urlencode(params)).decode("utf-8"))


def strip_html(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def lookup(titles, width):
    """First title that exists AND carries a licence we can ship."""
    for t in titles:
        try:
            d = api({"action": "query", "titles": t, "prop": "imageinfo",
                     "iiprop": "url|size|extmetadata", "iiurlwidth": str(width)})
            pages = d.get("query", {}).get("pages", {})
            for _, p in pages.items():
                if "missing" in p:
                    continue
                ii = (p.get("imageinfo") or [{}])[0]
                if not ii.get("width"):
                    continue
                md = ii.get("extmetadata", {})
                lic = strip_html(md.get("LicenseShortName", {}).get("value", ""))
                author = strip_html(md.get("Artist", {}).get("value", "")) or "Unknown"
                if BAD.search(lic) or not FREE.search(lic):
                    print(f"   skip {t} — licence {lic!r}", file=sys.stderr)
                    continue
                return {"title": p["title"], "thumb": ii.get("thumburl") or ii["url"],
                        "src": ii["url"], "lic": lic, "author": author,
                        "w": ii["width"], "h": ii["height"]}
        except Exception as e:
            print(f"   err  {t} — {e}", file=sys.stderr)
        time.sleep(0.3)
    return None


def save(entry):
    """Download the rendered thumb; filename is sha1(source-url)[:16]."""
    url = entry["thumb"]
    ext = ".png" if ".png" in url.lower() or entry["src"].lower().endswith(".svg") else ".jpg"
    name = hashlib.sha1(entry["src"].encode("utf-8")).hexdigest()[:16] + ext
    path = os.path.join(IMG, name)
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(get(url))
    return "img/" + name


def run(kind):
    table = CRESTS if kind == "crests" else STADIUMS
    width = 256 if kind == "crests" else 640
    out = {}
    for key, titles in table.items():
        print(f">> {key}", file=sys.stderr)
        e = lookup(titles, width)
        if not e:
            print(f"   NONE FREE for {key}", file=sys.stderr)
            continue
        try:
            e["path"] = save(e)
        except Exception as ex:
            print(f"   download failed: {ex}", file=sys.stderr)
            continue
        out[key] = {"path": e["path"], "author": e["author"], "lic": e["lic"],
                    "title": e["title"], "w": e["w"], "h": e["h"]}
        print(f"   {e['path']}  {e['lic']}  {e['author'][:40]}", file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False, indent=1))


run(sys.argv[1] if len(sys.argv) > 1 else "crests")
