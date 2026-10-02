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
  person   tools/gemini/people.json       -> the same portrait hand, from a free
           (coaches, pioneers, players       photograph found on Wikipedia (sources.py),
            the album has no picture of)     written to img/people/<slug>.webp
  mascot   tools/gemini/mascots.json      -> an original full-length cartoon mascot in
                                             the club's colours, painted in the album's
                                             hand: img/msc-club/<club>.webp

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
  FETCH_ONLY       if set, person items only fetch and stage their source
                   photograph (OUT/src/...) — no Gemini call, no cost
"""
import base64, glob, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import paint_test as pt          # the approved prompts and the API call
from fill_edges import finish
import sources

SCENE = """Repaint this photograph as a museum-quality hand-painted picture, in the manner of a \
contemporary master painter working in gouache and watercolour on heavy cold-press paper. This is a \
complete re-rendering in paint, not a filter: there must be no photographic detail left anywhere — \
buildings, sky, pitch, crowd, cars and signs are all rebuilt from visible brushstrokes, simplified \
into confident painted planes, broken edges and loose washes, the way a plein-air painter would \
paint the scene on location.

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


MASCOT = """Paint an original full-length cartoon football mascot character, in the manner of a master \
illustrator of classic 1990s Brazilian sticker albums, now painted by hand in gouache and watercolour on \
heavy cold-press paper.

The character: {who}. It is the mascot of {club}, known as "{name}". The reference image shows only which \
kind of creature or figure it is — design a new, original, charming character of that kind, standing or \
running, full body, friendly and full of personality, with a big expressive face.

It wears a plain football kit in the club's colours: {colors}. No crest, no badge, no logo, no sponsor, \
no letters and no numbers anywhere.

Rendering: confident ink-and-brush outlines, rich opaque gouache with visible brushwork and soft \
watercolour shading, warm highlights. Background: a soft watercolour wash in the club's colours that runs \
off every edge — no white paper, no frame, no border, no text, no signature. Square composition, the \
character centred and filling most of the picture. Return only the image."""

# what each figure is, for the prompt (the reference picture gives the shape)
MASCOT_WHO = {
    'galo': 'a proud rooster', 'raposa': 'a clever fox', 'porco': 'a cheerful pig', 'urubu': 'a black vulture',
    'peixe': 'a jolly fish', 'leao': 'a lion', 'coelho': 'a rabbit', 'macaca': 'a female monkey',
    'tigre': 'a tiger', 'touro': 'a strong bull', 'dragao': 'a friendly dragon', 'cobra': 'a coral snake',
    'periquito': 'a green parakeet', 'elefante': 'an elephant', 'tubarao': 'a shark', 'timbu': 'an opossum',
    'almirante': 'an old navy admiral with a white beard, a bicorne hat and a telescope',
    'mosqueteiro': 'a musketeer with a plumed wide-brimmed hat, cape and fencing sword',
    'saci': 'the Saci-pererê of Brazilian folklore: a one-legged boy with a red cap, drawn with warmth and respect',
    'poDeArroz': 'a dapper old-fashioned gentleman in a top hat and tailcoat',
    'cachorro': 'a scruffy black-and-white mongrel dog', 'santo': 'a kindly cartoon saint with a halo',
    'furacao': 'a whirling hurricane with a face', 'heroi': 'a cheerful superhero with a cape',
    'vovo': 'a lively grandfather with white hair', 'coxa': 'a sporty old man with a white beard',
    'dourado': 'a golden river fish', 'papo': 'a smiling cartoon figure', 'verdao': 'a green figure',
    'figueira': 'a fig tree with a friendly face', 'papao': 'a big friendly monster',
    'caravela': 'a Portuguese caravel ship with a face', 'azulao': 'a blue songbird',
    'pantera': 'a black panther',
}
LEAO_V = {'coroa': ' wearing a small crown', 'pici': '', 'ilha': '', 'azul': ' with a blue mane', 'barra': '', 'faixa': ''}
COLOR_NAMES = {'#111': 'black', '#EEE': 'white'}


def color_words(c1, c2):
    import colorsys
    def name(h):
        if h in COLOR_NAMES: return COLOR_NAMES[h]
        h = h.lstrip('#')
        if len(h) == 3: h = ''.join(x * 2 for x in h)
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        hu, l, s = colorsys.rgb_to_hls(r, g, b)
        if s < .15 or l < .1 or l > .92:
            return 'black' if l < .2 else 'white' if l > .85 else 'grey'
        hue = hu * 360
        base = ('red' if hue < 15 or hue >= 345 else 'orange' if hue < 40 else 'gold' if hue < 55 else
                'yellow' if hue < 70 else 'green' if hue < 165 else 'turquoise' if hue < 190 else
                'sky blue' if hue < 205 else 'blue' if hue < 250 else 'purple' if hue < 290 else
                'magenta' if hue < 330 else 'crimson')
        return ('deep ' if l < .32 else 'light ' if l > .7 else '') + base
    return ' and '.join(dict.fromkeys(name(c) for c in (c1, c2) if c))


def slug(s):
    import unicodedata
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def people():
    p = os.path.join(HERE, 'people.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else []


def mascots():
    p = os.path.join(HERE, 'mascots.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else []


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
    for pe in people():
        if not pe.get('skip'):
            items[f'img/people/{slug(pe["n"])}.webp'] = 'person'
    for m in mascots():
        if m['art'] != 'papo':
            items[f'img/msc-club/{m["id"]}.webp'] = 'mascot'
    return items, {v: k for k, v in players.items()}


def prompt(kind, rel=None):
    if kind == 'mascot':
        m = next(x for x in mascots() if rel.endswith('/' + x['id'] + '.webp'))
        who = MASCOT_WHO.get(m['art'], 'a friendly mascot') + (LEAO_V.get(m['v'], '') if m['art'] == 'leao' else '')
        return MASCOT.format(who=who, club=m['club'], name=m['n'], colors=color_words(m['c1'], m['c2']))
    return {'player': pt.prompt_for('atelier_full'), 'person': pt.prompt_for('atelier_full'),
            'scene': SCENE, 'emblem': EMBLEM, 'flag': FLAG}[kind]


def source(kind, rel, out):
    """the bytes to paint from, and a credit when the source is a found photo"""
    if kind == 'person':
        cached = os.path.join(out, 'src', rel.replace('.webp', '.jpg'))
        meta = cached + '.json'
        if os.path.exists(cached) and os.path.exists(meta):
            return open(cached, 'rb').read(), json.load(open(meta))
        pe = next(x for x in people() if rel.endswith('/' + slug(x['n']) + '.webp'))
        hit = sources.find(pe.get('wiki') or pe['n'])
        if not hit:
            raise RuntimeError('no free photograph found')
        data, credit = hit
        credit['n'] = pe['n']; credit['aka'] = pe.get('aka', [])
        os.makedirs(os.path.dirname(cached), exist_ok=True)
        open(cached, 'wb').write(data); json.dump(credit, open(meta, 'w'), ensure_ascii=False)
        return data, credit
    if kind == 'mascot':
        m = next(x for x in mascots() if rel.endswith('/' + x['id'] + '.webp'))
        return open(os.path.join(ROOT, 'img', 'msc', m['art'] + '.webp'), 'rb').read(), None
    return open(os.path.join(ROOT, rel), 'rb').read(), None


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
    # painted "white" paper is off-white and grainy: light and unsaturated is enough
    near = ((img.min(axis=2) > 200) & (img.max(axis=2).astype(int) - img.min(axis=2) < 28)).astype(np.uint8)
    near = cv2.morphologyEx(near, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
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
    if src_path:
        srcim = cv2.imread(src_path, cv2.IMREAD_UNCHANGED)
        sh, sw = srcim.shape[:2]
    else:
        sh, sw = (5, 4) if kind == 'person' else (1, 1)
    info = {}
    if kind == 'person':
        img, info = finish(img)
        img = fit_to(img, 4, 5)
    elif kind == 'mascot':
        img, info = finish(img)
        img = fit_to(img, 1, 1)
    elif kind in ('player', 'scene'):
        img, info = finish(img)
        img = fit_to(img, sw, sh)
    elif kind == 'flag':
        img = fit_to(img, sw, sh)
    else:
        img = key_white(img)
    # keep it light: never smaller than the source, at most 720px long side
    h, w = img.shape[:2]
    scale = min(1.0, 720 / max(h, w))
    if src_path:
        scale = max(scale, min(1.0, max(sh, sw) / max(h, w)))
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode('.webp', img, [cv2.IMWRITE_WEBP_QUALITY, 86])
    if not ok:
        raise RuntimeError('encode failed')
    return buf.tobytes(), info


def main():
    fetch_only = bool(os.environ.get('FETCH_ONLY'))
    key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not key and not fetch_only:
        sys.exit('GEMINI_API_KEY is not set')
    model = os.environ.get('GEMINI_MODEL', '').strip() or 'gemini-3-pro-image-preview'
    out = os.environ.get('OUT') or 'ai-batch'
    kinds = set(x for x in (os.environ.get('KINDS') or 'player,scene,emblem,flag,person,mascot').split(',') if x)
    shard, shards = int(os.environ.get('SHARD') or 0), int(os.environ.get('SHARDS') or 1)
    limit = int(os.environ.get('LIMIT') or 0)
    every = int(os.environ.get('COMMIT_EVERY') or 0)
    items, by_id = manifest()
    resolve = lambda s: by_id.get(s.strip(), s.strip())
    only = [resolve(x) for x in (os.environ.get('ONLY') or '').split(',') if x.strip()]
    force = set(resolve(x) for x in (os.environ.get('FORCE') or '').split(',') if x.strip())
    todo = [p for p in sorted(items) if (p in only if only else items[p] in kinds)]
    if fetch_only:
        todo = [p for p in todo if items[p] == 'person']
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
        t0 = time.time()
        rec = {'path': rel, 'kind': kind, 'model': model, 'player': next((k for k, v in by_id.items() if v == rel), None)}
        try:
            raw, credit = source(kind, rel, out)
            if credit: rec['credit'] = credit
            if fetch_only:
                if kind == 'person': print(f'· fetched {rel} <- {credit.get("article")} [{credit.get("l")}]', flush=True)
                continue
            pt.PROMPT_TEXT = prompt(kind, rel)
            mime = 'image/jpeg' if kind == 'person' else 'image/webp'
            res = pt.call(model, key, raw, mime, attempts=6)
            parts = (res.get('candidates') or [{}])[0].get('content', {}).get('parts', [])
            img = next((p.get('inlineData') or p.get('inline_data') for p in parts
                        if p.get('inlineData') or p.get('inline_data')), None)
            if not img:
                raise RuntimeError(f"no image ({(res.get('candidates') or [{}])[0].get('finishReason')})")
            data, info = postprocess(kind, base64.b64decode(img['data']),
                                     None if kind in ('person', 'mascot') else os.path.join(ROOT, rel))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(data)
            rec.update(ok=True, seconds=round(time.time() - t0, 1), edges=info)
            new += 1
            print(f'✓ {rel} [{kind}] {time.time() - t0:.0f}s', flush=True)
        except Exception as e:
            rec.update(ok=False, error=str(e)[:400])
            failed += 1
            print(f'✗ {rel} [{kind}] {str(e)[:200]}', flush=True)
            if 'HTTP 402' in str(e) or 'HTTP 403' in str(e):
                # no credit (or no access): every call after this fails the same way
                os.makedirs(os.path.dirname(st), exist_ok=True)
                json.dump(rec, open(st, 'w'), ensure_ascii=False)
                print('stopping: the Gemini account has no credit for this model', flush=True)
                break
        os.makedirs(os.path.dirname(st), exist_ok=True)
        json.dump(rec, open(st, 'w'), ensure_ascii=False)
        if every and new and new % every == 0:
            subprocess.run([os.path.join(HERE, 'publish.sh'), f'{new} more'], check=False)
        if limit and new >= limit:
            break
    print(f'shard {shard}/{shards}: {new} painted, {done} already done, {failed} failed')


if __name__ == '__main__':
    main()
