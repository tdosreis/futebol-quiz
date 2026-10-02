from PIL import Image, ImageFilter, ImageDraw
import sys
# subject bounding box as fractions of the source (x0, y0, x1, y1)
BOX = {
 'almirante':(.08,.1,.92,.6),'azulao':(.18,.18,.88,.9),'cachorro':(.25,.33,.42,.8),
 'caravela':(.2,.12,.85,.78),'cobra':(0,.35,.73,.65),'coelho':(.1,.12,.7,.88),
 'dourado':(.02,.2,.98,.5),'dragao':(.2,.15,.78,.85),'elefante':(.1,.25,.9,.97),
 'figueira':(0,.08,1,.95),'furacao':(.15,0,.85,.75),'galo':(.42,.06,.7,.75),
 'leao':(.2,.2,1,.83),'macaca':(.38,.28,.72,.78),'mosqueteiro':(.2,.02,.8,.92),
 'pantera':(.2,.15,.85,.95),'peixe':(.33,.18,.97,.55),'periquito':(.3,.15,.88,.9),
 'poDeArroz':(.1,.1,.9,.9),'porco':(.25,.1,.66,.75),'raposa':(0,.1,.72,.85),
 'saci':(.2,.08,.66,.95),'santo':(.25,.02,.75,.98),'tigre':(.08,.05,.86,.85),
 'timbu':(.2,.04,.86,.66),'touro':(0,.1,.9,.95),'tubarao':(.15,0,1,.75),
 'urubu':(0,.03,.66,.93),
}
FILL = .84   # share of the disc's diameter the subject may take
def crop(art, src, out, n=480):
    import numpy as np
    im = Image.open(src).convert('RGB'); W, H = im.size
    x0, y0, x1, y1 = BOX[art]; x0*=W; x1*=W; y0*=H; y1*=H
    big = max(x1-x0, y1-y0); side = big / FILL
    # rather than pad, let the subject fill a little more of the disc
    if side > min(W, H) and big / min(W, H) <= .97: side = min(W, H)
    cx, cy = (x0+x1)/2, (y0+y1)/2
    L, T = cx-side/2, cy-side/2
    if side <= W: L = min(max(L, 0), W-side)
    if side <= H: T = min(max(T, 0), H-side)
    s = round(side); L, T = round(L), round(T)
    pl, pt = max(0, -L), max(0, -T)
    pr, pb = max(0, L+s-W), max(0, T+s-H)
    a = np.asarray(im)
    if pl or pt or pr or pb:
        # mirror the photo into the padding and blur only what was mirrored,
        # fading into the real edge so there is no seam
        p = np.pad(a, ((pt, pb), (pl, pr), (0, 0)), mode='reflect' if max(pt,pb) < H and max(pl,pr) < W else 'edge')
        P = Image.fromarray(p); B = P.filter(ImageFilter.GaussianBlur(s/30))
        m = np.zeros(p.shape[:2], np.float32); m[pt:pt+H, pl:pl+W] = 1
        f = max(4, s//40)
        m = np.asarray(Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(f)), np.float32)/255
        m = np.where(np.pad(np.ones((H, W)), ((pt, pb), (pl, pr))) > 0, np.maximum(m, 0), m)
        q = (p*m[..., None] + np.asarray(B)*(1-m[..., None])).astype(np.uint8)
        im = Image.fromarray(q); L += pl; T += pt
    c = im.crop((L, T, L+s, T+s)).resize((n, n), Image.LANCZOS)
    c.save(out, 'WEBP', quality=84, method=6)
if __name__ == '__main__':
    import glob, os
    for art in BOX:
        crop(art, f'/tmp/claude-0/sp/msrc/{art}.jpg', f'/tmp/claude-0/sp/msrc/out/{art}.webp')
    fs = sorted(glob.glob('/tmp/claude-0/sp/msrc/out/*.webp')); D = 200
    sheet = Image.new('RGB', (7*D, 4*(D+20)), 'white'); d = ImageDraw.Draw(sheet)
    for i, f in enumerate(fs):
        im = Image.open(f).resize((D, D)); m = Image.new('L', (D, D), 0); ImageDraw.Draw(m).ellipse((0, 0, D, D), fill=255)
        x, y = (i%7)*D, (i//7)*(D+20); sheet.paste(im, (x, y), m); d.text((x+5, y+D+3), os.path.basename(f)[:-5], fill='black')
    sheet.save('/tmp/claude-0/sp/msrc/sheet.png')
