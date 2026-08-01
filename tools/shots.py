#!/usr/bin/env python3
"""Render specific game states to PNG so changes can be eyeballed."""
import subprocess, os, io, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT = os.path.join(ROOT, "store-assets")

# name -> JS to run once the page has booted
STATES = {
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
   const cq = GEN_QS(3).find(q => /caminho/.test(q.t));
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
    inject = ("<script>window.addEventListener('load',function(){setTimeout(function(){"
              "try{" + js + "}catch(e){document.body.innerHTML='<pre style=\"color:red;"
              "font-size:11px\">'+(e.stack||e)+'</pre>';}},250);});</script>")
    tmp = os.path.join(ROOT, "_shot.html")
    io.open(tmp, "w", encoding="utf-8").write(src.replace("</body>", inject + "</body>"))
    try:
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                        "--window-size=500,940", "--force-device-scale-factor=2",
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
