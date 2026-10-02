#!/usr/bin/env python3
"""Swap the reviewed paintings from the gemini-batch staging tree into img/.

  python3 tools/gemini/integrate.py <staging ai-batch dir> [--reject reject.txt] [--dry]

Every staged image whose status is ok, and which is not on the reject list,
replaces the file of the same path in img/. Emblems are keyed once more, so
a crest painted on off-white paper loses its ground. Rejected or failed
images keep their original photograph — the app never shows a blank.
The originals stay in git history; reverting the commit restores them.
"""
import argparse, glob, json, os, re, sys
import cv2, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from batch import key_white


def rekey(im, src=None):
    """Take the paper ground out of a painted emblem. When the original crest
    has its own transparent outline and the painting lines up with it, that
    outline is the cut — it keeps a white ring that touches the paper (the
    Fenerbahçe ring) which keying by colour would eat. Otherwise, key by colour."""
    rgb = im[..., :3].copy()
    if im.shape[2] == 4:
        a = im[..., 3:4] / 255.
        rgb = (rgb * a + 255 * (1 - a)).astype(np.uint8)
    keyed = key_white(rgb)
    if src is None or src.ndim < 3 or src.shape[2] != 4:
        return keyed
    sa = src[..., 3]
    ys, xs = np.where(sa > 40)
    if not len(xs):
        return keyed
    sa = sa[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    ka = keyed[..., 3]
    ky, kx = np.where(ka > 40)
    if not len(kx):
        return keyed
    y0, y1, x0, x1 = ky.min(), ky.max() + 1, kx.min(), kx.max() + 1
    body = keyed[y0:y1, x0:x1].copy()
    # the painted emblem must have the original's proportions to borrow its outline
    if abs((x1 - x0) / (y1 - y0) - sa.shape[1] / sa.shape[0]) > .06:
        return keyed
    sa = cv2.resize(sa, (x1 - x0, y1 - y0), interpolation=cv2.INTER_LINEAR)
    inter = ((sa > 128) & (body[..., 3] > 128)).sum()
    union = ((sa > 128) | (body[..., 3] > 128)).sum()
    if union == 0 or inter / union < .86:
        return keyed
    # composite the painting's own pixels under the original outline: where the
    # paper was keyed away, the painted RGB is still in `rgb`
    out = np.dstack([rgb[y0:y1, x0:x1], cv2.GaussianBlur(sa, (0, 0), .6)])
    m = max(2, int(max(out.shape[:2]) * .04))
    return cv2.copyMakeBorder(out, m, m, m, m, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage')
    ap.add_argument('--reject', default='')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--kinds', default='player,scene,emblem,flag,person,mascot')
    a = ap.parse_args()
    reject = set()
    if a.reject and os.path.exists(a.reject):
        reject = {l.split('#')[0].strip() for l in open(a.reject) if l.split('#')[0].strip()}
    done = skipped = 0
    credits = {}
    for st in sorted(glob.glob(os.path.join(a.stage, 'status', '**', '*.json'), recursive=True)):
        r = json.load(open(st))
        rel = r['path']
        key = r.get('player') or rel
        if not r.get('ok') or rel in reject or key in reject or r['kind'] not in a.kinds.split(','):
            skipped += 1
            continue
        src = os.path.join(a.stage, rel)
        im = cv2.imread(src, cv2.IMREAD_UNCHANGED)
        if im is None:
            skipped += 1
            continue
        if r['kind'] == 'emblem':
            im = rekey(im, cv2.imread(os.path.join(ROOT, rel), cv2.IMREAD_UNCHANGED))
        # as large as the app ever draws it, at 2x, and no larger: the album
        # is cached on the phone, every kilobyte is paid for once per player
        cap = {'player': 640, 'scene': 640, 'emblem': 320, 'flag': 240, 'person': 480, 'mascot': 480}[r['kind']]
        h, w = im.shape[:2]
        if max(h, w) > cap:
            k = cap / max(h, w)
            im = cv2.resize(im, (round(w * k), round(h * k)), interpolation=cv2.INTER_AREA)
        dst = os.path.join(ROOT, rel)
        new_file = r['kind'] in ('person', 'mascot')     # these have no original to replace
        if not os.path.exists(dst) and not new_file:
            skipped += 1
            continue
        if new_file:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if r['kind'] == 'person' and r.get('credit'):
                credits[rel] = r['credit']
        if not a.dry:
            ok, buf = cv2.imencode('.webp', im, [cv2.IMWRITE_WEBP_QUALITY, 86])
            open(dst, 'wb').write(buf.tobytes())
        done += 1
    print(f'{done} paintings swapped in, {skipped} kept as they were')
    if not a.dry:
        write_lists(credits)


def write_lists(new_credits):
    """rewrite the PEOPLE and MSC_PAINTED lists in index.html from what is in img/"""
    path = os.path.join(ROOT, 'index.html')
    html = open(path, encoding='utf-8').read()
    m = re.search(r'/\*PEOPLE:start\*/\nconst PEOPLE = (\{.*?\});\n/\*PEOPLE:end\*/', html, re.S)
    people = json.loads(m.group(1)) if m and m.group(1).strip() != '{}' else {}
    for rel, c in new_credits.items():
        people[c['n']] = {'img': rel, 'a': c.get('a', 'Wikimedia Commons'), 'l': c.get('l', ''), 'aka': c.get('aka', [])}
    people = {n: e for n, e in people.items() if os.path.exists(os.path.join(ROOT, e['img']))}
    block = 'const PEOPLE = ' + json.dumps(people, ensure_ascii=False, indent=1, sort_keys=True) + ';'
    html = re.sub(r'(/\*PEOPLE:start\*/\n).*?(\n/\*PEOPLE:end\*/)', lambda x: x.group(1) + block + x.group(2), html, flags=re.S)
    clubs = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(ROOT, 'img', 'msc-club', '*.webp')))
    block = 'const MSC_PAINTED = new Set(' + json.dumps(clubs) + ');'
    html = re.sub(r'(/\*MSCPAINT:start\*/\n).*?(\n/\*MSCPAINT:end\*/)', lambda x: x.group(1) + block + x.group(2), html, flags=re.S)
    open(path, 'w', encoding='utf-8').write(html)
    print(f'lists: {len(people)} portraits, {len(clubs)} painted mascots')


if __name__ == '__main__':
    main()
