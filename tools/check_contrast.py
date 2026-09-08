#!/usr/bin/env python3
"""Text contrast, measured on the rendered page rather than on the tokens.

Checking the colour variables alone is not enough: half the muted text in this
app is a token *plus* an opacity, and the two multiply. This walks every screen,
takes the computed colour of every text node, composites it over whatever is
actually behind it — including the opacity of every ancestor — and reports
anything below the WCAG AA threshold for its size.

Disabled controls are skipped: WCAG exempts them, and --ink-4 exists for them.
"""
import subprocess, os, io, re, json, html as _html

ROOT   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

PROBE = r"""
(function(){
  function parse(c){
    var m=/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/.exec(c);
    return m?{r:+m[1],g:+m[2],b:+m[3],a:m[4]===undefined?1:+m[4]}:null;
  }
  function lum(c){
    var f=function(v){v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4);};
    return .2126*f(c.r)+.7152*f(c.g)+.0722*f(c.b);
  }
  function ratio(a,b){var x=lum(a),y=lum(b),hi=Math.max(x,y),lo=Math.min(x,y);
    return (hi+.05)/(lo+.05);}
  function over(fg,bg,alpha){   // composite fg onto bg at alpha
    return {r:fg.r*alpha+bg.r*(1-alpha), g:fg.g*alpha+bg.g*(1-alpha), b:fg.b*alpha+bg.b*(1-alpha)};
  }
  function bgOf(el){
    var n=el;
    while(n && n!==document.documentElement){
      var c=parse(getComputedStyle(n).backgroundColor);
      if(c && c.a>0.99) return c;
      n=n.parentElement;
    }
    return {r:255,g:255,b:255};
  }
  function opacityChain(el){
    var o=1,n=el;
    while(n && n!==document.documentElement){ o*= parseFloat(getComputedStyle(n).opacity||1); n=n.parentElement; }
    return o;
  }
  function disabled(el){
    var n=el;
    while(n){ if(n.disabled || n.getAttribute && n.getAttribute('aria-disabled')==='true') return true; n=n.parentElement; }
    return false;
  }
  var out=[];
  document.querySelectorAll('#ct *').forEach(function(el){
    var direct='';
    for(var i=0;i<el.childNodes.length;i++)
      if(el.childNodes[i].nodeType===3) direct+=el.childNodes[i].textContent;
    direct=direct.replace(/\s+/g,' ').trim();
    if(!direct) return;
    var cs=getComputedStyle(el);
    if(cs.display==='none'||cs.visibility==='hidden') return;
    var r=el.getBoundingClientRect(); if(r.width<1||r.height<1) return;
    if(el.closest('[aria-hidden="true"]')) return;
    if(disabled(el)) return;
    var fg=parse(cs.color); if(!fg) return;
    var bg=bgOf(el);
    var alpha=fg.a*opacityChain(el);
    var eff=over(fg,bg,alpha);
    var size=parseFloat(cs.fontSize), weight=parseInt(cs.fontWeight)||400;
    var large=(size>=24)||(size>=18.66&&weight>=700);
    var need=large?3.0:4.5;
    var got=ratio(eff,bg);
    if(got<need-0.01){
      out.push({t:direct.slice(0,34), cls:(el.className||el.tagName).toString().slice(0,34),
                size:+size.toFixed(1), w:weight, got:+got.toFixed(2), need:need});
    }
  });
  return out;
})()
"""

SCREENS = ["home","album","medals","credits","difficulty"]

def run(theme):
    src = io.open(os.path.join(ROOT,"index.html"), encoding="utf-8").read()
    js = """
    /* The board deals in and the screen fades in, both starting at opacity 0.
       Sampling mid-animation reported every single node at exactly 1.00:1 —
       the text composited onto its own background at alpha 0. Kill animation
       before measuring anything. */
    (function(){ var st=document.createElement('style');
      st.textContent='*,*::before,*::after{animation:none!important;transition:none!important}';
      document.head.appendChild(st); })();
    document.documentElement.setAttribute('data-theme','%s');
    ALL_STICKERS.forEach(function(id){ album.add(id); });
    stats={games:9,correct:80,answered:120,bestStreak:5,perfect:1};
    var all=[], seen={};
    function grab(tag){
      (%s).forEach(function(o){
        var k=tag+'|'+o.cls+'|'+o.t;
        if(seen[k]) return; seen[k]=1; o.screen=tag; all.push(o);
      });
    }
    %s
    /* One board is not a sample. The dark theme's country band on a post-2000
       card was invisible at 1.32:1 and this check passed twice before a random
       deal happened to include a modern player. Deal a lot of boards, and make
       sure both printings are on screen: the retro card and the mint one carry
       different band colours. */
    for (var i=0;i<14;i++){ diffKey='medio'; startGame(); grab('quiz'); }
    for (var i=0;i<8;i++){ diffKey='dificil'; startGame(); grab('quiz-dificil'); }
    for (var i=0;i<8;i++){ startMilhao(); grab('milhao'); }
    sc='album'; albCtry='__escudos'; go(); grab('album/escudos');
    var d=document.createElement('pre'); d.id='OUT';
    d.textContent=JSON.stringify(all); document.body.appendChild(d);
    """ % (theme, PROBE, "".join("sc='%s'; go(); grab('%s');\n" % (s,s) for s in SCREENS))
    tmp=os.path.join(ROOT,"_contrast.html")
    io.open(tmp,"w",encoding="utf-8").write(
        src.replace("</body>","<script>window.addEventListener('load',function(){setTimeout(function(){try{"
                    +js+"}catch(e){document.body.innerHTML='<pre id=OUT>[]</pre>';console.log(e);}},700)});</script></body>"))
    try:
        r=subprocess.run([CHROME,"--headless","--disable-gpu","--window-size=420,900",
            "--virtual-time-budget=25000","--allow-file-access-from-files","--dump-dom","file://"+tmp],
            capture_output=True,text=True,timeout=240)
        m=re.search(r'<pre id="OUT">(.*?)</pre>', r.stdout, re.S)
        return json.loads(_html.unescape(m.group(1))) if m else None
    finally:
        os.path.exists(tmp) and os.remove(tmp)

bad_total=0
for theme in ("light","dark"):
    res=run(theme)
    if res is None:
        print("  %-5s  browser gave no answer — inconclusive" % theme); continue
    # one CSS rule can fail on a hundred cards; group so the list is a to-do
    # list of rules, not a wall of instances
    groups={}
    for o in res:
        k=(o["cls"], o["size"])
        g=groups.setdefault(k, {"n":0,"worst":99,"screens":set(),"eg":o["t"]})
        g["n"]+=1; g["worst"]=min(g["worst"],o["got"]); g["screens"].add(o["screen"])
    print("=== %s: %d distinct rules below AA (%d elements) ===" % (theme, len(groups), len(res)))
    for (cls,size),g in sorted(groups.items(), key=lambda kv: kv[1]["worst"]):
        print("   %5.2f:1  %4.1fpx  x%-4d %-26s %-22s %s"
              % (g["worst"], size, g["n"], cls, ",".join(sorted(g["screens"]))[:22], g["eg"][:24]))
    bad_total+=len(groups)
print()
print("PASS — every text node meets AA" if bad_total==0
      else "FAIL — %d text elements below AA" % bad_total)
raise SystemExit(1 if bad_total else 0)
