#!/usr/bin/env python3
"""Find images that fail to decode in a real browser, plus file-level problems."""
import subprocess, os, io, re, json, struct

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
s = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()

refs = sorted(set(re.findall(r"img/[0-9a-f]{16}\.(?:png|jpg|jpeg)", s)))
print(f"{len(refs)} image references in index.html")

# ── file level ──
missing, tiny, bad = [], [], []
for r in refs:
    p = os.path.join(ROOT, r)
    if not os.path.exists(p): missing.append(r); continue
    n = os.path.getsize(p)
    if n < 1500: tiny.append((r, n)); continue
    head = io.open(p, "rb").read(12)
    if not (head.startswith(b"\x89PNG") or head.startswith(b"\xff\xd8")):
        bad.append((r, head[:8]))
print(f"  missing={len(missing)} tiny={len(tiny)} bad-header={len(bad)}")
for x in missing[:10]: print("   MISSING", x)
for x in tiny[:10]:    print("   TINY   ", x)
for x in bad[:10]:     print("   BADHDR ", x)

# ── orphans on disk ──
on_disk = {f"img/{f}" for f in os.listdir(os.path.join(ROOT, "img"))}
orphans = sorted(on_disk - set(refs))
print(f"  orphaned files on disk (not referenced): {len(orphans)}")

# ── browser level: does every player/club image actually decode? ──
T = r"""
<script>
(function(){
  const urls = new Set();
  PL.forEach(p => p.img && urls.add(p.img));
  Object.values(LOGOS).forEach(u => urls.add(u));
  Object.values(PORT_IMGS || {}).forEach(u => urls.add(u));
  Object.values(STAD_IMGS || {}).forEach(u => urls.add(u));
  const list = [...urls];
  let done = 0; const failed = [], small = [];
  list.forEach(u => {
    const im = new Image();
    im.onload = () => {
      if (im.naturalWidth < 60 || im.naturalHeight < 60)
        small.push({u, w: im.naturalWidth, h: im.naturalHeight});
      if (++done === list.length) finish();
    };
    im.onerror = () => { failed.push(u); if (++done === list.length) finish(); };
    im.src = u;
  });
  function finish(){
    // which player owns each broken file
    const who = u => { const p = PL.find(x=>x.img===u); if (p) return 'player:'+p.n;
      const c = Object.keys(LOGOS).find(k=>LOGOS[k]===u); if (c) return 'club:'+c;
      return '?'; };
    const el = document.createElement('div'); el.id='OUT';
    el.textContent = JSON.stringify({
      total:list.length,
      failed: failed.map(u=>({u, who:who(u)})),
      small: small.map(o=>({...o, who:who(o.u)})),
    });
    document.body.appendChild(el);
  }
  if (list.length === 0) finish();
})();
</script>
"""
tmp = os.path.join(ROOT, "_imgchk.html")
io.open(tmp, "w", encoding="utf-8").write(s.replace("</body>", T + "</body>"))
try:
    dom = subprocess.run([CHROME, "--headless", "--disable-gpu", "--virtual-time-budget=15000",
                          "--allow-file-access-from-files", "--dump-dom", "file://" + tmp],
                         capture_output=True, text=True, timeout=240).stdout
finally:
    os.remove(tmp)

m = re.search(r'<div id="OUT">(.*?)</div>', dom, re.S)
if not m:
    print("\n!! browser check produced no output")
else:
    d = json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&")
                             .replace("&lt;", "<").replace("&gt;", ">"))
    print(f"\nbrowser-decoded {d['total']} images")
    print(f"  FAILED TO LOAD: {len(d['failed'])}")
    for f in d["failed"]: print("    ", f["who"], f["u"])
    print(f"  suspiciously small: {len(d['small'])}")
    for f in d["small"]: print("    ", f["who"], f["u"], f"{f['w']}x{f['h']}")
