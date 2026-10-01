#!/usr/bin/env python3
"""Repaint every raster image in the app with a Gemini image model, into a
staging tree — never over the live images.

What gets painted, and how:
  player   the album's portraits          -> atelier_full (the approved style)
  scene    every other photograph in img/ -> the same hand, for places/things
  emblem   club crests, mascot pictures   -> a hand-painted emblem, exact
           (img/ logos, img/crests, img/msc)  shapes and lettering, background
                                               keyed back to transparent
  flag     img/flags                      -> painted cloth, exact design

Output: OUT/<same relative path as the source>, as .webp, cropped to the
source's proportions; OUT/status/<path>.json records how each one went.
An image whose output already exists is skipped, so a run that stops can
simply be started again. FORCE lists paths to redo regardless.

Environment:
  GEMINI_API_KEY   required, never printed
  GEMINI_MODEL     default gemini-3-pro-image-preview
  KINDS            comma list of kinds to do (default: all)
  SHARD, SHARDS    do only items i where i % SHARDS == SHARD
  ONLY             comma list of source paths or player ids (overrides kinds)
  FORCE            comma list of source paths or player ids to redo
  OUT              staging root (default ai-batch)
  COMMIT_EVERY     if set, call ./publish.sh every N new images
  LIMIT            stop after this many new images (0 = no limit)
"""
import base64, glob, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import paint_test as pt          # the approved prompts and the API call
from fill_edges import finish

SCENE = """Repaint this photograph as a museum-quality hand-painted picture, in the manner of a \
contemporary master painter working in gouache and watercolour on heavy cold-press paper.

The main subject — whatever the photo is of: a stadium, a trophy, a ball, a match, a crowd, an object — \
is fully and confidently painted with expressive visible brushstrokes, sculpted light and shadow and \
crisp highlights. Secondary areas loosen into soft washes and gestural strokes in the photo's own \
colours, with wet-in-wet blooms and layered glazes; the paper grain shows through the thin washes.

Preserve exactly: the composition, framing and crop, the architecture and every object, the people \
and their poses, the colours, and any existing lettering (keep it legible, add none).

Full bleed, painted on a toned ground: no white paper anywhere, every edge and corner solid paint, \
as if cropped from a larger canvas. No vignette, border, frame or signature. It must read \
unmistakably as a painting, never as a filtered photograph. Return only the image."""

EMBLEM = """Repaint this emblem as a hand-painted gouache and enamel-paint emblem, as if a master sign \
painter had painted it by hand on paper.

Keep it EXACTLY the same design: identical shapes, outlines, proportions, symbols, stars, colours and \
every letter and number of its text, all fully legible and spelled exactly as in the source. Do not \
redesign, simplify, add or remove anything.

Rendering: flat areas become rich opaque gouache with subtle visible brush texture and slight \
hand-painted edges; metallic or gold parts get painterly highlights. Keep it a flat, front-facing \
emblem — no 3D, no perspective, no drop shadow, no frame.

Background: plain pure white (#FFFFFF), completely empty, the emblem centred with a small margin. \
Return only the image."""

FLAG = """Repaint this flag as a hand-painted gouache flag on heavy paper, as a master painter would \
paint it.

Keep it EXACTLY the same design: identical stripes, bands, shapes, emblems, stars and colours, in the \
same proportions and positions, flat and front-facing — no waving, no perspective, no pole.

Rendering: rich opaque gouache with visible brush strokes following each band, subtle soft cloth \
texture and slight hand-painted edges between colours. Full bleed: the flag fills the entire canvas \
edge to edge, no border, no background, no vignette, no signature. Return only the image."""


def manifest():
    """every raster image the app uses -> kind"""
    src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    players = {}
    for m in re.finditer(r"id:\s*'([a-z0-9_]+)',\s*n:\s*'((?:[^'\\]|\\.)*)',\s*img:\s*'(img/[^']+)'", src):
        players[m.group(3)] = m.group(1)
    logos = set(re.findall(r"'(img/(?:crests/)?[0-9a-z\-]+\.webp)'",
                           src[src.index('const LOGOS = {'):src.index('const XCREST_NAME')]))
    items = {}
    for p in sorted(glob.glob(os.path.join(ROOT, 'img', '*.webp'))):
        rel = os.path.relpath(p, ROOT)
        if os.path.basename(rel).startswith('paint-'):
            continue
        items[rel] = 'player' if rel in players else 'emblem' if rel in logos else 'scene'
    for p in sorted(glob.glob(os.path.join(ROOT, 'img', 'crests', '*.webp'))):
        items[os.path.relpath(p, ROOT)] = 'emblem'
    for p in sorted(glob.glob(os.path.join(ROOT, 'img', 'msc', '*.webp'))):
        items[os.path.relpath(p, ROOT)] = 'emblem'
    for p in sorted(glob.glob(os.path.join(ROOT, 'img', 'flags', '*.webp'))):
        items[os.path.relpath(p, ROOT)] = 'flag'
    return items, {v: k for k, v in players.items()}


def prompt(kind):
    return {'player': pt.prompt_for('atelier_full'), 'scene': SCENE, 'emblem': EMBLEM, 'flag': FLAG}[kind]


def fit_to(img, w, h):
    """centre-crop to the source's proportions"""
    ih, iw = img.shape[:2]
    if iw / ih > w / h:
        nw = int(ih * w / h); x = (iw - nw) // 2; img = img[:, x:x + nw]
    else:
        nh = int(iw * h / w); y = (ih - nh) // 2; img = img[y:y + nh]
    return img


def key_white(img):
    """the emblem prompt asks for a white ground; take it back out — only the
    white that touches the border, so white inside the emblem stays"""
    import cv2, numpy as np
    h, w = img.shape[:2]
    near = (img.min(axis=2) > 232).astype(np.uint8)
    mask = np.zeros((h + 2, w + 2), np.uint8)
    flood = near.copy()
    for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        if near[y, x]:
            cv2.floodFill(flood, mask, (x, y), 2)
    bg = (flood == 2).astype(np.float32)
    alpha = 1 - cv2.GaussianBlur(bg, (0, 0), 1.0)
    out = np.dstack([img, (alpha * 255).clip(0, 255).astype(np.uint8)])
    # trim to the emblem with a small margin
    ys, xs = np.where(alpha > .1)
    if len(xs):
        m = int(max(h, w) * .04)
        out = out[max(0, ys.min() - m):ys.max() + m + 1, max(0, xs.min() - m):xs.max() + m + 1]
    return out


def postprocess(kind, data, src_path):
    import cv2, numpy as np
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError('undecodable image')
    srcim = cv2.imread(src_path, cv2.IMREAD_UNCHANGED)
    sh, sw = srcim.shape[:2]
    info = {}
    if kind in ('player', 'scene'):
        img, info = finish(img)
        img = fit_to(img, sw, sh)
    elif kind == 'flag':
        img = fit_to(img, sw, sh)
    else:
        img = key_white(img)
    # keep it light: never smaller than the source, at most 720px long side
    h, w = img.shape[:2]
    scale = min(1.0, 720 / max(h, w))
    scale = max(scale, min(1.0, max(sh, sw) / max(h, w)))
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode('.webp', img, [cv2.IMWRITE_WEBP_QUALITY, 86])
    if not ok:
        raise RuntimeError('encode failed')
    return buf.tobytes(), info


def main():
    key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not key:
        sys.exit('GEMINI_API_KEY is not set')
    model = os.environ.get('GEMINI_MODEL', '').strip() or 'gemini-3-pro-image-preview'
    out = os.environ.get('OUT') or 'ai-batch'
    kinds = set(x for x in (os.environ.get('KINDS') or 'player,scene,emblem,flag').split(',') if x)
    shard, shards = int(os.environ.get('SHARD') or 0), int(os.environ.get('SHARDS') or 1)
    limit = int(os.environ.get('LIMIT') or 0)
    every = int(os.environ.get('COMMIT_EVERY') or 0)
    items, by_id = manifest()
    resolve = lambda s: by_id.get(s.strip(), s.strip())
    only = [resolve(x) for x in (os.environ.get('ONLY') or '').split(',') if x.strip()]
    force = set(resolve(x) for x in (os.environ.get('FORCE') or '').split(',') if x.strip())
    todo = [p for p in sorted(items) if (p in only if only else items[p] in kinds)]
    todo = [p for i, p in enumerate(todo) if i % shards == shard]
    print(f'{len(items)} images in the app; this shard: {len(todo)} ({", ".join(sorted(kinds)) if not only else "selected"})')
    done = new = failed = 0
    for rel in todo:
        dst = os.path.join(out, rel)
        st = os.path.join(out, 'status', rel + '.json')
        if os.path.exists(dst) and rel not in force:
            done += 1
            continue
        kind = items[rel]
        pt.PROMPT_TEXT = prompt(kind)
        raw = open(os.path.join(ROOT, rel), 'rb').read()
        t0 = time.time()
        rec = {'path': rel, 'kind': kind, 'model': model, 'player': next((k for k, v in by_id.items() if v == rel), None)}
        try:
            res = pt.call(model, key, raw, 'image/webp', attempts=6)
            parts = (res.get('candidates') or [{}])[0].get('content', {}).get('parts', [])
            img = next((p.get('inlineData') or p.get('inline_data') for p in parts
                        if p.get('inlineData') or p.get('inline_data')), None)
            if not img:
                raise RuntimeError(f"no image ({(res.get('candidates') or [{}])[0].get('finishReason')})")
            data, info = postprocess(kind, base64.b64decode(img['data']), os.path.join(ROOT, rel))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(data)
            rec.update(ok=True, seconds=round(time.time() - t0, 1), edges=info)
            new += 1
            print(f'✓ {rel} [{kind}] {time.time() - t0:.0f}s', flush=True)
        except Exception as e:
            rec.update(ok=False, error=str(e)[:400])
            failed += 1
            print(f'✗ {rel} [{kind}] {str(e)[:200]}', flush=True)
        os.makedirs(os.path.dirname(st), exist_ok=True)
        json.dump(rec, open(st, 'w'), ensure_ascii=False)
        if every and new and new % every == 0:
            subprocess.run([os.path.join(HERE, 'publish.sh'), f'{new} more'], check=False)
        if limit and new >= limit:
            break
    print(f'shard {shard}/{shards}: {new} painted, {done} already done, {failed} failed')


if __name__ == '__main__':
    main()
