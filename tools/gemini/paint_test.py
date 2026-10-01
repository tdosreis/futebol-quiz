#!/usr/bin/env python3
"""Gemini image-to-image test: repaint a few player photos as painterly
editorial / gouache realism, into a separate test folder.

Nothing in img/ is touched. The script reads the photos the album uses, sends
each one with the style prompt to a Gemini image model, and writes the
results — plus the originals and a side-by-side sheet — to OUT.

Environment:
  GEMINI_API_KEY  required; read from the environment and never printed
  GEMINI_MODEL    image model id (default gemini-3-pro-image-preview)
  STYLE           atelier (portrait study dissolving into paper) or gouache (painted edge to edge)
  PLAYERS         comma-separated album ids (default: five representative ones)
  OUT             output folder (default ai-test/local)
"""
import base64, json, os, re, sys, time, urllib.request, urllib.error

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
API = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
DEFAULT_PLAYERS = 'pele,ronaldo,messi,garrincha,didi'   # 1970 colour, modern stage, suit, full-length, b/w

# What every style keeps: the person, exactly.
IDENTITY = """Preserve, exactly as in the source photo: the person's identity and exact facial structure, \
realistic eyes, apparent age, hairstyle, facial hair, expression, head angle, pose, body proportions and \
clothing (shirt colours, badges, details). The result must remain immediately recognizable as the same \
person. Facial hair stays exactly as photographed — never add a beard or moustache. Where the face is \
small in the frame, paint it with extra care from the photo's own features rather than inventing them. \
A black-and-white photo becomes a monochrome painting (ink, charcoal and grey washes); a colour photo \
keeps its colours.

Do not: add anime features, enlarge the eyes, caricature, beautify, slim, de-age, change facial \
proportions, change the identity, add or remove people, add text, logos, pins, badges or signatures of \
any kind. Return only the image."""

STYLES = {
    # the look of run 1's Ronaldo: a portrait painted on paper, the subject finished, the rest left loose
    'atelier': """Repaint this photograph as a museum-quality hand-painted portrait study, in the manner of a \
contemporary master portrait painter working in gouache and watercolour on heavy cold-press paper.

The subject — face, hair, shoulders and kit — is fully and confidently painted: sculpted planes of \
light and shadow, expressive visible brushstrokes, warm skin glazes with cool shadow notes, crisp \
highlights in the eyes. Away from the subject the painting deliberately loosens: the background is \
re-imagined as soft abstract washes and a few gestural strokes in colours taken from the photo, with \
wet-in-wet blooms and drips, and towards the outer edges the paint thins and dissolves into bare, \
textured off-white paper, as in an unfinished artist's study. The paper grain shows through the thin \
washes. It must read unmistakably as a painting, never as a filtered photograph.""",
    # run 2: the whole frame painted, edge to edge
    'gouache': """Transform this photograph into a premium painterly illustration: editorial gouache realism, \
as if a skilled portrait painter had hand-painted this exact photograph, edge to edge. Subtle visible \
brushwork, sophisticated matte gouache texture, natural slightly warm colours, the background gently \
simplified while the subject stays detailed. The whole image, face and clothes included, must look \
brushed, not retouched. No borders, frames or vignettes.""",
}

def prompt_for(style):
    return STYLES.get(style, STYLES['atelier']) + '\n\n' + IDENTITY

def players():
    """album id -> (name, image path), read from the app itself"""
    src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    out = {}
    for m in re.finditer(r"\{\s*id:'([a-z0-9_]+)',\s*n:'([^']+)',\s*img:'(img/[0-9a-f]{16}\.webp)'", src):
        out[m.group(1)] = (m.group(2), m.group(3))
    return out

PROMPT_TEXT = ''

def call(model, key, img_bytes, mime, attempts=4):
    body = {
        'contents': [{'parts': [
            {'text': PROMPT_TEXT},
            {'inline_data': {'mime_type': mime, 'data': base64.b64encode(img_bytes).decode()}},
        ]}],
        'generationConfig': {'responseModalities': ['TEXT', 'IMAGE']},
    }
    req = urllib.request.Request(API.format(model=model), data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
    last = None
    for i in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            # the body explains the error; the key is in a header, so it is not in here
            last = f'HTTP {e.code}: {e.read()[:400].decode("utf-8", "replace")}'
            if e.code not in (429, 500, 502, 503, 504):
                break
        except Exception as e:
            last = f'{type(e).__name__}: {e}'
        time.sleep(4 * (2 ** i))
    raise RuntimeError(last)

def main():
    key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not key:
        sys.exit('GEMINI_API_KEY is not set')
    model = os.environ.get('GEMINI_MODEL', '').strip() or 'gemini-3-pro-image-preview'
    style = os.environ.get('STYLE', '').strip() or 'atelier'
    global PROMPT_TEXT
    PROMPT_TEXT = prompt_for(style)
    ids = [x.strip() for x in (os.environ.get('PLAYERS') or DEFAULT_PLAYERS).split(',') if x.strip()]
    out = os.environ.get('OUT') or os.path.join('ai-test', 'local')
    os.makedirs(out, exist_ok=True)
    pl = players()
    report = {'model': model, 'style': style, 'prompt': PROMPT_TEXT, 'results': []}
    for pid in ids:
        if pid not in pl:
            print(f'· {pid}: not an album id, skipped'); report['results'].append({'id': pid, 'ok': False, 'error': 'unknown id'}); continue
        name, rel = pl[pid]
        raw = open(os.path.join(ROOT, rel), 'rb').read()
        open(os.path.join(out, f'{pid}-original.webp'), 'wb').write(raw)
        t0 = time.time()
        try:
            res = call(model, key, raw, 'image/webp')
            parts = (res.get('candidates') or [{}])[0].get('content', {}).get('parts', [])
            img = next((p.get('inlineData') or p.get('inline_data') for p in parts
                        if p.get('inlineData') or p.get('inline_data')), None)
            note = ' '.join(p.get('text', '') for p in parts if p.get('text')).strip()
            if not img:
                reason = (res.get('candidates') or [{}])[0].get('finishReason') or res.get('promptFeedback')
                raise RuntimeError(f'no image returned ({reason}) {note[:200]}')
            ext = 'png' if 'png' in img.get('mimeType', img.get('mime_type', 'image/png')) else 'jpg'
            open(os.path.join(out, f'{pid}-painted.{ext}'), 'wb').write(base64.b64decode(img['data']))
            report['results'].append({'id': pid, 'name': name, 'source': rel, 'ok': True,
                                      'file': f'{pid}-painted.{ext}', 'seconds': round(time.time() - t0, 1), 'note': note[:300]})
            print(f'✓ {pid} ({name}) in {time.time() - t0:.1f}s')
        except Exception as e:
            report['results'].append({'id': pid, 'name': name, 'source': rel, 'ok': False, 'error': str(e)[:500]})
            print(f'✗ {pid} ({name}): {str(e)[:300]}')
        time.sleep(2)
    json.dump(report, open(os.path.join(out, 'report.json'), 'w'), ensure_ascii=False, indent=1)
    sheet(out, report)
    ok = sum(r['ok'] for r in report['results'])
    print(f'{ok}/{len(ids)} painted → {out}')
    if ok == 0:
        sys.exit(1)

def sheet(out, report):
    """original | painted, one row per player, to look at on a phone"""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    rows = []
    for r in report['results']:
        if not r.get('ok'):
            continue
        a = Image.open(os.path.join(out, f"{r['id']}-original.webp")).convert('RGB')
        b = Image.open(os.path.join(out, r['file'])).convert('RGB')
        H = 520
        a = a.resize((int(a.width * H / a.height), H)); b = b.resize((int(b.width * H / b.height), H))
        row = Image.new('RGB', (a.width + b.width + 30, H + 40), (24, 26, 20))
        row.paste(a, (0, 40)); row.paste(b, (a.width + 30, 40))
        ImageDraw.Draw(row).text((8, 10), f"{r['name']}  -  original | {report['model']} · {report.get('style', '')}", fill=(235, 228, 205))
        rows.append(row)
    if not rows:
        return
    W = max(r.width for r in rows)
    out_im = Image.new('RGB', (W, sum(r.height for r in rows)), (24, 26, 20))
    y = 0
    for r in rows:
        out_im.paste(r, (0, y)); y += r.height
    out_im.save(os.path.join(out, 'compare.jpg'), quality=88)

if __name__ == '__main__':
    main()
