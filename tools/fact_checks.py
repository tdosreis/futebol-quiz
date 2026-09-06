#!/usr/bin/env python3
"""The claims a number-scanner cannot check: associations and superlatives.

tools/audit_questions.py catches questions asserting a year or a count. The rest
assert that a thing is associated with another thing — "Sócrates liderou a
Democracia Corinthiana em qual clube?", "Qual clube carioca é o Gigante da
Colina?" — or make a superlative claim with no number in it, which is where this
kind of error usually hides.

Those cannot be derived, so they are listed by hand: each claim names the exact
article that would settle it and the terms that must appear in it. Adding a
question of that kind means adding a row here.

  python3 tools/fact_checks.py      # exits non-zero if any claim fails

Last full run: 61/61 confirmed. The only error the whole audit found was
elsewhere — "maior artilheiro da Seleção Brasileira" answered Neymar where Marta
holds the record across both teams; it now says "masculina".
"""
import json,urllib.request,urllib.parse,unicodedata,time,sys
UA="FutebolQuizBR/1.2 (https://tdosreis.github.io/futebol-quiz/; tiagor.reis@gmail.com)"
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA}),timeout=60).read()
def japi(u): return json.loads(get(u).decode())
CACHE={}
def art(lang,title):
    k=(lang,title)
    if k in CACHE: return CACHE[k]
    try:
        d=japi(f"https://{lang}.wikipedia.org/w/api.php?format=json&action=query&prop=extracts&explaintext=1"
               f"&redirects=1&titles={urllib.parse.quote(title)}")
        t=(list(d["query"]["pages"].values())[0].get("extract","") or "")
    except Exception: t=""
    CACHE[k]=t; time.sleep(0.2); return t
def fold(x): return ''.join(c for c in unicodedata.normalize('NFD',str(x).lower()) if unicodedata.category(c)!='Mn')

# (label, lang, article, [terms that must all appear])
C=[
 ("Pelé -> Santos","pt","Pelé",["santos"]),
 ("Garrincha -> Botafogo","pt","Garrincha",["botafogo"]),
 ("Kaká -> São Paulo","pt","Kaká",["sao paulo"]),
 ("Ronaldo -> Cruzeiro","pt","Ronaldo Nazário",["cruzeiro"]),
 ("Sócrates -> Democracia Corinthiana","pt","Sócrates (futebolista)",["democracia corinthiana","corinthians"]),
 ("Sport -> leão","pt","Sport Club do Recife",["leao"]),
 ("Vasco -> Gigante da Colina","pt","Club de Regatas Vasco da Gama",["gigante da colina"]),
 ("Atlético-MG -> Galo","pt","Clube Atlético Mineiro",["galo"]),
 ("Santos -> Peixe","pt","Santos Futebol Clube",["peixe"]),
 ("Coritiba -> Coxa","pt","Coritiba Foot Ball Club",["coxa"]),
 ("Corinthians -> Timão","pt","Sport Club Corinthians Paulista",["timao"]),
 ("Allianz Parque -> Palmeiras","pt","Allianz Parque",["palmeiras"]),
 ("Neo Química Arena -> Corinthians","pt","Neo Química Arena",["corinthians"]),
 ("Beira-Rio -> Internacional","pt","Estádio Beira-Rio",["internacional"]),
 ("Vila Belmiro -> Santos","pt","Estádio Urbano Caldeira",["santos"]),
 ("São Januário -> Vasco","pt","Estádio São Januário",["vasco"]),
 ("Arena do Grêmio -> Grêmio","pt","Arena do Grêmio",["gremio"]),
 ("Maracanã -> Flamengo+Fluminense","pt","Estádio do Maracanã",["flamengo","fluminense"]),
 ("Mineirão -> Cruzeiro+Atlético","pt","Estádio Governador Magalhães Pinto",["cruzeiro","atletico"]),
 ("Morumbi -> São Paulo","pt","Estádio do Morumbi",["sao paulo"]),
 ("Fonte Nova -> Bahia","pt","Arena Fonte Nova",["bahia"]),
 ("Couto Pereira -> Coritiba","pt","Estádio Major Antônio Couto Pereira",["coritiba"]),
 ("Arruda -> Santa Cruz","pt","Estádio José do Rego Maciel",["santa cruz"]),
 ("Nílton Santos -> Enciclopédia","pt","Nílton Santos",["enciclopedia"]),
 ("Coutinho -> Santos com Pelé","pt","Coutinho (futebolista)",["santos","pele"]),
 ("Pepe -> Santos toda a carreira","pt","Pepe (futebolista brasileiro)",["santos"]),
 ("Casagrande -> Democracia Corinthiana","pt","Walter Casagrande Júnior",["corinthians"]),
 ("Chilavert -> faltas e pênaltis","es","José Luis Chilavert",["penal"]),
 ("Valderrama -> capitão 3 Copas","es","Carlos Valderrama",["1990","1994","1998"]),
 ("Francescoli -> River + Marseille","es","Enzo Francescoli",["river plate","marsella"]),
 ("Reinaldo -> lesões no joelho","pt","José Reinaldo de Lima",["joelho"]),
 ("Cruyff -> a finta","en","Cruyff Turn",["cruyff"]),
 ("Charles Miller -> pai do futebol BR","pt","Charles Miller",["futebol"]),
 ("FIFA fundada 1904 Paris","pt","FIFA",["1904","paris"]),
 ("pênaltis introduzidos 1891","en","Penalty kick (association football)",["1891"]),
 ("Laranja Mecânica","pt","Seleção Neerlandesa de Futebol",["laranja mecanica"]),
 ("10 de linha + goleiro","en","Laws of the Game (association football)",["eleven"]),
 ("substituições em Copas 1970","en","Substitute (association football)",["1970"]),
 ("Copa com 32 seleções em 1998","en","FIFA World Cup",["1998","32"]),
 ("grande área 16,5 m","en","Penalty area",["16.5"]),
 ("El Clásico","en","El Clásico",["real madrid","barcelona"]),
 ("Derby della Madonnina","en","Derby della Madonnina",["inter","milan"]),
 ("Old Firm","en","Old Firm",["celtic","rangers"]),
 ("Tiki-taka -> Guardiola/Barça","en","Tiki-taka",["barcelona"]),
 ("Bernabéu -> Real Madrid","en","Santiago Bernabéu Stadium",["real madrid"]),
 ("Camp Nou -> Barcelona","en","Camp Nou",["barcelona"]),
 ("San Siro -> Milan + Inter","en","San Siro",["milan","inter"]),
 ("Anfield -> YNWA","en","Anfield",["you'll never walk alone"]),
 ("Old Trafford -> Man United","en","Old Trafford",["manchester united"]),
 ("Signal Iduna Park -> Dortmund","en","Westfalenstadion",["dortmund","yellow wall"]),
 ("Galatasaray -> Ali Sami Yen inferno","en","Ali Sami Yen Stadium",["hell"]),
 ("Jupiler Pro League -> Bélgica","en","Belgian Pro League",["belgium"]),
 ("Superclásico -> Boca x River","en","Superclásico",["boca","river"]),
 ("Mourinho -> UCL Porto e Inter","en","José Mourinho",["porto","inter"]),
 ("Klopp -> gegenpressing Liverpool","en","Jürgen Klopp",["liverpool","gegenpressing"]),
 ("Brasil 5 Copas","pt","Seleção Brasileira de Futebol",["cinco"]),
 ("camisa branca abandonada apos 1950","pt","Uniformes da Seleção Brasileira de Futebol",["1950","aposentada"]),
 ("Roberto Carlos -> faltas","pt","Roberto Carlos da Silva",["falta"]),
 ("Ibrahimović -> títulos em 4 países","en","Zlatan Ibrahimović",["ajax","juventus","barcelona","paris saint-germain"]),
 ("Beckham -> cobranças de falta","en","David Beckham",["free-kick"]),
 ("Henry -> 4x artilheiro da PL","en","Thierry Henry",["golden boot"]),
 # ── Da Arquibancada: os clássicos, os mascotes, os apelidos ──
 ("Clássico dos Milhões = Fla x Vasco","pt","Clássico dos Milhões",["flamengo","vasco"]),
 ("Fla-Flu","pt","Fla-Flu",["flamengo","fluminense"]),
 ("Grenal","pt","Gre-Nal",["gremio","internacional"]),
 ("Derby Paulista = Cor x Pal","pt","Derby Paulista",["corinthians","palmeiras"]),
 ("Choque-Rei = SP x Pal","pt","Choque-Rei",["sao paulo","palmeiras"]),
 ("Majestoso = Cor x SP","pt","Clássico Majestoso",["corinthians","sao paulo"]),
 ("San-São = Santos x SP","pt","San-São",["santos","sao paulo"]),
 ("Clássico Mineiro","pt","Clássico Mineiro",["cruzeiro","atletico"]),
 ("Ba-Vi","pt","Ba-Vi",["bahia","vitoria"]),
 ("Flamengo urubu","pt","Clube de Regatas do Flamengo",["urubu"]),
 ("Palmeiras porco","pt","Sociedade Esportiva Palmeiras",["porco"]),
 ("Corinthians mosqueteiro","pt","Sport Club Corinthians Paulista",["mosqueteiro"]),
 ("Cruzeiro raposa","pt","Cruzeiro Esporte Clube",["raposa"]),
 ("Palmeiras Verdão","pt","Sociedade Esportiva Palmeiras",["verdao"]),
 ("Internacional Colorado","pt","Sport Club Internacional",["colorado"]),
 ("Grêmio Imortal","pt","Grêmio Foot-Ball Porto Alegrense",["imortal"]),
 ("Ceará Vozão","pt","Ceará Sporting Club",["vozao"]),
 ("Fortaleza Leão do Pici","pt","Fortaleza Esporte Clube",["pici"]),
 ("Bahia Esquadrão de Aço","pt","Esporte Clube Bahia",["esquadrao"]),
 ("Athletico Furacão","pt","Club Athletico Paranaense",["furacao"]),
 ("Avaí Leão da Ilha","pt","Avaí Futebol Clube",["leao da ilha"]),
 ("Paysandu Papão da Curuzu","pt","Paysandu Sport Club",["papao"]),
 ("Fluminense Laranjeiras","pt","Fluminense Football Club",["laranjeiras"]),
 # ── futebol feminino e a era moderna ──
 ("1a Copa Feminina em 1991","en","1991 FIFA Women's World Cup",["1991"]),
 ("EUA maior campeã feminina","en","FIFA Women's World Cup",["united states"]),
 ("Espanha campeã 2023","en","2023 FIFA Women's World Cup",["spain"]),
 ("Brasil sedia a Copa Feminina de 2027","en","2027 FIFA Women's World Cup",["brazil"]),
 # note: the English "Formiga (footballer)" is a disambiguation page — use pt.
 ("Formiga em 7 Copas","pt","Formiga (futebolista)",["7 copas"]),
 ("Argentina campeã 2022","pt","Copa do Mundo FIFA de 2022",["argentina"]),
 ("Marrocos na semifinal de 2022","en","2022 FIFA World Cup",["morocco"]),
 ("Mbappé hat-trick na final de 2022","en","2022 FIFA World Cup final",["hat-trick"]),
 ("Copa 2026: EUA, Canadá, México, 48","en","2026 FIFA World Cup",["mexico","canada","48"]),
 ("Mundial de Clubes com 32 em 2025","en","2025 FIFA Club World Cup",["32"]),
]
bad=[]
for label,lang,title,terms in C:
    t=fold(art(lang,title))
    if not t: bad.append((label,"article empty: "+title)); print(f"  ??  {label:40s} article empty ({title})"); continue
    miss=[x for x in terms if fold(x) not in t]
    if miss: bad.append((label,"missing "+str(miss))); print(f"  ??  {label:40s} missing {miss}")
    else: print(f"  OK  {label:40s}")
print(f"\n{len(C)-len(bad)} of {len(C)} claims confirmed against Wikipedia")
if bad:
    print("  unresolved:")
    for label, why in bad: print(f"    {label}: {why}")
sys.exit(1 if bad else 0)
