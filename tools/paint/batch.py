"""Repaint every raster image in the app.

  players & scene photos -> layered brush painting (paint2.paint)
  club crests & mascots  -> gouache: flattened, brushed, on paper tooth,
                            with a hand-inked, slightly irregular edge
  flag images            -> painted cloth: brushed, with folds of light
"""
import cv2, numpy as np, os, sys, json, glob
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__))
from paint import paint, _paper

ROOT = '/home/user/futebol-quiz/'
OUT = '/tmp/claude-0/sp/paint/out/'
Q = [cv2.IMWRITE_WEBP_QUALITY, 84]

def grade(bgr, warm=4.0):
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    L, A, B = cv2.split(lab)
    L = 12 + L * (236 / 255)
    A = 128 + (A - 128) * .95 + 1.2
    B = 128 + (B - 128) * .95 + warm
    return cv2.cvtColor(cv2.merge([L, A, B]).clip(0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)

def tooth(bgr, seed, k=.2):
    h, w = bgr.shape[:2]
    t = _paper(h, w, seed)[..., None]
    b = bgr.astype(np.float32) / 255
    b = np.where(t > 0, b + (np.sqrt(b) - b) * t * k * 2, b - b * (1 - b) * (-t) * k * 2)
    return (b * 255).clip(0, 255).astype(np.uint8)

def paint_logo(im, seed):
    h0, w0 = im.shape[:2]
    alpha = im[:, :, 3].astype(np.float32) / 255 if im.shape[2] == 4 else np.ones((h0, w0), np.float32)
    rgb = im[:, :, :3]
    S = min(3, max(1, 600 / max(h0, w0)))
    W, H = int(w0 * S), int(h0 * S)
    big = cv2.resize(rgb, (W, H), interpolation=cv2.INTER_CUBIC)
    a = cv2.resize(alpha, (W, H), interpolation=cv2.INTER_LINEAR)
    # paint the colour out past the edge so the brush never drags in black
    fill = big.copy()
    m = (a < .5).astype(np.uint8)
    if m.any() and (1 - m).any():
        fill = cv2.inpaint(big, m, 3, cv2.INPAINT_TELEA)
    flat = cv2.edgePreservingFilter(fill, flags=cv2.RECURS_FILTER, sigma_s=8, sigma_r=.22)
    try:
        oil = cv2.xphoto.oilPainting(flat, 3, 1, cv2.COLOR_BGR2Lab)
        flat = cv2.addWeighted(oil, .45, flat, .55, 0)
    except Exception:
        pass
    col = tooth(grade(flat, 3), seed, .2)
    # a hand-inked edge: the outline wobbles a hair, and the ink pools there
    r = np.random.default_rng(seed)
    nz = cv2.GaussianBlur(r.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 3)
    nz /= nz.std() + 1e-6
    ab = cv2.GaussianBlur(a, (0, 0), 1.2)
    a2 = np.clip((ab - .5 + nz * .06) * 3 + .5, 0, 1) * (a > .02)
    edge = np.clip(1 - np.abs(ab - .5) * 4, 0, 1)
    col = (col.astype(np.float32) * (1 - edge[..., None] * .22)).clip(0, 255).astype(np.uint8)
    out = cv2.resize(col, (w0, h0), interpolation=cv2.INTER_AREA)
    ao = cv2.resize(a2, (w0, h0), interpolation=cv2.INTER_AREA)
    return np.dstack([out, (ao * 255).astype(np.uint8)])

def paint_flag(im, seed):
    h0, w0 = im.shape[:2]
    rgb = im[:, :, :3] if im.ndim == 3 else cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    S = min(4, max(1, 480 / max(h0, w0)))
    W, H = int(w0 * S), int(h0 * S)
    big = cv2.resize(rgb, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    # cloth: soft diagonal folds of light and shade
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u = (xx / W) * 2.2 + (yy / H) * .5
    fold = np.sin(u * np.pi * 2.1 + .6) * .5 + np.sin(u * np.pi * 4.3 + 1.7) * .22
    big = big * (1 + fold[..., None] * .09)
    big = big.clip(0, 255).astype(np.uint8)
    flat = cv2.edgePreservingFilter(big, flags=cv2.RECURS_FILTER, sigma_s=10, sigma_r=.25)
    try:
        oil = cv2.xphoto.oilPainting(flat, 4, 1, cv2.COLOR_BGR2Lab)
        flat = cv2.addWeighted(oil, .6, flat, .4, 0)
    except Exception:
        pass
    col = tooth(grade(flat, 3), seed, .26)
    out = cv2.resize(col, (w0, h0), interpolation=cv2.INTER_AREA)
    if im.ndim == 3 and im.shape[2] == 4:
        out = np.dstack([out, im[:, :, 3]])
    return out

def job(args):
    rel, kind = args
    src = ROOT + rel
    dst = OUT + rel
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im = cv2.imread(src, cv2.IMREAD_UNCHANGED)
    if im is None:
        return rel, 'unreadable'
    seed = abs(hash(rel)) % 100000
    try:
        if kind == 'photo':
            alpha = im[:, :, 3] if im.ndim == 3 and im.shape[2] == 4 else None
            out = paint(im[:, :, :3] if im.ndim == 3 else cv2.cvtColor(im, cv2.COLOR_GRAY2BGR), seed)
            if alpha is not None:
                out = np.dstack([out, alpha])
        elif kind == 'logo':
            if im.ndim == 2: im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGRA)
            if im.shape[2] == 3: im = cv2.cvtColor(im, cv2.COLOR_BGR2BGRA)
            out = paint_logo(im, seed)
        else:
            out = paint_flag(im, seed)
        cv2.imwrite(dst, out, Q)
        return rel, 'ok'
    except Exception as e:
        return rel, 'ERR ' + str(e)

if __name__ == '__main__':
    kinds = json.load(open(sys.argv[1]))
    only = sys.argv[2:]
    jobs = [(k, v) for k, v in kinds.items() if not only or k in only]
    with Pool(os.cpu_count()) as p:
        for i, (rel, st) in enumerate(p.imap_unordered(job, jobs), 1):
            if st != 'ok' or i % 50 == 0:
                print(i, rel, st, flush=True)
    print('done', len(jobs))
