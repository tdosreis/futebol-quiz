#!/usr/bin/env python3
"""Render specific game states to PNG so changes can be eyeballed."""
import subprocess, os, io, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT = os.path.join(ROOT, "store-assets")

# name -> JS to run once the page has booted
STATES = {

 # ── The six phone screenshots on the Play listing ──────────────
 # They have to carry the story in order: what the app is, that the clubs
 # and the players are really in it, that there is an album to fill, that a
 # wrong answer teaches you something, and that the million is the point.
 #   THEME=light python3 tools/shots.py shot-01-home shot-02-crests \
 #     shot-03-question shot-04-album shot-05-ficha shot-06-milhao

 "shot-01-home": """album=new Set(PL.slice(0,58).map(p=>p.id)); LS.set('album',[...album]);
   stats={games:37,correct:412,answered:560,bestStreak:9,perfect:3,hard80:2,survBest:11};
   LS.set('stats',stats); LS.set('milBest',150000);
   heroSticker=function(){ const h=PL.find(p=>p.id==='pele'); return {p:h,num:PL.indexOf(h)+1}; };
   sc='home'; go();""",

 "shot-02-crests": """diffKey='moderado'; cat=buildGame('moderado');
   const fq={ t:'Campeão do Brasileirão em 2024?', a:['botafogo'],
     fixed:['botafogo','palmeiras','flamengo','cruzeiro','saopaulo',
            'gremio','corinthians','vasco','santos','atleticomg'] };
   cat.qs=[fq]; qi=0; sel.clear(); pts=48; streak=4; runLog=[3,3,3,1,3];
   sc='quiz'; tMax=25; tLeft=19; disp=getDisp(fq); go();""",

 "shot-03-question": """diffKey='dificil'; cat=buildGame('dificil');
   const fq={ t:'Quem marcou os dois gols do Brasil na final da Copa de 2002?',
     a:['ronaldo'], type:'player',
     fixed:['ronaldo','ronaldinho','rivaldo','bebeto','romario',
            'careca','edmundo','zico','socrates','falcao'] };
   cat.qs=[fq]; qi=0; sel.clear(); pts=72; streak=6; runLog=[3,3,3,3,3,3];
   sc='quiz'; tMax=20; tLeft=14; disp=getDisp(fq); go();""",

 "shot-04-album": """album=new Set(PL.slice(0,22).map(p=>p.id)
     .concat(PL.slice(30,38).map(p=>p.id)).concat(PL.slice(45,52).map(p=>p.id)));
   LS.set('album',[...album]); sc='album'; go();""",

 "shot-05-ficha": """advanceAfterReveal=function(){};
   album=new Set(); diffKey='moderado'; cat=buildGame('moderado');
   const fq={ t:'Quem ganhou a Bola de Ouro em 2007, jogando pelo AC Milan?',
     a:['kaka'], type:'player',
     fixed:['kaka','ronaldinho','pirlo','nedved','shevchenko',
            'figo','totti','del_piero','maldini','nesta'] };
   cat.qs=[fq]; qi=0; disp=getDisp(fq); sel=new Set(['kaka']); tLeft=15; pts=54; doReveal();""",

 "shot-06-milhao": """startMilhao(); rung=11; qi=11; banked=50000;
   cat.qs[11]={ t:'Qual destes jogadores foi campeão do mundo em 1970?',
     a:['jairzinho'], type:'player',
     fixed:['jairzinho','tostao','gerson','rivellino','carlos_alberto',
            'zico','falcao','socrates','junior','dinamite'], _cat:{id:'copa',name:'Copa do Mundo',col:'#2E7D4F'} };
   sel.clear(); sc='quiz'; tMax=qTime(); tLeft=21; disp=getDisp(cat.qs[11]); go();""",


 "s-wrong": """advanceAfterReveal=function(){};
   diffKey='moderado'; startGame();
   const q=cat.qs[0]; const bad=disp.find(o=>!q.a.includes(o.id));
   sel=new Set([bad.id]); tLeft=12; doReveal();""",

 "s-medals": """stats={games:14,correct:132,answered:190,bestStreak:6,perfect:1,hard80:1,survBest:4};
   LS.set('stats',stats); sc='medals'; go();""",
 "s-home2": """stats={games:14,correct:132,answered:190,bestStreak:6,perfect:1,hard80:1,survBest:9};
   LS.set('stats',stats); sc='home'; go();""",
 "s-survival": """startSurvival();""",

 "s-lifelines": """diffKey='moderado'; startGame();
   useHalf();""",
 "s-frozen": """diffKey='moderado'; startGame(); useFreeze();""",

 "s-svgcrest": """diffKey='facil';
   cat = buildGame('facil');
   const fq = { t:'Escudos originais do app (Vasco, Corinthians, Sport, Bragantino, Náutico)',
                a:['vasco'],
                fixed:['vasco','corinthians','sport','bragantino','nautico',
                       'flamengo','palmeiras','santos','gremio','cruzeiro'] };
   cat.qs=[fq]; qi=0; sel.clear(); pts=0; streak=0; runLog=[];
   sc='quiz'; tMax=30; tLeft=25; disp=getDisp(fq); go();""",

 "s-album": """album=new Set(PL.slice(0,46).map(p=>p.id).concat(PL.slice(60,74).map(p=>p.id)));
   LS.set('album',[...album]); sc='album'; go();""",
 "s-back-hit": """advanceAfterReveal=function(){};   /* hold the reveal on screen */
   diffKey='moderado'; startGame();
   const q=cat.qs.find(x=>x.type==='player'&&x.a.length===1)||cat.qs[0];
   qi=cat.qs.indexOf(q); disp=getDisp(q); sel=new Set(q.a); tLeft=14; doReveal();""",
 "s-back-miss": """advanceAfterReveal=function(){};
   diffKey='moderado'; startGame();
   const q=cat.qs.find(x=>x.type==='player'&&x.a.length===1)||cat.qs[0];
   qi=cat.qs.indexOf(q); disp=getDisp(q); album=new Set(PL.map(p=>p.id));
   const bad=disp.find(o=>!q.a.includes(o.id)); sel=new Set([bad.id]); tLeft=9; doReveal();""",
 "s-home2b": """album=new Set(PL.slice(0,52).map(p=>p.id)); LS.set('album',[...album]);
   stats={games:14,correct:132,answered:190,bestStreak:6,perfect:1,hard80:1,survBest:9};
   LS.set('stats',stats); sc='home'; go();""",
 "s-newcrests": """diffKey='facil'; cat=buildGame('facil');
   const ids=['goias','atleticogo','avai','crb','sampaio','botafogosp','santacruz','portuguesa','remo','chapecoense'];
   const fq={ t:'Escudos novos: Goiás, Atlético GO, Avaí, CRB, Sampaio, Botafogo-SP, Santa Cruz, Portuguesa, Remo, Chapecoense',
              a:['goias'], fixed:ids };
   cat.qs=[fq]; qi=0; sel.clear(); sc='quiz'; tMax=30; tLeft=25; disp=getDisp(fq); go();""",
 "s-newcrests2": """diffKey='facil'; cat=buildGame('facil');
   const ids=['cuiaba','csa','abc','juventude','figueirense','paysandu','mirassol','sport','bragantino','nautico'];
   const fq={ t:'Cuiabá, CSA, ABC, Juventude, Figueirense, Paysandu, Mirassol, Sport, Bragantino, Náutico',
              a:['cuiaba'], fixed:ids };
   cat.qs=[fq]; qi=0; sel.clear(); sc='quiz'; tMax=30; tLeft=25; disp=getDisp(fq); go();""",
 "s-newstad": """diffKey='facil'; cat=buildGame('facil');
   const fq={ t:'O Morumbi é o estádio de qual clube paulista?', a:['saopaulo'], stad:'morumbi',
              pool: CL.filter(c=>c.id!=='saopaulo').map(c=>c.id) };
   cat.qs=[fq]; qi=0; sel.clear(); sc='quiz'; tMax=30; tLeft=22; disp=getDisp(fq); go();""",
 "s-home":       "sc='home'; go();",
 "s-difficulty": "sc='difficulty'; go();",
 "s-credits":    "sc='credits'; go();",
 "s-quiz-hard":  "diffKey='dificil'; startGame();",
 "s-reveal": """diffKey='moderado';
   cat = buildGame('moderado');
   const rq = GEN_QS(2).find(q => q.reveal);
   cat.qs = [rq]; qi=0; sel.clear(); pts=0; streak=0; runLog=[];
   sc='quiz'; tMax=25; tLeft=17; disp=getDisp(rq); go();""",
 "s-career": """diffKey='dificil';
   cat = buildGame('dificil');
   const cq = GEN_QS(3).find(q => /nesta ordem/.test(q.t));
   cat.qs = [cq]; qi=0; sel.clear(); pts=0; streak=0; runLog=[];
   sc='quiz'; tMax=20; tLeft=14; disp=getDisp(cq); go();""",
 "s-clubface": """diffKey='moderado';
   cat = buildGame('moderado');
   const fq = GEN_QS(2).find(q => q.face);
   cat.qs=[fq]; qi=0; sel.clear(); pts=0; streak=0; runLog=[];
   sc='quiz'; tMax=25; tLeft=20; disp=getDisp(fq); go();""",
 "s-end": """diffKey='dificil';
   cat = buildGame('dificil'); cat.qs = cat.qs.slice(0,10);
   pts=64; nCorrect=8; nPartial=1; bestStreak=5; streak=5;
   runLog=[3,3,3,0,3,3,1,3,3,3]; scores['dificil']=64;
   stats={games:12,correct:74,answered:110,bestStreak:7};
   sc='end'; go();""",
 "s-combo": """diffKey='dificil'; startGame();
   pts=41; streak=4; prevPts=30;
   sc='reveal'; lastMsg='';
   (function(){ const q=cat.qs[0]; sel=new Set(q.a); tLeft=16; doReveal(); })();""",
}

def shot(name, js):
    src = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    theme = os.environ.get("THEME", "")
    if theme: src = src.replace("<html lang=\"pt-BR\">", f"<html lang=\"pt-BR\" data-theme=\"{theme}\">")
    inject = ("<script>window.addEventListener('load',function(){setTimeout(function(){"
              "try{" + js + "}catch(e){document.body.innerHTML='<pre style=\"color:red;"
              "font-size:11px\">'+(e.stack||e)+'</pre>';}},250);});</script>")
    tmp = os.path.join(ROOT, "_shot.html")
    io.open(tmp, "w", encoding="utf-8").write(src.replace("</body>", inject + "</body>"))
    try:
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                        "--window-size=500," + os.environ.get("H", "940"),
                        "--force-device-scale-factor=2",
                        "--allow-file-access-from-files", "--virtual-time-budget=5000",
                        "--screenshot=" + os.path.join(OUT, name + ".png"),
                        "file://" + tmp], capture_output=True, timeout=240)
    finally:
        if os.path.exists(tmp): os.remove(tmp)
    p = os.path.join(OUT, name + ".png")
    print(f"  {name:14s} {'ok' if os.path.exists(p) else 'MISSING'}")

want = sys.argv[1:] or list(STATES)
for n in want:
    if n in STATES: shot(n, STATES[n])
