#!/usr/bin/env python3
"""Retry the players whose Wikipedia titles resolved to no image."""
import importlib.util, os, sys, io, json

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fp", os.path.join(HERE, "fetch_players.py"))

# reuse helpers without executing main(): read + exec only the top section
src = io.open(os.path.join(HERE, "fetch_players.py"), encoding="utf-8").read()
src = src.split("def main():")[0]
ns = {"__name__": "fp", "__file__": os.path.join(HERE, "fetch_players.py")}
exec(compile(src, "fetch_players.py", "exec"), ns)

RETRY = [
 ("lucio","Lúcio","pt:Lucimar da Silva Ferreira","DF",(1997,2020),"BRA",["internacional","leverkusen","bayern","inter"]),
 ("junior","Júnior","pt:Leovegildo Lins da Gama Júnior","DF",(1974,1993),"BRA",["flamengo","torino","pescara"]),
 ("gerson","Gérson","pt:Gérson de Oliveira Nunes","MF",(1959,1977),"BRA",["flamengo","botafogo","saopaulo","fluminense"]),
 ("xavi","Xavi","en:Xavi Hernandez","MF",(1998,2019),"ESP",["barcelona","alsadd"]),
 ("careca","Careca","pt:Careca (futebolista)","FW",(1978,1997),"BRA",["guarani","saopaulo","napoli"]),
 ("edmundo","Edmundo","pt:Edmundo Alves de Souza Neto","FW",(1988,2008),"BRA",["vasco","palmeiras","flamengo","fiorentina","corinthians","santos"]),
 # a few extra names worth having
 ("zagallo","Zagallo","pt:Mário Jorge Lobo Zagallo","FW",(1950,1965),"BRA",["flamengo","botafogo"]),
 ("vava","Vavá","pt:Vavá","FW",(1951,1970),"BRA",["vasco","atleticomg","palmeiras"]),
 ("didi","Didi","pt:Didi (futebolista)","MF",(1946,1966),"BRA",["botafogo","realmadrid","fluminense","sport"]),
 ("nilton_santos","Nílton Santos","pt:Nílton Santos","DF",(1948,1964),"BRA",["botafogo"]),
]

ROOT = ns["ROOT"]; DATA = ns["DATA"]; FLAG = ns["FLAG"]
import re, time, hashlib, os.path as op
out_path = op.join(DATA, "players_extra.json")
cred_path = op.join(DATA, "credits.json")
players = json.load(io.open(out_path))
credits = json.load(io.open(cred_path))

added = failed = 0
for (pid, disp, wiki, pos, era, ctry, clubs) in RETRY:
    if pid in players:
        print(f"  .. {pid} already present"); continue
    lang, title = wiki.split(":", 1)
    try:
        s = ns["summary"](lang, title)
        src_url = (s.get("thumbnail") or {}).get("source") or (s.get("originalimage") or {}).get("source")
        if not src_url:
            print(f"  -- {pid}: still no image"); failed += 1; time.sleep(1.2); continue
        if "/wikipedia/commons/" not in src_url:
            print(f"  XX {pid}: non-free, skipped"); failed += 1; time.sleep(1.2); continue
        src_url = re.sub(r"/\d+px-", "/330px-", src_url)
        ext = op.splitext(src_url)[1].lower() or ".jpg"
        if ext not in (".jpg", ".jpeg", ".png"): ext = ".jpg"
        fn = "img/" + hashlib.sha1(src_url.encode()).hexdigest()[:16] + ext
        fp = op.join(ROOT, fn)
        if not op.exists(fp):
            io.open(fp, "wb").write(ns["get"](src_url))
        lic = ns["license_for"](src_url)
        if lic: credits[fn] = lic
        players[pid] = {"id": pid, "n": disp, "nat": FLAG.get(ctry, "🏳"), "img": fn,
                        "pos": pos, "era": list(era), "ctry": ctry, "clubs": clubs}
        added += 1
        print(f"  ok {pid:15s} {pos} {fn}  [{(lic or {}).get('license','?')}]")
    except Exception as e:
        print(f"  !! {pid}: {str(e)[:70]}"); failed += 1
    time.sleep(1.2)

json.dump(players, io.open(out_path, "w"), ensure_ascii=False, indent=1)
json.dump(credits, io.open(cred_path, "w"), ensure_ascii=False, indent=1)
print(f"\nadded={added} failed={failed} total={len(players)}")
