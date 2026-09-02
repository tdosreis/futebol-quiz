#!/usr/bin/env python3
"""Make every club crest sit at the same optical size on a square canvas.

The files come from Commons in whatever shape their uploader chose: 250x192
to 330x554, some with generous internal padding, some cropped tight, a few on
an opaque background. Dropped into the same disc they read as a jumble of
sizes — which is exactly what "the crests aren't standardised" means.

So each mark is trimmed of its own margin, scaled so its longest side is a
fixed fraction of the canvas, and centred on a square transparent field. After
this the CSS can treat all of them identically, because they really are.

Background handling:
  * transparent already      -> trim to the alpha bounding box
  * opaque, uniform border   -> that colour is the background: drop it, trim
  * opaque, no uniform border-> a flag or full-bleed artwork: keep it whole

Cropping and scaling is an adaptation, not a re-licence: the author and licence
recorded in CREDITS still apply and are unchanged.

  python3 tools/normalize_crests.py --dry-run
  python3 tools/normalize_crests.py
"""
import io, os, re, sys
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CANVAS = 384          # output square
FILL   = 0.94         # longest side of the mark, as a fraction of the canvas
TOL    = 26           # how close two colours must be to count as the same


def close(a, b):
    return all(abs(int(x) - int(y)) <= TOL for x, y in zip(a[:3], b[:3]))


def normalize(path, dry=False):
    im = Image.open(path)
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    note = ""

    alpha = im.getchannel("A")
    has_transparency = alpha.getextrema()[0] < 250

    if not has_transparency:
        corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
        if all(close(corners[0], c) for c in corners[1:]):
            bg = corners[0]
            # knock out the background colour, feathering nothing: these are
            # flat-colour plates, not photographs
            data = [(0, 0, 0, 0) if close(p, bg) else p for p in im.getdata()]
            im.putdata(data)
            note = "bg removed"
        else:
            note = "full-bleed (flag)"

    box = im.getchannel("A").getbbox()
    if box:
        im = im.crop(box)

    mw, mh = im.size
    scale = (CANVAS * FILL) / max(mw, mh)
    im = im.resize((max(1, round(mw * scale)), max(1, round(mh * scale))), Image.LANCZOS)

    out = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    out.paste(im, ((CANVAS - im.size[0]) // 2, (CANVAS - im.size[1]) // 2), im)
    if not dry:
        out.save(path, "PNG", optimize=True)
    return f"{w}x{h} -> {CANVAS}x{CANVAS}  {note}"


def main():
    dry = "--dry-run" in sys.argv
    src = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    seg = src[src.index("const LOGOS = {"):src.index("IMAGES — PLAYER PORTRAITS")]
    pairs = re.findall(r"(\w+):\s*'(img/[0-9a-f]+\.(?:png|jpg))'", seg)
    for key, rel in pairs:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            print(f"  !! {key}: missing {rel}")
            continue
        try:
            print(f"  {key:14s} {normalize(path, dry)}")
        except Exception as e:
            print(f"  !! {key}: {e}")
    print(f"\n{len(pairs)} crests {'checked' if dry else 'normalised'} "
          f"to {CANVAS}px square, mark at {int(FILL*100)}%")


main()
