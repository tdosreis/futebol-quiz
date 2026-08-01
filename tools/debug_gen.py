#!/usr/bin/env python3
import subprocess, os, io, re, json
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
T = r"""
<script>
(function(){
  const bad = [];
  const P = id => PL.find(p=>p.id===id), C = id => CL.find(c=>c.id===id);
  for (let i=0;i<10;i++) {
    GEN_QS(2).forEach(q => {
      q.a.forEach(id => {
        const hit = q.type === 'player' ? P(id) : C(id);
        if (!hit) bad.push({t:q.t.slice(0,70), id:String(id), type:q.type||'club',
                            gen:(q._cat&&q._cat.name)||'?'});
      });
    });
  }
  const seen = {}; const uniq = [];
  bad.forEach(b => { const k=b.t+b.id; if(!seen[k]){seen[k]=1;uniq.push(b);} });
  const el=document.createElement('div'); el.id='OUT';
  el.textContent=JSON.stringify({count:bad.length, sample:uniq.slice(0,12)});
  document.body.appendChild(el);
})();
</script>
"""
src = io.open(os.path.join(ROOT,"index.html"),encoding="utf-8").read()
tmp = os.path.join(ROOT,"_dbg.html")
io.open(tmp,"w",encoding="utf-8").write(src.replace("</body>", T+"</body>"))
try:
    dom = subprocess.run([CHROME,"--headless","--disable-gpu","--virtual-time-budget=9000",
                          "--allow-file-access-from-files","--dump-dom","file://"+tmp],
                         capture_output=True,text=True,timeout=200).stdout
finally: os.remove(tmp)
m = re.search(r'<div id="OUT">(.*?)</div>', dom, re.S)
if not m:
    print("no output"); print(re.findall(r"Uncaught[^<\n]*", dom)[:3])
else:
    d = json.loads(m.group(1).replace("&quot;",'"').replace("&amp;","&"))
    print("unresolvable answers:", d["count"])
    for b in d["sample"]: print("  ", b)
