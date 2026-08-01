#!/usr/bin/env python3
"""Fetch freely-licensed (Wikimedia Commons ONLY) player photos + license metadata.

Rules enforced:
  * only images served from /wikipedia/commons/  (non-free /wikipedia/en/ files rejected)
  * author + license captured for every file so the app can attribute properly
Outputs data/players_extra.json and data/credits.json
"""
import json, os, io, re, time, hashlib, urllib.request, urllib.parse, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IMG = os.path.join(ROOT, "img")
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)

UA = "FutebolQuizBR/1.1 (https://tdosreis.github.io/futebol-quiz/; tiagor.reis@gmail.com)"

FLAG = {
 'BRA':'🇧🇷','ARG':'🇦🇷','POR':'🇵🇹','FRA':'🇫🇷','NED':'🇳🇱','GER':'🇩🇪','BUL':'🇧🇬',
 'ITA':'🇮🇹','ENG':'🏴󠁧󠁢󠁥󠁮󠁧󠁿','SWE':'🇸🇪','POL':'🇵🇱','CIV':'🇨🇮','LBR':'🇱🇷','CRO':'🇭🇷',
 'COL':'🇨🇴','ESP':'🇪🇸','URU':'🇺🇾','EGY':'🇪🇬','NOR':'🇳🇴','CMR':'🇨🇲','UKR':'🇺🇦',
 'HUN':'🇭🇺','BEL':'🇧🇪','CZE':'🇨🇿','DEN':'🇩🇰','RUS':'🇷🇺','MEX':'🇲🇽','CHI':'🇨🇱','GHA':'🇬🇭',
}

# id, display, wiki(lang:title), pos, era, ctry, clubs
P = [
 # ── GOLEIROS (the big gap) ──
 ("dida","Dida","pt:Dida (futebolista)","GK",(1992,2015),"BRA",["cruzeiro","milan","corinthians","gremio"]),
 ("rogerio_ceni","Rogério Ceni","pt:Rogério Ceni","GK",(1990,2015),"BRA",["saopaulo"]),
 ("marcos","Marcos","pt:Marcos (futebolista)","GK",(1992,2012),"BRA",["palmeiras"]),
 ("julio_cesar","Júlio César","pt:Júlio César Soares Espíndola","GK",(1997,2018),"BRA",["flamengo","inter","benfica"]),
 ("alisson","Alisson","pt:Alisson Becker","GK",(2013,2026),"BRA",["internacional","roma","liverpool"]),
 ("ederson","Ederson","pt:Ederson Santana de Moraes","GK",(2012,2026),"BRA",["benfica","mancity"]),
 ("leao","Emerson Leão","pt:Emerson Leão","GK",(1965,1985),"BRA",["palmeiras","gremio","corinthians","sport"]),
 ("buffon","Gianluigi Buffon","en:Gianluigi Buffon","GK",(1995,2023),"ITA",["parma","juventus","psg"]),
 ("casillas","Iker Casillas","en:Iker Casillas","GK",(1999,2020),"ESP",["realmadrid","porto"]),
 ("neuer","Manuel Neuer","en:Manuel Neuer","GK",(2006,2026),"GER",["schalke","bayern"]),
 ("kahn","Oliver Kahn","en:Oliver Kahn","GK",(1987,2008),"GER",["karlsruher","bayern"]),
 ("van_der_sar","Van der Sar","en:Edwin van der Sar","GK",(1990,2011),"NED",["ajax","juventus","fulham","manutd"]),
 ("schmeichel","Peter Schmeichel","en:Peter Schmeichel","GK",(1981,2003),"DEN",["brondby","manutd","mancity"]),
 ("cech","Petr Čech","en:Petr Čech","GK",(1999,2019),"CZE",["rennes","chelsea","arsenal"]),
 ("courtois","Thibaut Courtois","en:Thibaut Courtois","GK",(2009,2026),"BEL",["genk","chelsea","atletico","realmadrid"]),
 ("yashin","Lev Yashin","en:Lev Yashin","GK",(1950,1970),"RUS",["dinamomoscow"]),
 # ── DEFENSORES ──
 ("thiago_silva","Thiago Silva","pt:Thiago Silva","DF",(2004,2026),"BRA",["fluminense","milan","psg","chelsea"]),
 ("lucio","Lúcio","pt:Lúcio","DF",(1997,2020),"BRA",["internacional","leverkusen","bayern","inter"]),
 ("aldair","Aldair","pt:Aldair","DF",(1985,2004),"BRA",["flamengo","benfica","roma"]),
 ("marcelo","Marcelo","pt:Marcelo Vieira","DF",(2005,2026),"BRA",["fluminense","realmadrid","olympiacos"]),
 ("dani_alves","Daniel Alves","pt:Daniel Alves","DF",(2001,2023),"BRA",["bahia","sevilla","barcelona","juventus","psg","saopaulo"]),
 ("junior","Júnior","pt:Júnior (futebolista)","DF",(1974,1993),"BRA",["flamengo","torino","pescara"]),
 ("marquinhos","Marquinhos","pt:Marcos Aoás Corrêa","DF",(2012,2026),"BRA",["corinthians","roma","psg"]),
 ("david_luiz","David Luiz","pt:David Luiz","DF",(2006,2026),"BRA",["vitoria","benfica","chelsea","psg","arsenal","flamengo"]),
 ("maicon","Maicon","pt:Maicon Douglas Sisenando","DF",(2001,2020),"BRA",["cruzeiro","monaco","inter","roma"]),
 ("maldini","Paolo Maldini","en:Paolo Maldini","DF",(1984,2009),"ITA",["milan"]),
 ("baresi","Franco Baresi","en:Franco Baresi","DF",(1977,1997),"ITA",["milan"]),
 ("nesta","Alessandro Nesta","en:Alessandro Nesta","DF",(1993,2014),"ITA",["lazio","milan"]),
 ("sergio_ramos","Sergio Ramos","en:Sergio Ramos","DF",(2003,2026),"ESP",["sevilla","realmadrid","psg"]),
 ("puyol","Carles Puyol","en:Carles Puyol","DF",(1999,2014),"ESP",["barcelona"]),
 ("beckenbauer","Beckenbauer","en:Franz Beckenbauer","DF",(1964,1983),"GER",["bayern","cosmos"]),
 ("cannavaro","Fabio Cannavaro","en:Fabio Cannavaro","DF",(1992,2011),"ITA",["napoli","parma","inter","juventus","realmadrid"]),
 ("van_dijk","Virgil van Dijk","en:Virgil van Dijk","DF",(2011,2026),"NED",["celtic","southampton","liverpool"]),
 ("lahm","Philipp Lahm","en:Philipp Lahm","DF",(2002,2017),"GER",["bayern","stuttgart"]),
 # ── MEIAS ──
 ("rivellino","Rivellino","pt:Rivellino","MF",(1965,1981),"BRA",["corinthians","fluminense"]),
 ("gerson","Gérson","pt:Gérson","MF",(1959,1977),"BRA",["flamengo","botafogo","saopaulo","fluminense"]),
 ("dunga","Dunga","pt:Dunga","MF",(1980,2000),"BRA",["internacional","fiorentina","pescara","stuttgart"]),
 ("juninho","Juninho Pernambucano","pt:Juninho Pernambucano","MF",(1993,2013),"BRA",["vasco","lyon","alsadd"]),
 ("gilberto_silva","Gilberto Silva","pt:Gilberto Silva","MF",(1997,2013),"BRA",["atleticomg","arsenal","panathinaikos","gremio"]),
 ("emerson","Emerson","pt:Emerson Ferreira da Rosa","MF",(1993,2010),"BRA",["gremio","leverkusen","roma","juventus","realmadrid","milan"]),
 ("alex","Alex","pt:Alex de Souza","MF",(1995,2012),"BRA",["palmeiras","cruzeiro","fenerbahce","coritiba"]),
 ("diego","Diego","pt:Diego Ribas da Cunha","MF",(2002,2021),"BRA",["santos","porto","werder","juventus","flamengo"]),
 ("casemiro","Casemiro","pt:Casemiro","MF",(2010,2026),"BRA",["saopaulo","realmadrid","manutd"]),
 ("xavi","Xavi","en:Xavi","MF",(1998,2019),"ESP",["barcelona","alsadd"]),
 ("iniesta","Andrés Iniesta","en:Andrés Iniesta","MF",(2002,2024),"ESP",["barcelona","vissel"]),
 ("pirlo","Andrea Pirlo","en:Andrea Pirlo","MF",(1995,2017),"ITA",["brescia","inter","milan","juventus","nycfc"]),
 ("gerrard","Steven Gerrard","en:Steven Gerrard","MF",(1998,2016),"ENG",["liverpool","lagalaxy"]),
 ("lampard","Frank Lampard","en:Frank Lampard","MF",(1995,2016),"ENG",["westham","chelsea","mancity","nycfc"]),
 ("scholes","Paul Scholes","en:Paul Scholes","MF",(1993,2013),"ENG",["manutd"]),
 ("kroos","Toni Kroos","en:Toni Kroos","MF",(2007,2024),"GER",["bayern","leverkusen","realmadrid"]),
 ("de_bruyne","Kevin De Bruyne","en:Kevin De Bruyne","MF",(2008,2026),"BEL",["genk","chelsea","wolfsburg","mancity"]),
 ("riquelme","Riquelme","en:Juan Román Riquelme","MF",(1996,2014),"ARG",["boca","barcelona","villarreal","argentinos"]),
 ("nedved","Pavel Nedvěd","en:Pavel Nedvěd","MF",(1991,2009),"CZE",["sparta","lazio","juventus"]),
 ("figo","Luís Figo","en:Luís Figo","MF",(1989,2009),"POR",["sporting","barcelona","realmadrid","inter"]),
 # ── ATACANTES ──
 ("careca","Careca","pt:Careca","FW",(1978,1997),"BRA",["guarani","saopaulo","napoli"]),
 ("tostao","Tostão","pt:Tostão","FW",(1963,1973),"BRA",["cruzeiro","vasco"]),
 ("edmundo","Edmundo","pt:Edmundo","FW",(1988,2008),"BRA",["vasco","palmeiras","flamengo","fiorentina","corinthians","santos"]),
 ("robinho","Robinho","pt:Robinho","FW",(2002,2020),"BRA",["santos","realmadrid","mancity","milan"]),
 ("hulk","Hulk","pt:Hulk (futebolista)","FW",(2004,2026),"BRA",["porto","zenit","atleticomg"]),
 ("luis_fabiano","Luís Fabiano","pt:Luís Fabiano","FW",(1997,2018),"BRA",["saopaulo","porto","sevilla","vasco"]),
 ("suarez","Luis Suárez","en:Luis Suárez","FW",(2005,2026),"URU",["ajax","liverpool","barcelona","atletico","gremio","intermiami"]),
 ("cavani","Edinson Cavani","en:Edinson Cavani","FW",(2006,2026),"URU",["palermo","napoli","psg","manutd","boca"]),
 ("salah","Mohamed Salah","en:Mohamed Salah","FW",(2010,2026),"EGY",["basel","chelsea","roma","liverpool"]),
 ("haaland","Erling Haaland","en:Erling Haaland","FW",(2016,2026),"NOR",["salzburg","dortmund","mancity"]),
 ("kane","Harry Kane","en:Harry Kane","FW",(2011,2026),"ENG",["tottenham","bayern"]),
 ("aguero","Sergio Agüero","en:Sergio Agüero","FW",(2003,2021),"ARG",["independiente","atletico","mancity","barcelona"]),
 ("etoo","Samuel Eto'o","en:Samuel Eto'o","FW",(1997,2019),"CMR",["realmadrid","mallorca","barcelona","inter","chelsea"]),
 ("shevchenko","Shevchenko","en:Andriy Shevchenko","FW",(1994,2012),"UKR",["dynamokyiv","milan","chelsea"]),
 ("raul","Raúl","en:Raúl (footballer)","FW",(1994,2015),"ESP",["realmadrid","schalke","cosmos"]),
 ("del_piero","Del Piero","en:Alessandro Del Piero","FW",(1991,2014),"ITA",["padova","juventus","sydney"]),
 ("totti","Francesco Totti","en:Francesco Totti","FW",(1992,2017),"ITA",["roma"]),
 ("rooney","Wayne Rooney","en:Wayne Rooney","FW",(2002,2021),"ENG",["everton","manutd","dcunited"]),
 ("owen","Michael Owen","en:Michael Owen","FW",(1996,2013),"ENG",["liverpool","realmadrid","newcastle","manutd"]),
 ("puskas","Ferenc Puskás","en:Ferenc Puskás","FW",(1943,1966),"HUN",["honved","realmadrid"]),
 ("distefano","Di Stéfano","en:Alfredo Di Stéfano","FW",(1945,1966),"ARG",["riverplate","millonarios","realmadrid","espanyol"]),
 ("eusebio","Eusébio","en:Eusébio","FW",(1957,1979),"POR",["benfica"]),
 ("gerd_muller","Gerd Müller","en:Gerd Müller","FW",(1963,1981),"GER",["bayern","fortlauderdale"]),
 ("charlton","Bobby Charlton","en:Bobby Charlton","FW",(1956,1975),"ENG",["manutd","prestonne"]),
]

def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout).read()

def summary(lang, title):
    u = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title.replace(' ','_'))}"
    return json.loads(get(u))

def license_for(file_url):
    """Look up author + license for a Commons file from its upload URL."""
    m = re.search(r"/commons/(?:thumb/)?[0-9a-f]/[0-9a-f]{2}/([^/]+)", file_url)
    if not m: return None
    fname = urllib.parse.unquote(m.group(1))
    api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
           "&prop=imageinfo&iiprop=extmetadata&titles=" + urllib.parse.quote("File:" + fname))
    try:
        d = json.loads(get(api))
        pages = d.get("query", {}).get("pages", {})
        for _, pg in pages.items():
            ii = (pg.get("imageinfo") or [{}])[0].get("extmetadata", {})
            def v(k):
                x = ii.get(k, {}).get("value", "")
                return re.sub(r"<[^>]+>", "", x).strip()
            return {"file": fname, "author": v("Artist") or "Desconhecido",
                    "license": v("LicenseShortName") or "?",
                    "url": "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(fname)}
    except Exception:
        return None
    return None

def main():
    out_path = os.path.join(DATA, "players_extra.json")
    cred_path = os.path.join(DATA, "credits.json")
    players = json.load(io.open(out_path)) if os.path.exists(out_path) else {}
    credits = json.load(io.open(cred_path)) if os.path.exists(cred_path) else {}

    added = skipped = failed = nonfree = 0
    for (pid, disp, wiki, pos, era, ctry, clubs) in P:
        if pid in players:
            skipped += 1; continue
        lang, title = wiki.split(":", 1)
        try:
            s = summary(lang, title)
            src = (s.get("thumbnail") or {}).get("source") or \
                  (s.get("originalimage") or {}).get("source")
            if not src:
                print(f"  -- {pid}: no image"); failed += 1; time.sleep(1.0); continue
            if "/wikipedia/commons/" not in src:
                print(f"  XX {pid}: NON-FREE image, skipping ({src.split('/')[4]})")
                nonfree += 1; time.sleep(1.0); continue
            # normalise to a reasonable width
            src = re.sub(r"/\d+px-", "/330px-", src)
            ext = os.path.splitext(src)[1].lower() or ".jpg"
            if ext not in (".jpg", ".jpeg", ".png"): ext = ".jpg"
            fn = "img/" + hashlib.sha1(src.encode()).hexdigest()[:16] + ext
            fp = os.path.join(ROOT, fn)
            if not os.path.exists(fp):
                data = get(src)
                io.open(fp, "wb").write(data)
            lic = license_for(src)
            if lic: credits[fn] = lic
            players[pid] = {"id": pid, "n": disp, "nat": FLAG.get(ctry, "🏳"),
                            "img": fn, "pos": pos, "era": list(era),
                            "ctry": ctry, "clubs": clubs}
            added += 1
            print(f"  ok {pid:16s} {pos} {fn}  [{(lic or {}).get('license','?')}]")
        except Exception as e:
            print(f"  !! {pid}: {str(e)[:70]}"); failed += 1
        time.sleep(1.2)   # be polite to Wikimedia

    json.dump(players, io.open(out_path, "w"), ensure_ascii=False, indent=1)
    json.dump(credits, io.open(cred_path, "w"), ensure_ascii=False, indent=1)
    print(f"\nadded={added} skipped={skipped} failed={failed} nonfree-rejected={nonfree}")
    print(f"total players in file: {len(players)}")

main()
