#!/usr/bin/env python3
"""Layout checks at real phone sizes.

Headless Chrome will not give you a viewport narrower than 500px: it accepts
`--window-size=320,568` and silently reports clientWidth 500. A probe run
directly in the page therefore tests 500px while claiming to test 320px, and
comes back clean for sizes it never touched — which is exactly how a
below-the-fold CONFIRMAR button survived a "no overflow at 320px" report.

The fix is to render index.html inside an iframe of the target size. An iframe
gets its own viewport, so vw/vh units, media queries and wrapping all behave
as they would on the device.
"""
import subprocess, os, io, re, json, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# width, height, what it stands for
SIZES = [
    (320, 568, "iPhone SE / smallest supported"),
    (360, 640, "common budget Android"),
    (390, 844, "iPhone 14"),
    (412, 915, "Pixel"),
]

PROBE = r"""
<script>
(function(){
  const res=[];
  function probe(label){
    const vw=document.documentElement.clientWidth, vh=document.documentElement.clientHeight;
    const over=[], clipped=[], collide=[];
    document.querySelectorAll('#qz, #ct, #ct *').forEach(function(el){
      const r=el.getBoundingClientRect();
      if(r.width<0.5 && r.height<0.5) return;
      if(r.right>vw+0.5 || r.left<-0.5)
        over.push(el.tagName+(el.className?'.'+String(el.className).split(' ')[0]:'')
                  +' w='+Math.round(r.width)+' "'+(el.textContent||'').trim().slice(0,18)+'"');
    });
    document.querySelectorAll('.tile-name').forEach(function(nm){
      if(nm.scrollHeight>nm.clientHeight+1) clipped.push(nm.textContent.trim().slice(0,20));
    });
    document.querySelectorAll('.b').forEach(function(t){
      const nm=t.querySelector('.tile-name'), v=t.querySelector('.vote-pct');
      if(!nm||!v) return;
      const a=nm.getBoundingClientRect(), b=v.getBoundingClientRect();
      if(a.left<b.right && b.left<a.right && a.top<b.bottom && b.top<a.bottom)
        collide.push(nm.textContent.trim().slice(0,16));
    });
    const cta=document.getElementById('bconf')||document.getElementById('bfinal')
             ||document.getElementById('mil-btn')||document.getElementById('bmilrep');
    const cr=cta?cta.getBoundingClientRect():null;
    res.push({label,vw,vh,
      over:[...new Set(over)].slice(0,4), overN:over.length,
      clipped:[...new Set(clipped)].slice(0,4), clippedN:clipped.length,
      collide:[...new Set(collide)].slice(0,4), collideN:collide.length,
      scrolls:document.documentElement.scrollHeight>vh+1,
      ctaBelowFold: cr ? cr.bottom>vh+1 : null});
  }
  function firstQ(pred){ for(let i=0;i<cat.qs.length;i++) if(pred(cat.qs[i])) return i; return 0; }
  try{
    sc='home'; go(); probe('home');
    startMilhao(); probe('milhao rung 1');
    qi=firstQ(q=>q.type==='player'&&!q.textTiles); rung=9; disp=getDisp(cat.qs[qi]); go();
      usePoll(); useExpert(); probe('photo tiles + 2 ajudas');
    startMilhao(); qi=firstQ(q=>q.textTiles); rung=9; disp=getDisp(cat.qs[qi]); go();
      usePoll(); probe('text tiles + placar');
    startMilhao(); qi=firstQ(q=>q.reveal); rung=11; disp=getDisp(cat.qs[qi]); go();
      usePoll(); useExpert(); probe('photo-reveal + 2 ajudas');
    ladderOpen=true; go(); probe('ladder sheet'); ladderOpen=false;
    sel=new Set([disp[0].id]); sc='ask'; go(); probe('resposta final');
    startSurvival(); probe('mata-mata');
    startDaily(); probe('diario');
    diffKey='dificil'; startGame(); probe('treino');
    sc='medals'; go(); probe('medalhas');
    album=new Set(PL.slice(0,60).map(x=>x.id)); sc='album'; go(); probe('album');
    (function(){                       // the reveal, with a sticker back on screen
      const save=advanceAfterReveal; advanceAfterReveal=function(){};
      diffKey='moderado'; startGame();
      const q=cat.qs.find(x=>x.type==='player'&&x.a.length===1)||cat.qs[0];
      qi=cat.qs.indexOf(q); disp=getDisp(q); album=new Set(); sel=new Set(q.a); doReveal();
      probe('reveal + ficha'); advanceAfterReveal=save;
    })();
    sc='credits'; go(); probe('creditos');
    sc='difficulty'; go(); probe('escolha');
    startMilhao(); rung=16; banked=1000000; cashed=true; nCorrect=16; sc='end';
      window._newMedals=[]; go(); probe('fim - milhao');
  }catch(e){ res.push({label:'EXCEPTION',err:(e&&e.stack)||String(e)}); }
  const payload=JSON.stringify(res);
  const el=document.createElement('div'); el.id='OUT';
  el.textContent=payload; document.body.appendChild(el);
  // postMessage rather than leaving the parent to poll contentDocument:
  // reaching into the frame races with its document being swapped in.
  try { parent.postMessage(payload, '*'); } catch (e) {}
})();
</script>
"""

# Poll for the inner probe rather than waiting a fixed interval: the page has
# 150+ images to decode and a single setTimeout races with load, which shows up
# as one size at random reporting nothing.
WRAP = """<body style="margin:0;background:#000">
<iframe id=f src="_narrow_inner.html" style="width:%dpx;height:%dpx;border:0"></iframe>
<div id=R></div>
<script>
(function(){
  var done = false;
  function land(t){ if(!done){ done = true; document.getElementById('R').textContent = t; } }
  window.addEventListener('message', function(e){ if (typeof e.data === 'string') land(e.data); });
  // fallback for the case where the frame loaded before the listener attached
  var deadline = Date.now() + 25000;
  (function poll(){
    if (done) return;
    try {
      var d = document.getElementById('f').contentDocument;
      var o = d && d.getElementById('OUT');
      if (o) return land(o.textContent);
    } catch (e) {}
    if (Date.now() > deadline) return land('NONE');
    setTimeout(poll, 120);
  })();
})();
</script></body>"""


def run(w, h):
    inner = os.path.join(ROOT, "_narrow_inner.html")
    wrap = os.path.join(ROOT, "_narrow_wrap.html")
    src = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    io.open(inner, "w", encoding="utf-8").write(src.replace("</body>", PROBE + "</body>"))
    io.open(wrap, "w", encoding="utf-8").write(WRAP % (w, h))
    # Chrome occasionally wedges on a headless dump; one retry rather than
    # taking the whole suite down with it.
    dom = ""
    try:
        for attempt in (1, 2):
            try:
                dom = subprocess.run(
                    [CHROME, "--headless", "--disable-gpu", "--window-size=1000,1000",
                     "--allow-file-access-from-files", "--virtual-time-budget=40000",
                     "--dump-dom", "file://" + wrap],
                    capture_output=True, text=True, timeout=180).stdout
                break
            except subprocess.TimeoutExpired:
                if attempt == 2:
                    print(f"   (chrome hung twice at {w}x{h})")
                    return None
    finally:
        for f in (inner, wrap):
            if os.path.exists(f):
                os.remove(f)
    m = re.search(r'<div id="R">(.*?)</div>', dom, re.S)
    if not m or "NONE" in m.group(1):
        return None
    return json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&")
                                .replace("&lt;", "<").replace("&gt;", ">"))


fails = 0
for w, h, note in SIZES:
    rows = run(w, h)
    if rows is None:
        print(f"\n=== {w}x{h} — probe did not report ==="); fails += 1; continue
    real = rows[0].get("vw")
    if real != w:
        print(f"\n!! {w}x{h}: iframe reported viewport {real}px — harness broken")
        fails += 1
        continue
    bad = [r for r in rows if r.get("err") or r.get("overN") or r.get("clippedN")
           or r.get("collideN") or r.get("ctaBelowFold")]
    print(f"\n=== {w}x{h}  ({note})  screens={len(rows)}  problems={len(bad)} ===")
    for r in bad:
        fails += 1
        if r.get("err"):
            print(f"  EXCEPTION {r['err'][:160]}"); continue
        print(f"  {r['label']}")
        if r["overN"]:     print(f"      overflows x{r['overN']}: {', '.join(r['over'])}")
        if r["clippedN"]:  print(f"      clipped captions x{r['clippedN']}: {', '.join(r['clipped'])}")
        if r["collideN"]:  print(f"      vote/name overlap x{r['collideN']}: {', '.join(r['collide'])}")
        if r["ctaBelowFold"]: print("      CONFIRM BUTTON BELOW THE FOLD")
    if not bad:
        print("  all clean")

print(f"\n{'PASS' if fails == 0 else 'FAIL'} — {fails} problem(s)")
sys.exit(0 if fails == 0 else 1)
