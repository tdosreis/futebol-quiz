#!/usr/bin/env python3
"""The painted materials the app's frame is built from — made procedurally,
so they match the paintings without another image model call.

  img/atelier/paper-night.webp   tileable: indigo-umber paper, grain + faint blooms
  img/atelier/paper-day.webp     tileable: warm cream cold-press paper
  img/atelier/wash-*.webp        transparent watercolour washes (pigment pooled at the edge)
  img/atelier/stroke-*.webp      alpha masks: a gouache brushstroke, a painted card, a dab

Run: python3 tools/make_atelier.py  (deterministic: same seeds, same files)
"""
import os
import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'img', 'atelier')
os.makedirs(OUT, exist_ok=True)


def tile_noise(n, sigma, rng):
    """Gaussian-blurred noise that wraps at the edges (tileable)."""
    p = int(sigma * 3) + 2
    base = rng.normal(0, 1, (n, n)).astype(np.float32)
    big = np.pad(base, p, mode='wrap')
    out = cv2.GaussianBlur(big, (0, 0), sigma)[p:-p, p:-p]
    return (out - out.mean()) / (out.std() + 1e-6)


def noise(h, w, sigma, rng):
    out = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), sigma)
    return (out - out.mean()) / (out.std() + 1e-6)


def save(name, img, q=82):
    cv2.imwrite(os.path.join(OUT, name), img, [cv2.IMWRITE_WEBP_QUALITY, q])
    print(name, img.shape, os.path.getsize(os.path.join(OUT, name)) // 1024, 'KB')


def paper(name, base, tint_a, tint_b, grain, bloom, seed, n=512):
    rng = np.random.default_rng(seed)
    # cold-press tooth: two scales of grain, slightly directional fibres
    fine = tile_noise(n, .7, rng)
    tooth = tile_noise(n, 2.2, rng)
    fib = tile_noise(n, 1.0, rng)
    fib = cv2.GaussianBlur(np.pad(fib, 8, mode='wrap'), (0, 0), sigmaX=4, sigmaY=.6)[8:-8, 8:-8]
    fib /= fib.std() + 1e-6
    t = fine * .45 + tooth * .4 + fib * .25
    # large soft blooms of two tints, like a wash laid unevenly
    b1 = tile_noise(n, 48, rng); b2 = tile_noise(n, 70, rng)
    img = np.ones((n, n, 3), np.float32) * np.array(base, np.float32)
    img += (np.array(tint_a, np.float32) - base) * (np.clip(b1, 0, 3) / 3 * bloom)[..., None]
    img += (np.array(tint_b, np.float32) - base) * (np.clip(b2, 0, 3) / 3 * bloom)[..., None]
    img *= (1 + t * grain)[..., None]
    save(name, np.clip(img, 0, 255).astype(np.uint8))


def wash(name, w, h, color, seed, density=.85, edge=.55, shape='blob'):
    """A watercolour wash: soft body, darker pooled rim, granulation, a few
    blooms (backruns), on transparency."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    if shape == 'blob':
        d = np.sqrt(((xx - w / 2) / (w * .42)) ** 2 + ((yy - h / 2) / (h * .40)) ** 2)
        field = 1 - d
    elif shape == 'band':       # a horizontal sweep, ragged above and below
        d = np.abs((yy - h / 2) / (h * .34))
        field = 1 - d - np.abs((xx - w / 2) / (w * .5)) ** 6 * .8
    else:                       # 'corner': pooled into the top-left
        d = np.sqrt((xx / (w * .9)) ** 2 + (yy / (h * .9)) ** 2)
        field = 1 - d
    field = field + noise(h, w, min(w, h) * .09, rng) * .16 + noise(h, w, min(w, h) * .03, rng) * .035
    a = np.clip(field * 5, 0, 1)
    a = cv2.GaussianBlur(a, (0, 0), .8)
    # pigment pools where the wash dried: a darker line just inside the edge
    rim = np.clip(1 - np.abs(field * 5 - .15) * 5, 0, 1)
    gran = noise(h, w, .7, rng) * .3 + noise(h, w, min(w, h) * .05, rng) * .7
    # a wash is darker where it was laid first and paler where it ran thin
    body = a * density * (.72 + .18 * np.clip(gran, -1.5, 1.5) / 1.5 + .1 * np.clip(field * 2, 0, 1))
    # backruns: pale cauliflower blooms with a dark edge
    for _ in range(2):
        cx, cy = rng.uniform(.25, .75) * w, rng.uniform(.3, .7) * h
        r = rng.uniform(.08, .16) * min(w, h)
        dd = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r + noise(h, w, r * .25, rng) * .12
        body *= 1 - np.clip(1 - dd, 0, 1) * .35
        body += np.clip(1 - np.abs(dd - 1) * 7, 0, 1) * a * .06
    alpha = np.clip(body + rim * a * edge * .5, 0, 1)
    # never touch the image's own edge: a wash cut by its rectangle shows a
    # hard straight line on the page
    win = np.clip(np.minimum(np.minimum(xx, w - 1 - xx) / (w * .14), np.minimum(yy, h - 1 - yy) / (h * .14)), 0, 1)
    alpha *= win * win * (3 - 2 * win)
    c = np.array(color, np.float32)
    rgb = np.ones((h, w, 3), np.float32) * c * (1 - .35 * rim[..., None] * edge)
    out = np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8)
    save(name, out)


def stroke(name, w, h, seed, kind='bar'):
    """Alpha mask of a single gouache stroke: ragged top/bottom edges, a
    loaded start, dry-brush streaks breaking up toward the end."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = xx / w; v = yy / h
    edge_top = .10 + noise(1, w, w * .02, rng)[0] * .025 + noise(1, w, w * .004, rng)[0] * .008
    edge_bot = .90 + noise(1, w, w * .02, rng)[0] * .025 + noise(1, w, w * .004, rng)[0] * .008
    if kind == 'card':
        edge_top = .04 + noise(1, w, w * .03, rng)[0] * .01
        edge_bot = .96 + noise(1, w, w * .03, rng)[0] * .01
    inside = np.clip(np.minimum(v - edge_top[None, :], edge_bot[None, :] - v) * h / 2.2, 0, 1)
    # ends: a rounded loaded start on the left, a dry trailing end on the right
    lx = .035 if kind == 'bar' else .015
    left = np.clip((u - lx - noise(h, 1, h * .08, rng)[:, :1] * .012) * w / 3, 0, 1)
    right = np.clip((1 - lx - u + noise(h, 1, h * .08, rng)[:, :1] * .02) * w / 3, 0, 1)
    a = inside * left * right
    # bristle streaks along the stroke, strongest at the dry end
    streak = noise(h, w, .6, rng)
    streak = cv2.GaussianBlur(streak, (0, 0), sigmaX=w * .06, sigmaY=.6)
    streak /= streak.std() + 1e-6
    dry = np.clip((u - .55) / .45, 0, 1) ** 1.6 if kind == 'bar' else np.zeros_like(u) + .08
    keep = np.clip(1 - dry * np.clip(-streak * .9 + .2, 0, 1) * 1.4, 0, 1)
    edge_dry = np.clip(1 - np.clip(-streak, 0, 3) * .35 * (1 - inside), 0, 1)
    a = a * keep * edge_dry
    # paint is not flat: a little density variation inside
    a *= .93 + .07 * np.clip(noise(h, w, 14, rng), -1, 1)
    save(name, np.dstack([np.full((h, w, 3), 255, np.uint8), (np.clip(a, 0, 1) * 255).astype(np.uint8)]), 90)


def dab(name, n, seed):
    """A round dab of gouache: a slightly irregular disc, a few bristle
    marks at the rim."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    ang = np.arctan2(yy - n / 2, xx - n / 2)
    r = np.sqrt((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / (n * .44)
    wob = sum(rng.uniform(-.035, .035) * np.cos(k * ang + rng.uniform(0, 6.3)) for k in range(2, 9))
    field = 1 - r + wob + noise(n, n, n * .02, rng) * .03
    a = np.clip(field * n * .08, 0, 1)
    a *= .94 + .06 * np.clip(noise(n, n, n * .06, rng), -1, 1)
    save(name, np.dstack([np.full((n, n, 3), 255, np.uint8), (a * 255).astype(np.uint8)]), 90)


def filled(name, mask, bgr, alpha, solid=False, seed=0):
    """A painted card in one colour: the shape of a stroke mask, filled, with
    the paint a touch denser at the edge where it pooled. A solid card (a
    paper slip) keeps only the torn outline: it is opaque inside, and its
    texture is in the colour — a soft wash and paper tooth — not the alpha,
    which on the dark page would show through as mottling."""
    m = cv2.imread(os.path.join(OUT, mask), cv2.IMREAD_UNCHANGED)[..., 3].astype(np.float32) / 255
    rim = np.clip(m - cv2.GaussianBlur(m, (0, 0), 3), 0, 1) * 2.2
    if solid:
        m = np.clip((cv2.GaussianBlur(m, (0, 0), 2.5) - .35) * 4, 0, 1)
        h, w = m.shape
        rng = np.random.default_rng(seed)
        tone = 1 + noise(h, w, 40, rng)[..., None] * .025 + noise(h, w, .8, rng)[..., None] * .018
        edge = np.clip(1 - cv2.GaussianBlur(m, (0, 0), 6), 0, 1)[..., None]
        rgb = np.array(bgr, np.float32) * tone * (1 - edge * .22)
        save(name, np.dstack([np.clip(rgb, 0, 255), m * alpha * 255]).astype(np.uint8), 88)
        return
    a = np.clip(m * alpha * (1 + rim * .6), 0, 1)
    rgb = np.ones(m.shape + (3,), np.float32) * np.array(bgr, np.float32)
    save(name, np.dstack([rgb, a * 255]).astype(np.uint8), 88)


if __name__ == '__main__':
    paper('paper-night.webp', base=(40, 28, 22), tint_a=(70, 40, 28), tint_b=(34, 36, 48), grain=.10, bloom=.6, seed=3)
    paper('paper-day.webp', base=(226, 238, 244), tint_a=(205, 222, 236), tint_b=(214, 232, 230), grain=.045, bloom=.5, seed=4)
    # BGR colours: indigo, umber, ochre-gold, viridian
    wash('wash-indigo.webp', 900, 640, (96, 52, 40), 11, density=.7)
    wash('wash-umber.webp', 760, 560, (42, 68, 120), 12, density=.55)
    wash('wash-gold.webp', 820, 300, (70, 160, 214), 13, density=.75, shape='band')
    wash('wash-green.webp', 700, 520, (82, 110, 46), 14, density=.5)
    stroke('stroke-bar.webp', 900, 220, 21, 'bar')
    stroke('stroke-card.webp', 600, 420, 22, 'card')
    stroke('stroke-tab.webp', 240, 240, 23, 'card')
    dab('stroke-dab.webp', 200, 24)
    filled('card-day.webp', 'stroke-card.webp', (240, 249, 253), .82)
    filled('card-night.webp', 'stroke-card.webp', (200, 226, 236), .13)
    filled('card-day-on.webp', 'stroke-card.webp', (228, 243, 250), .97)
    filled('card-night-on.webp', 'stroke-card.webp', (200, 226, 236), .22)
    # answer slips: ivory paper laid on the page, and the same slip painted
    # gold (chosen), green (right) and red (wrong)
    filled('slip-ivory.webp', 'stroke-card.webp', (214, 232, 242), .97, solid=True, seed=31)
    filled('slip-gold.webp', 'stroke-card.webp', (118, 196, 232), .98, solid=True, seed=31)
    filled('slip-good.webp', 'stroke-card.webp', (150, 206, 166), .98, solid=True, seed=31)
    filled('slip-bad.webp', 'stroke-card.webp', (150, 156, 222), .98, solid=True, seed=31)
