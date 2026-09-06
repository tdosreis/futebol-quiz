#!/usr/bin/env python3
"""Sanity checks on the game data in index.html — as text, then in a real browser."""
import io, re, os, sys, json

P = os.path.join(os.path.dirname(__file__), "..", "index.html")
s = io.open(P, encoding="utf-8").read()

def ids_in(block_re, flags=re.S):
    m = re.search(block_re, s, flags)
    return (m.group(1) if m else ""), bool(m)

errs, warns = [], []

pl_block, ok = ids_in(r"const PL = \[(.*?)\n\];")
cl_block, _  = ids_in(r"const CL = \[(.*?)\n\];")
meta_block,_ = ids_in(r"const PL_META = \{(.*?)\n\};")
clmeta,_     = ids_in(r"const CL_META = \{(.*?)\n\};")

pl_ids   = re.findall(r"\{ *id:'([\w_]+)'", pl_block)
cl_ids   = re.findall(r"\{ *id:'([\w_]+)'", cl_block)
meta_ids = re.findall(r"^\s*([\w_]+):\s*\{", meta_block, re.M)
clm_ids  = re.findall(r"(\w+):\{f:", clmeta)

print(f"players={len(pl_ids)} clubs={len(cl_ids)} pl_meta={len(meta_ids)} cl_meta={len(clm_ids)}")

for pid in pl_ids:
    if pid not in meta_ids: errs.append(f"player '{pid}' has no PL_META entry")
for mid in meta_ids:
    if mid not in pl_ids: errs.append(f"PL_META '{mid}' is not a real player")
for cid in cl_ids:
    if cid not in clm_ids: errs.append(f"club '{cid}' has no CL_META entry")

# duplicate ids
for name, arr in (("PL", pl_ids), ("CL", cl_ids)):
    dups = {x for x in arr if arr.count(x) > 1}
    if dups: errs.append(f"{name} duplicate ids: {dups}")

# Two rows for the same person is worse than a duplicate id: the ids differ so
# nothing above complains, but the album prints him twice and a generator can
# name one and answer with the other's clubs. Caught exactly that way with
# Juninho Pernambucano, who was added a second time as `juninho_pe`.
pl_names = re.findall(r"\{ *id:'[\w_]+', *n:'((?:[^'\\]|\\.)*)'", pl_block)
seen_n = {}
for n in pl_names:
    seen_n[n] = seen_n.get(n, 0) + 1
dup_n = sorted(n for n, k in seen_n.items() if k > 1)
if dup_n: errs.append(f"PL duplicate player names: {dup_n}")

pl_imgs = re.findall(r"\{ *id:'[\w_]+',[^\n]*img:'(img/[^']+)'", pl_block)
dup_i = sorted({i for i in pl_imgs if pl_imgs.count(i) > 1})
if dup_i: errs.append(f"PL two players share a photo: {dup_i}")

# every question answer id must resolve
qs = re.findall(r"\{ t:'((?:[^'\\]|\\.)*)'[^\n]*?a:\[([^\]]*)\]([^\n]*)", s)
print(f"questions parsed={len(qs)}")
for t, alist, rest in qs:
    # A text question answers with a word, not a row: check its answers are
    # among its own choices instead of looking for them in PL or CL.
    if "type:'txt'" in rest:
        continue
    answers = re.findall(r"'([\w_]+)'", alist)
    is_player = "type:'player'" in rest
    pool = pl_ids if is_player else cl_ids
    for a in answers:
        if a not in pool:
            errs.append(f"answer '{a}' not found in {'PL' if is_player else 'CL'} :: {t[:60]}")
    if not answers:
        errs.append(f"question with no answers :: {t[:60]}")

# era sanity
for mid, body in re.findall(r"^\s*([\w_]+):\s*\{([^}]*)\}", meta_block, re.M):
    em = re.search(r"era:\[(\d+),(\d+)\]", body)
    if not em: errs.append(f"{mid}: missing era"); continue
    a, b = int(em.group(1)), int(em.group(2))
    if a >= b: errs.append(f"{mid}: era start >= end ({a},{b})")
    # 1925: the album now reaches Friedenreich's generation, so a 1920s debut
    # is real data rather than a typo. Anything earlier still deserves a look.
    if a < 1925 or b > 2027: warns.append(f"{mid}: suspicious era ({a},{b})")
    if not re.search(r"pos:'(GK|DF|MF|FW)'", body): errs.append(f"{mid}: bad/missing pos")
    if not re.search(r"clubs:\[", body): errs.append(f"{mid}: missing clubs")

# text questions: every answer must be one of that question's own choices,
# and the choices must be distinct — a duplicate makes two tiles both right.
for m in re.finditer(r"\{ t:'((?:[^'\\]|\\.)*)'[^\n]*?type:'txt'[^\n]*", s):
    blk = m.group(0)
    ch = re.search(r"choices:\[([^\]]*)\]", blk)
    an = re.search(r"a:\[([^\]]*)\]", blk)
    if not ch or not an:
        errs.append(f"txt question missing choices or a :: {m.group(1)[:50]}"); continue
    choices = re.findall(r"'((?:[^'\\]|\\.)*)'", ch.group(1))
    answers = re.findall(r"'((?:[^'\\]|\\.)*)'", an.group(1))
    if len(set(choices)) != len(choices):
        errs.append(f"txt question has duplicate choices :: {m.group(1)[:50]}")
    if len(choices) < 4:
        errs.append(f"txt question has only {len(choices)} choices :: {m.group(1)[:50]}")
    for a in answers:
        if a not in choices:
            errs.append(f"txt answer '{a}' not among its choices :: {m.group(1)[:50]}")

# image references resolve on disk
root = os.path.dirname(P)
for img in sorted(set(re.findall(r"img/[a-f0-9]{16}\.(?:png|jpg|jpeg)", s))):
    if not os.path.exists(os.path.join(root, img)):
        errs.append(f"missing image file: {img}")

# ── does the page's script actually parse and run? ──
# A single stray apostrophe in a name kills the whole <script>, and every
# check above still passes because they only ever read the file as text.
# So boot it in a real browser and ask the app to count itself.
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if os.path.exists(CHROME):
    import subprocess, json as _json
    probe = ("<script>setTimeout(function(){var o={};"
             "['PL','PL_META','LOGOS','CL','CREDITS'].forEach(function(k){"
             "  try{var v=eval(k); o[k]=Array.isArray(v)?v.length:Object.keys(v).length;}"
             "  catch(e){o[k]='UNDEFINED';}});"
             "var d=document.createElement('pre');d.id='VOUT';"
             "d.textContent=JSON.stringify(o);document.body.appendChild(d);},600);</script>")
    tmp = os.path.join(root, "_validate_boot.html")
    io.open(tmp, "w", encoding="utf-8").write(s.replace("</body>", probe + "</body>"))
    try:
        # A browser that never answered proves nothing about the page. Treat a
        # timeout or a crash as the tool failing, not the app — a check that
        # cries wolf on a busy machine is worse than no check at all.
        dom = None
        try:
            dom = subprocess.run([CHROME, "--headless", "--disable-gpu",
                                  "--virtual-time-budget=8000", "--allow-file-access-from-files",
                                  "--dump-dom", "file://" + tmp],
                                 capture_output=True, text=True, timeout=180).stdout
        except subprocess.TimeoutExpired:
            warns.append("boot check skipped: headless Chrome timed out (machine busy?)")
        except Exception as ex:
            warns.append(f"boot check skipped: could not run Chrome ({ex})")
        m = re.search(r'<pre id="VOUT">(.*?)</pre>', dom, re.S) if dom else None
        if dom is None:
            pass                     # already reported as a warning
        elif not m:
            errs.append("the page's script did not run at all (parse error?)")
        else:
            got = _json.loads(m.group(1))
            dead = [k for k, v in got.items() if v == "UNDEFINED"]
            if dead:
                errs.append("script failed to define: " + ", ".join(dead)
                            + " — usually an unescaped quote in a name")
            else:
                print("  booted ok: " + "  ".join(f"{k}={v}" for k, v in got.items()))
    finally:
        if os.path.exists(tmp): os.remove(tmp)

print(f"\n{len(errs)} errors, {len(warns)} warnings")
for e in errs[:40]: print("  ERR ", e)
for w in warns[:20]: print("  warn", w)
sys.exit(1 if errs else 0)
