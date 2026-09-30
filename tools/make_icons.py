#!/usr/bin/env python3
"""Every icon the app ships, drawn from one picture: icons/icon-source.png.

That file is the 512px Play Store icon — an ivory question mark with a brass
dot on pitch green. The installed app does not use the Play listing's icon: the
launcher icon, the adaptive-icon layers and the launch splash are resources
inside the Android bundle, and the web manifest has its own set. They were all
still the old football. This regenerates the lot from the one source, so they
cannot drift apart again.

  python3 tools/make_icons.py

The source is flat — three colours and under one level of noise — so rather
than resize the picture, the question mark and the dot are lifted out as two
masks, redrawn over a background of exactly one colour, and scaled from there.
That is what makes a proper adaptive icon possible: Android wants the glyph on
its own transparent layer, small enough to survive every launcher's mask.

The masks are upscaled to 2048 and their edges re-sharpened before anything is
drawn, because the splash wants 1200px and a 512px picture blown up to that is
soft at the edges. A flat shape can be upscaled cleanly; a photograph could not.
"""
import os
import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "icons", "icon-source.png")
RES = os.path.join(ROOT, "android", "app", "src", "main", "res")

MASTER = 2048          # the size the glyph is rebuilt at before scaling down

DENS = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}


def colours(rgb):
    """Background, ivory and brass, measured off the picture itself."""
    h, w, _ = rgb.shape
    edge = np.concatenate([rgb[:3].reshape(-1, 3), rgb[-3:].reshape(-1, 3),
                           rgb[:, :3].reshape(-1, 3), rgb[:, -3:].reshape(-1, 3)])
    bg = edge.mean(0)
    far = np.linalg.norm(rgb - bg, axis=2) > 120
    ivory = rgb[far & (rgb[..., 2] > 150)].mean(0)
    brass = rgb[far & (rgb[..., 2] < 110)].mean(0)
    return bg, ivory, brass


def coverage(rgb, bg, fgs):
    """How much of each pixel is each foreground colour laid over `bg`: its
    projection on the line between the two. An anti-aliased edge comes out
    fractional, background noise at zero.

    Each pixel belongs to one line only — whichever it lies closest to. Taking
    the projection alone is not enough: ivory is further from the green than
    brass is, in nearly the same direction, so the whole question mark projects
    past the end of the brass line and came out as solid brass."""
    alphas, resid = [], []
    for fg in fgs:
        d = fg - bg
        a = np.clip(((rgb - bg) @ d) / (d @ d), 0, 1)
        alphas.append(a)
        resid.append(np.linalg.norm((rgb - bg) - a[..., None] * d, axis=2))
    owner = np.argmin(np.stack(resid), axis=0)
    return [a * (owner == i) for i, a in enumerate(alphas)]


def master_mask(a512):
    """512px coverage to a crisp 2048px one: bicubic up, then the edge ramp —
    now four pixels wide — pulled back to about one."""
    im = Image.fromarray((a512 * 255).astype(np.uint8)).resize((MASTER, MASTER), Image.BICUBIC)
    a = np.asarray(im, dtype=np.float32) / 255
    a = np.clip((a - 0.5) / 0.32 + 0.5, 0, 1)
    return a


def hexc(c):
    return "#%02X%02X%02X" % tuple(int(round(x)) for x in c)


class Icon:
    def __init__(self):
        rgb = np.asarray(Image.open(SRC).convert("RGB"), dtype=np.float32)
        assert rgb.shape[:2] == (512, 512), "icon-source.png should be 512x512"
        self.bg, self.ivory, self.brass = colours(rgb)
        a_ivory, a_brass = coverage(rgb, self.bg, [self.ivory, self.brass])
        self.a_ivory = master_mask(a_ivory)
        self.a_brass = master_mask(a_brass)

    def glyph(self, size, mono=False):
        """The question mark and dot alone on transparency, at `size` px for
        what was 512px in the source."""
        def layer(a, c):
            px = np.zeros((MASTER, MASTER, 4), np.uint8)
            px[..., :3] = (255, 255, 255) if mono else np.round(c)
            px[..., 3] = np.round(a * 255)
            return Image.fromarray(px)
        g = layer(self.a_ivory, self.ivory)
        g.alpha_composite(layer(self.a_brass, self.brass))
        return g.resize((size, size), Image.LANCZOS)

    def full(self, size):
        """The whole square icon, as on the Play listing."""
        im = Image.new("RGBA", (size, size), tuple(int(round(x)) for x in self.bg) + (255,))
        im.alpha_composite(self.glyph(size))
        return im.convert("RGB")

    def foreground(self, px, mono=False):
        """An adaptive-icon layer: 108dp square, of which launchers show the
        middle 72dp. The glyph is drawn so that 72dp holds exactly what the
        512px source holds, which keeps its proportion identical to the Play
        icon under a square mask and well inside the 66dp safe circle under
        a round one."""
        inner = round(px * 72 / 108)
        im = Image.new("RGBA", (px, px), (0, 0, 0, 0))
        off = (px - inner) // 2
        im.alpha_composite(self.glyph(inner, mono), (off, off))
        return im


def save(im, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, "PNG", optimize=True)
    return os.path.relpath(path, ROOT)


def main():
    ic = Icon()
    print("background %s  ivory %s  brass %s" % (hexc(ic.bg), hexc(ic.ivory), hexc(ic.brass)))

    # sanity: the rebuilt icon at 512 should be the source, give or take the noise
    back = np.asarray(ic.full(512), dtype=np.float32)
    src = np.asarray(Image.open(SRC).convert("RGB"), dtype=np.float32)
    diff = np.abs(back - src).mean()
    print("rebuilt 512 vs source: mean difference %.2f / 255" % diff)
    assert diff < 3, "the rebuilt icon has drifted from the source"

    out = []
    for name, f in DENS.items():
        d = os.path.join(RES, "mipmap-" + name)
        out.append(save(ic.full(round(48 * f)), os.path.join(d, "ic_launcher.png")))
        out.append(save(ic.full(round(82 * f)), os.path.join(d, "ic_maskable.png")))
        out.append(save(ic.foreground(round(108 * f)), os.path.join(d, "ic_launcher_foreground.png")))
        out.append(save(ic.foreground(round(108 * f), mono=True), os.path.join(d, "ic_launcher_monochrome.png")))
        out.append(save(ic.full(round(300 * f)), os.path.join(RES, "drawable-" + name, "splash.png")))
    for s in (72, 96, 128, 144, 152, 192, 384, 512):
        out.append(save(ic.full(s), os.path.join(ROOT, "icons", "icon-%d.png" % s)))
    out.append(save(ic.full(512), os.path.join(ROOT, "android", "store_icon.png")))
    print("%d files written" % len(out))
    print("launcher background colour for colors.xml / build.gradle: %s" % hexc(ic.bg))


if __name__ == "__main__":
    main()
