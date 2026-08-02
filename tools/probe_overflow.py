#!/usr/bin/env python3
"""Measure which element is wider than the viewport on each screen."""
import subprocess, os, io, re, json
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

T = r"""
<script>
(function(){
  function probe(label){
    const vw = document.documentElement.clientWidth;
    const bad = [];
    document.querySelectorAll('#qz, #ct, #ct *').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.right > vw + 0.5 || r.width > vw + 0.5) {
        bad.push({tag: el.tagName, cls: el.className||'',
                  w: Math.round(r.width), right: Math.round(r.right),
                  txt: (el.textContent||'').trim().slice(0,28)});
      }
    });
    return {label, vw, count: bad.length, sample: bad.slice(0,6)};
  }
  const res = [];
  sc='home'; go();               res.push(probe('home'));
  sc='credits'; go();            res.push(probe('credits'));
  diffKey='dificil'; startGame();res.push(probe('quiz-hard'));
  (function(){
    const cq = GEN_QS(3).find(q=>/nesta ordem/.test(q.t));
    if (cq){ cat.qs=[cq]; qi=0; sel.clear(); disp=getDisp(cq); sc='quiz'; go(); }
  })();                          res.push(probe('career'));
  const el=document.createElement('div'); el.id='OUT';
  el.textContent=JSON.stringify(res); document.body.appendChild(el);
})();
</script>
"""
src = io.open(os.path.join(ROOT,"index.html"),encoding="utf-8").read()
tmp = os.path.join(ROOT,"_probe.html")
io.open(tmp,"w",encoding="utf-8").write(src.replace("</body>", T+"</body>"))
try:
    dom = subprocess.run([CHROME,"--headless","--disable-gpu","--window-size=430,860",
                          "--allow-file-access-from-files","--virtual-time-budget=8000",
                          "--dump-dom","file://"+tmp],capture_output=True,text=True,timeout=200).stdout
finally: os.remove(tmp)
m = re.search(r'<div id="OUT">(.*?)</div>', dom, re.S)
if not m:
    print("no output"); print(re.findall(r"Uncaught[^<\n]*", dom)[:3])
else:
    for r in json.loads(m.group(1).replace("&quot;",'"').replace("&amp;","&")
                                  .replace("&lt;","<").replace("&gt;",">")):
        print(f"\n{r['label']}  viewport={r['vw']}  overflowing={r['count']}")
        for b in r["sample"]:
            print(f"   <{b['tag']}> w={b['w']} right={b['right']}  '{b['txt']}'")
