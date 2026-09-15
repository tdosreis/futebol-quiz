#!/usr/bin/env python3
"""Fetch freely licensed photographs of trophies and grounds from Wikimedia Commons.

A question about a competition or a stadium used to be illustrated with a
drawn symbol. These are the real things instead. As with every other image in
the app, only public domain, CC0, CC BY and CC BY-SA files are taken, and the
author and licence of each one are recorded so the credits screen can name
them. Files are converted to .webp and named sha1(source-url)[:16].

  python3 tools/fetch_art_photos.py OUT.json [keys...]
"""
import hashlib, io, json, os, re, sys, time, urllib.parse, urllib.request
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UA = "FutebolQuizBR/1.3 (https://tdosreis.github.io/futebol-quiz/; tiagor.reis@gmail.com)"
FREE = re.compile(r"(public domain|^pd\b|^cc0|^cc[ -]by)", re.I)
BAD = re.compile(r"(fair use|non-free|nonfree)", re.I)
SKIP = re.compile(r"(logo|\.svg|map|diagram|plan|chart|drawing|kit|badge|crest|emblem|flag)", re.I)

# key -> Commons searches, best first. Each must actually show the thing.
WANT = {
    "t_worldcup": ["FIFA World Cup trophy close", "Copa do Mundo FIFA taça", "World Cup trophy Brazil tour"],
    "t_ucl":        ["UEFA Champions League trophy", "European Champion Clubs' Cup trophy"],
    "t_libert": ["Copa Libertadores trofeo museo", "Libertadores trophy CONMEBOL museum", "Trofeo de la Copa Libertadores de América"],
    "t_copaam":     ["Copa América trophy", "Trofeo Copa América"],
    "t_euro":       ["Henri Delaunay Trophy", "UEFA European Championship trophy"],
    "t_ballon": ["Ballon d'Or golden ball trophy museum", "Ballon d'Or trophy"],
    "t_premier":    ["Premier League trophy"],
    "t_uel": ["UEFA Cup trophy museum", "UEFA Europa League trophy Sevilla"],
    "t_clubwc": ["FIFA Club World Cup trophy close", "Club World Cup trophy"],
    "t_wwc": ["Women's World Cup trophy close up", "FIFA Women's World Cup trophy tour"],
    "t_fa":         ["FA Cup trophy"],
    "s_wembley":    ["Wembley Stadium interior", "Wembley Stadium"],
    "s_campnou":    ["Camp Nou interior", "Camp Nou"],
    "s_bernabeu":   ["Santiago Bernabéu Stadium interior", "Estadio Santiago Bernabéu"],
    "s_sansiro": ["San Siro stadium exterior towers", "Stadio San Siro Milano esterno"],
    "s_anfield":    ["Anfield stadium", "Anfield Liverpool"],
    "s_oldtrafford": ["Old Trafford stadium stands pitch", "Old Trafford interior panorama"],
    "s_allianzarena":["Allianz Arena Munich", "Allianz Arena"],
    "s_azteca":     ["Estadio Azteca", "Estadio Azteca interior"],
    "s_bombonera": ["La Bombonera stands interior match", "Estadio La Bombonera tribunas"],
    "s_monumental": ["Estadio Monumental River Plate", "Estadio Mâs Monumental"],
    "s_centenario": ["Estadio Centenario Montevideo"],
    "s_luzhniki":   ["Luzhniki Stadium", "Luzhniki Stadium interior"],
    "s_metlife":    ["MetLife Stadium"],
    "s_lusail":     ["Lusail Stadium"],
    "s_olympiaberlin":["Olympiastadion Berlin"],
    "s_stadedefrance":["Stade de France"],
    "s_rosebowl":   ["Rose Bowl stadium Pasadena"],
    "s_soccercity": ["Soccer City stadium Johannesburg", "FNB Stadium"],
    "s_signaliduna":["Signal Iduna Park", "Westfalenstadion"],
    "s_parcdesprinces":["Parc des Princes"],
    "s_luz": ["Estádio da Luz interior 2014", "Estadio da Luz Lisbon stadium"],
    "s_dekuip":     ["De Kuip Rotterdam stadium"],
    "s_johancruyff":["Johan Cruyff Arena", "Amsterdam Arena"],
    "s_velodrome":  ["Stade Vélodrome Marseille"],
    "s_olimpico":   ["Stadio Olimpico Rome"],
    "s_ataturk":    ["Atatürk Olympic Stadium"],
    "s_hampden": ["Hampden Park interior", "Hampden Park stands pitch Glasgow"],
    "s_stamford":   ["Stamford Bridge stadium Chelsea"],
    "s_emirates":   ["Emirates Stadium Arsenal"],
    "s_ibrox": ["Ibrox Stadium interior stands", "Ibrox Stadium Glasgow exterior"],
    "s_mestalla": ["Mestalla stadium exterior", "Estadio de Mestalla Valencia exterior"],
    "g_ball": ["association football ball on grass", "soccer ball grass pitch"],
    "g_referee":    ["football referee yellow card", "referee showing card football"],
}

def api(params):
    u = "https://commons.wikimedia.org/w/api.php?format=json&formatversion=2&" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60).read())
        except Exception:
            time.sleep(3 + attempt * 3)
    return {}

def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=90).read()

def clean(x):
    return re.sub(r"<[^>]+>", "", x or "").strip()

def pick(query):
    d = api({"action": "query", "generator": "search", "gsrnamespace": 6, "gsrsearch": query, "gsrlimit": 15,
             "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 720})
    pages = (d.get("query") or {}).get("pages") or []
    pages.sort(key=lambda p: p.get("index", 99))
    words = [w for w in re.findall(r"[a-zà-ÿ]+", query.lower()) if len(w) > 2]
    best = None
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        title = p.get("title", "")
        if ii.get("mime") not in ("image/jpeg", "image/png") or SKIP.search(title):
            continue
        if (ii.get("width") or 0) < 800 or (ii.get("height") or 0) < 500:
            continue
        md = ii.get("extmetadata") or {}
        lic = clean((md.get("LicenseShortName") or {}).get("value"))
        if not FREE.search(lic) or BAD.search(lic):
            continue
        score = sum(1 for w in words if w in title.lower()) - p.get("index", 0) * 0.1
        if best is None or score > best[0]:
            best = (score, p, ii, lic, clean((md.get("Artist") or {}).get("value")) or "Desconhecido")
    return best

def main():
    out_path = sys.argv[1]
    keys = sys.argv[2:] or list(WANT)
    out = json.load(io.open(out_path)) if os.path.exists(out_path) else {}
    for key in keys:
        if key in out:
            continue
        got = None
        for q in WANT[key]:
            got = pick(q)
            time.sleep(0.6)
            if got:
                break
        if not got:
            print(f"  -- {key}: nothing free"); continue
        _, p, ii, lic, author = got
        src = ii.get("thumburl") or ii.get("url")
        fn = "img/" + hashlib.sha1(src.encode()).hexdigest()[:16] + ".webp"
        fp = os.path.join(ROOT, fn)
        if not os.path.exists(fp):
            im = Image.open(io.BytesIO(get(src))).convert("RGB")
            if im.width > 640:
                im = im.resize((640, round(im.height * 640 / im.width)), Image.LANCZOS)
            im.save(fp, "WEBP", quality=80, method=6)
        out[key] = {"img": fn, "file": p["title"].replace("File:", ""), "author": author[:120], "license": lic,
                    "url": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(p["title"].replace(" ", "_"))}
        print(f"  ok {key:16s} {fn}  [{lic}]  {p['title'][:70]}")
        json.dump(out, io.open(out_path, "w"), ensure_ascii=False, indent=1)
        time.sleep(0.8)

main()
