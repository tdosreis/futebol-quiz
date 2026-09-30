"""Painterly realism, stroke by stroke.

A layered brush renderer (after Hertzmann, "Painterly Rendering with Curved
Brush Strokes of Multiple Sizes"): the canvas is laid in with a broad wash,
then painted over in passes of smaller and smaller brushes. Each stroke takes
its colour from the photograph and runs across the grain of the form (along
the edges, not through them), and a pass only paints where the canvas still
differs from the photo — so broad areas stay loose and painterly while the
face, which differs most, gets the finest brush. Identity comes entirely from
the photograph; only the medium changes.
"""
import cv2, numpy as np, sys

CASC = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def _paper(h, w, seed):
    r = np.random.default_rng(seed)
    n = cv2.GaussianBlur(r.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 1.1)
    m = cv2.GaussianBlur(r.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 9)
    t = n / (n.std() + 1e-6) * .6 + m / (m.std() + 1e-6) * .4
    return np.clip(t / 3, -1, 1)

def _faces(gray):
    try:
        f = CASC.detectMultiScale(gray, 1.1, 5, minSize=(max(24, gray.shape[1] // 12),) * 2)
        return list(f)
    except Exception:
        return []

def paint(img, seed=0, style='gouache'):
    r = np.random.default_rng(seed)
    h0, w0 = img.shape[:2]
    S = 720 / max(h0, w0)
    S = min(2.4, max(1.0, S))
    W, H = int(w0 * S), int(h0 * S)
    ref = cv2.resize(img, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    gray = cv2.cvtColor(ref.astype(np.uint8), cv2.COLOR_BGR2GRAY)

    # where the fine brush is allowed: faces (and a margin), plus strong detail
    fmask = np.zeros((H, W), np.float32)
    for (x, y, w, h) in _faces(gray):
        cv2.ellipse(fmask, (x + w // 2, y + int(h * .55)), (int(w * .75), int(h * .95)), 0, 0, 360, 1, -1)
    fmask = cv2.GaussianBlur(fmask, (0, 0), 8)
    # the sitter: portraits put the subject in the middle and the head high,
    # so the fine brushes stay there and the edges of the picture dissolve
    smask = np.zeros((H, W), np.float32)
    cv2.ellipse(smask, (W // 2, int(H * .45)), (int(W * .40), int(H * .52)), 0, 0, 360, 1, -1)
    smask = np.maximum(cv2.GaussianBlur(smask, (0, 0), max(W, H) * .07), fmask)

    # underpainting: a broad, warm wash of the picture
    canvas = cv2.GaussianBlur(ref, (0, 0), 14)
    base = max(W, H) / 720
    radii = [int(18 * base), int(9 * base), int(5 * base), max(2, int(2.6 * base))]
    for li, R in enumerate(radii):
        refb = cv2.GaussianBlur(ref, (0, 0), max(.8, R * .45))
        g = cv2.cvtColor(refb.clip(0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
        gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
        # smooth the orientation field so strokes flow instead of jitter
        cxx = cv2.GaussianBlur(gx * gx, (0, 0), R); cyy = cv2.GaussianBlur(gy * gy, (0, 0), R)
        cxy = cv2.GaussianBlur(gx * gy, (0, 0), R)
        theta = .5 * np.arctan2(2 * cxy, cxx - cyy) + np.pi / 2     # along the edges
        coh = np.sqrt((cxx - cyy) ** 2 + 4 * cxy ** 2) / (cxx + cyy + 1e-3)
        diff = np.linalg.norm(canvas - refb, axis=2)
        grid = max(2, int(R * .9))
        T = 22 if li < len(radii) - 1 else 14
        pts = []
        for y in range(grid // 2, H, grid):
            for x in range(grid // 2, W, grid):
                x0, y0 = max(0, x - grid // 2), max(0, y - grid // 2)
                win = diff[y0:y + grid // 2 + 1, x0:x + grid // 2 + 1]
                if win.size == 0: continue
                err = win.mean()
                if li >= len(radii) - 2 and smask[y, x] < .35 and err < 55:
                    continue                                  # fine brushes: the sitter only
                if err > T or li == 0:
                    iy, ix = np.unravel_index(np.argmax(win), win.shape)
                    pts.append((x0 + ix, y0 + iy))
        r.shuffle(pts)
        th = max(1, int(R * (1.1 if li else 1.3)))
        for (x, y) in pts:
            c = refb[y, x]
            # a hand never mixes the same colour twice
            c = np.clip(c * (1 + r.normal(0, .035)) + r.normal(0, 3, 3), 0, 255)
            ang = theta[y, x] + r.normal(0, .12)
            L = R * (1.6 + 2.2 * min(1, coh[y, x] * 1.4)) * (1.3 if li == 0 else 1)
            # a short curved stroke: two segments that follow the field
            p = [(float(x), float(y))]
            px, py = float(x), float(y)
            for _ in range(2):
                dx, dy = np.cos(ang) * L / 2, np.sin(ang) * L / 2
                px, py = px + dx, py + dy
                ix, iy = int(min(W - 1, max(0, px))), int(min(H - 1, max(0, py)))
                ang2 = theta[iy, ix]
                if np.cos(ang2 - ang) < 0: ang2 += np.pi
                ang = ang * .5 + ang2 * .5
                p.append((px, py))
            # and back the other way from the start
            q = (x - np.cos(theta[y, x]) * L / 3, y - np.sin(theta[y, x]) * L / 3)
            poly = np.array([q] + p, np.int32).reshape(-1, 1, 2)
            cv2.polylines(canvas, [poly], False, c.tolist(), th, cv2.LINE_AA)
    # the edges of the picture thin out to the paper, as a painter leaves them
    paper = np.array([228, 236, 240], np.float32)
    fade = ((1 - smask) * .16)[..., None]
    out = (canvas * (1 - fade) + paper * fade).clip(0, 255)

    # the palette: gouache warmth, lifted shadows, softer chroma
    lab = cv2.cvtColor(out.astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
    L_, A_, B_ = cv2.split(lab)
    L_ = 14 + L_ * (232 / 255)
    A_ = 128 + (A_ - 128) * .94 + 1.5
    B_ = 128 + (B_ - 128) * .94 + 4.5
    out = cv2.cvtColor(cv2.merge([L_, A_, B_]).clip(0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR).astype(np.float32)

    # the paper/canvas tooth under the paint (soft light)
    tex = _paper(H, W, seed)[..., None]
    b = out / 255
    k = .22
    b = np.where(tex > 0, b + (np.sqrt(b) - b) * tex * k * 2, b - b * (1 - b) * (-tex) * k * 2)
    out = (b * 255).clip(0, 255).astype(np.uint8)
    return cv2.resize(out, (w0, h0), interpolation=cv2.INTER_AREA)

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    im = cv2.imread(src, cv2.IMREAD_UNCHANGED)
    alpha = im[:, :, 3] if im.ndim == 3 and im.shape[2] == 4 else None
    out = paint(im[:, :, :3])
    if alpha is not None: out = np.dstack([out, alpha])
    cv2.imwrite(dst, out, [cv2.IMWRITE_WEBP_QUALITY, 86])
