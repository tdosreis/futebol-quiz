#!/usr/bin/env python3
"""Swap the reviewed paintings from the gemini-batch staging tree into img/.

  python3 tools/gemini/integrate.py <staging ai-batch dir> [--reject reject.txt] [--dry]

Every staged image whose status is ok, and which is not on the reject list,
replaces the file of the same path in img/. Emblems are keyed once more, so
a crest painted on off-white paper loses its ground. Rejected or failed
images keep their original photograph — the app never shows a blank.
The originals stay in git history; reverting the commit restores them.
"""
import argparse, glob, json, os, sys
import cv2, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from batch import key_white


def rekey(im):
    rgb = im[..., :3].copy()
    if im.shape[2] == 4:
        a = im[..., 3:4] / 255.
        rgb = (rgb * a + 255 * (1 - a)).astype(np.uint8)
    return key_white(rgb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage')
    ap.add_argument('--reject', default='')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    reject = set()
    if a.reject and os.path.exists(a.reject):
        reject = {l.split('#')[0].strip() for l in open(a.reject) if l.split('#')[0].strip()}
    done = skipped = 0
    for st in sorted(glob.glob(os.path.join(a.stage, 'status', '**', '*.json'), recursive=True)):
        r = json.load(open(st))
        rel = r['path']
        key = r.get('player') or rel
        if not r.get('ok') or rel in reject or key in reject:
            skipped += 1
            continue
        src = os.path.join(a.stage, rel)
        im = cv2.imread(src, cv2.IMREAD_UNCHANGED)
        if im is None:
            skipped += 1
            continue
        if r['kind'] == 'emblem':
            im = rekey(im)
        # as large as the app ever draws it, at 2x, and no larger: the album
        # is cached on the phone, every kilobyte is paid for once per player
        cap = {'player': 640, 'scene': 640, 'emblem': 320, 'flag': 240}[r['kind']]
        h, w = im.shape[:2]
        if max(h, w) > cap:
            k = cap / max(h, w)
            im = cv2.resize(im, (round(w * k), round(h * k)), interpolation=cv2.INTER_AREA)
        dst = os.path.join(ROOT, rel)
        if not os.path.exists(dst):
            skipped += 1
            continue
        if not a.dry:
            ok, buf = cv2.imencode('.webp', im, [cv2.IMWRITE_WEBP_QUALITY, 86])
            open(dst, 'wb').write(buf.tobytes())
        done += 1
    print(f'{done} paintings swapped in, {skipped} kept as they were')


if __name__ == '__main__':
    main()
