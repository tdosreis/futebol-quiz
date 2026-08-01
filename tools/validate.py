#!/usr/bin/env python3
"""Static sanity checks on the game data inside index.html."""
import re, io, os, sys, json

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

# every question answer id must resolve
qs = re.findall(r"\{ t:'((?:[^'\\]|\\.)*)'[^\n]*?a:\[([^\]]*)\]([^\n]*)", s)
print(f"questions parsed={len(qs)}")
for t, alist, rest in qs:
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
    if a < 1940 or b > 2027: warns.append(f"{mid}: suspicious era ({a},{b})")
    if not re.search(r"pos:'(GK|DF|MF|FW)'", body): errs.append(f"{mid}: bad/missing pos")
    if not re.search(r"clubs:\[", body): errs.append(f"{mid}: missing clubs")

# image references resolve on disk
root = os.path.dirname(P)
for img in sorted(set(re.findall(r"img/[a-f0-9]{16}\.(?:png|jpg|jpeg)", s))):
    if not os.path.exists(os.path.join(root, img)):
        errs.append(f"missing image file: {img}")

print(f"\n{len(errs)} errors, {len(warns)} warnings")
for e in errs[:40]: print("  ERR ", e)
for w in warns[:20]: print("  warn", w)
sys.exit(1 if errs else 0)
