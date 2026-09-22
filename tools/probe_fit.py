#!/usr/bin/env python3
"""Nothing in this app should scroll. This measures whether that is true.

Renders every screen at several real phone sizes and reports anything taller
than the viewport: the page itself, and any .scroll-y box whose content
overflows its own frame. Screens are driven through the real state machine,
and the deals are repeated, because one deal is not a sample — a ten-tile
board with a long "Você sabia?" is the case that overflows, and it only turns
up on some questions.

The Android nav bar is simulated the way the album work found it had to be:
headless reports env(safe-area-inset-bottom) as 0, so the inset is string-
replaced into the source before rendering.
"""
import subprocess, os, io, re, json, sys

ROOT   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# label, css width, css height, simulated bottom inset
CHROME_H = 87   # headless browser chrome, measured

SIZES = [
    ("small-360x640",  360, 640, 0),
    ("iphone-390x844", 390, 844, 0),
    ("pixel-412x915",  412, 915, 48),
    ("tall-360x780",   360, 780, 40),
]

PROBE = r"""
  function fit(label){
    var de = document.documentElement, b = document.body;
    var vh = de.clientHeight;
    /* #qz is capped to the viewport and clips, so the page can no longer
       grow: what matters now is whether a screen's content is TALLER than
       the frame it is being drawn into, i.e. whether anything is cut off. */
    var qz = document.getElementById('qz');
    var pgEl = document.querySelector('#ct > .pg');
    var over = Math.max(de.scrollHeight - vh, 0);
    if (qz && pgEl) over = Math.max(over, pgEl.scrollHeight - qz.clientHeight,
                                    qz.scrollHeight - qz.clientHeight);
    /* Créditos is the one box in the app allowed to scroll: it is ~200 photo
       attributions, a licence obligation rather than gameplay, and paginating
       a legal list would be worse to read. Its FRAME still has to fit, which
       the page check above enforces — only its contents may run long. */
    var boxes = [];
    if (label !== 'credits') document.querySelectorAll('.scroll-y').forEach(function(el){
      var d = el.scrollHeight - el.clientHeight;
      if (d > 1) boxes.push({cls: (el.className||'').slice(0,40), over: Math.round(d)});
    });
    /* what is actually making the page tall: the direct children of the
       screen, so the report names a block rather than the whole page */
    var tall = [];
    if (over > 1) {
      var pg = document.querySelector('#ct > .pg') || document.querySelector('#ct');
      if (pg) Array.prototype.forEach.call(pg.children, function(el){
        var r = el.getBoundingClientRect();
        tall.push({cls: (el.className||el.tagName||'').slice(0,26), h: Math.round(r.height)});
      });
      tall.sort(function(a,b){ return b.h - a.h; });
      tall = tall.slice(0, 4);
    }
    if (over > 1 || boxes.length) all.push({label: label, over: Math.round(over), vh: vh,
                                            boxes: boxes.slice(0,3), tall: tall});
    seen++;
  }
"""

DRIVE = r"""
  /* the still screens */
  ['home','album','medals','credits','difficulty'].forEach(function(s){ sc=s; go(); fit(s); });
  sc='album'; albCtry='__escudos'; go(); fit('album/escudos');
  sc='album'; albCtry='__mascotes'; go(); fit('album/mascotes');

  /* boards: several deals per level, because tile count varies by question */
  ['facil','moderado','dificil'].forEach(function(k){
    for (var i=0;i<3;i++){ diffKey=k; startGame(); fit("quiz/"+k); }
  });

  /* the ladder, every rung — the tall boards and the cartas especiais */
  for (var r=0;r<LADDER.length;r++){
    startMilhao(); rung=r; qi=r; disp=dealDisp(r); tMax=qTime(); tLeft=tMax;
    if (cat.qs[r]._special){ sc='card'; go(); fit('carta/'+cat.qs[r]._special); }
    sc='quiz'; go(); fit('milhao/rung'+(r+1));
    if (cat.qs[r].clues){ cat.qs[r]._shown=cat.qs[r].clues.length; go(); fit('milhao/rung'+(r+1)+'-4pistas'); }
  }

  /* the ladder sheet and the final-answer beat */
  startMilhao(); rung=9; qi=9; disp=dealDisp(9); sc='quiz'; ladderOpen=true; go(); fit('ladder-sheet');
  ladderOpen=false;
  startMilhao(); rung=ASK_FROM_RUNG; qi=rung; disp=dealDisp(qi); sel=new Set([disp[0].id]);
  sc='ask'; go(); fit('resposta-final');

  /* THE REVEAL — verdict + sticker back + "Você sabia?" + Próxima, all of it
     under the board. This is the one the player reported. Hold it on screen
     and try a lot of questions, long stories included. */
  advanceAfterReveal = function(){};
  ['moderado','dificil'].forEach(function(k){
    for (var i=0;i<7;i++){
      diffKey=k; startGame();
      var j = i % cat.qs.length;
      qi=j; disp=getDisp(cat.qs[j]); sel=new Set(cat.qs[j].a); tLeft=Math.round(tMax*0.6);
      doReveal();
      var st = document.querySelector('.story');
      fit('reveal/'+k+(st?'+story':''));
    }
  });
  for (var i=0;i<7;i++){
    startMilhao(); var r2=i%LADDER.length; rung=r2; qi=r2;
    disp=dealDisp(r2); sel=new Set(cat.qs[r2].a); tLeft=10; doReveal();
    var st2 = document.querySelector('.story');
    fit('reveal/milhao-rung'+(r2+1)+(st2?'+story':''));
  }
  /* and a miss, which prints the right answer as well */
  for (var i=0;i<4;i++){
    diffKey="dificil"; startGame();
    var q3=cat.qs[i%cat.qs.length]; qi=cat.qs.indexOf(q3); disp=getDisp(q3);
    var bad=disp.find(function(o){ return !q3.a.includes(o.id); });
    sel=new Set(bad?[bad.id]:[]); tLeft=5; doReveal();
    fit('reveal/errou');
  }

  /* the endings */
  startMilhao(); banked=1000000; rung=LADDER.length; cashed=true; sc='end'; go(); fit('end/milhao-win');
  startMilhao(); banked=5000; rung=7; cashed=false; sc='end'; go(); fit('end/milhao-queda');
  startMilhao(); banked=0; rung=1; cashed=false; sc='end'; go(); fit('end/milhao-zero');
  diffKey='moderado'; startGame(); nCorrect=14; sc='end'; go(); fit('end/treino');
  startSurvival(); nCorrect=9; sc='end'; go(); fit('end/mata-mata');
"""

def run(label, w, h, inset):
    src = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    if inset:
        src = re.sub(r"env\(safe-area-inset-bottom,\s*0px\)", "%dpx" % inset, src)
    # Measure the settled layout, not the entrance. Every screen slides in by
    # 6px and the reveal panel by 16px, and a measurement taken mid-flight
    # reads those as overflow -- which is exactly the constant +6 and +22 this
    # probe reported on screens that plainly fit.
    src = src.replace("</head>", "<style>*,*::before,*::after{animation:none !important;"
                      "transition:none !important}</style></head>")
    js = ("(function(){var all=[],seen=0;" + PROBE + "try{" + DRIVE
          + "}catch(e){all.push({label:'EXCEPTION',over:0,vh:0,boxes:[],"
            "tall:[{cls:(e&&(e.stack||e.message))||String(e),h:0}]});}"
            "var d=document.createElement('pre');d.id='OUT';"
            "d.textContent=JSON.stringify({checked:seen,bad:all});"
            "document.body.appendChild(d);})();")
    tmp = os.path.join(ROOT, "_fit.html")
    io.open(tmp, "w", encoding="utf-8").write(
        src.replace("</body>", "<script>window.addEventListener('load',function(){"
                    "setTimeout(function(){" + js + "},400)});</script></body>"))
    try:
        dom = subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                              # --window-size is the WINDOW: headless still keeps ~87px of
                              # browser chrome, so a "640" window was measuring a 553px
                              # viewport and the labels were lying about which phone failed.
                              "--window-size=%d,%d" % (w, h + CHROME_H), "--allow-file-access-from-files",
                              "--virtual-time-budget=20000", "--dump-dom", "file://" + tmp],
                             capture_output=True, text=True, timeout=560).stdout
    finally:
        if os.path.exists(tmp): os.remove(tmp)
    m = re.search(r'<pre id="OUT">(.*?)</pre>', dom, re.S)
    if not m:
        print("  %s: NO OUTPUT" % label)
        for u in re.findall(r"Uncaught[^<\n]*", dom)[:3]: print("     " + u)
        return None
    return json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&")
                                .replace("&lt;", "<").replace("&gt;", ">"))

want = sys.argv[1:]
total_bad = 0
for label, w, h, inset in SIZES:
    if want and label not in want: continue
    r = run(label, w, h, inset)
    if r is None: total_bad += 1; continue
    # one line per distinct screen, worst overflow kept
    worst = {}
    for b in r["bad"]:
        k = b["label"]
        if k not in worst or b["over"] > worst[k]["over"]: worst[k] = b
    print("\n== %s (%dx%d, inset %d) — %d states checked, %d overflowing =="
          % (label, w, h, inset, r["checked"], len(worst)))
    for k in sorted(worst, key=lambda k: -worst[k]["over"]):
        b = worst[k]
        bits = "  ".join("%s %dpx" % (t["cls"], t["h"]) for t in b["tall"])
        box = "  ".join("%s +%d" % (x["cls"], x["over"]) for x in b["boxes"])
        print("   %-34s page +%-4d %s%s" % (k, b["over"], bits, ("  | box: " + box) if box else ""))
    total_bad += len(worst)

print("\n%s" % ("PASS — nothing scrolls" if total_bad == 0
                else "FAIL — %d screen/size combinations overflow" % total_bad))
sys.exit(0 if total_bad == 0 else 1)
