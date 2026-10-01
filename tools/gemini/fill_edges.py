import cv2, numpy as np
def paper_mask(img):
    """near-white, low-saturation pixels: unpainted paper"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return ((hsv[..., 2] > 222) & (hsv[..., 1] < 34)).astype(np.uint8)

def finish(img, max_trim=.12):
    """Trim unpainted paper off the edges, then paint any left in the margin
    from the surrounding colour, and return the original size and shape."""
    h, w = img.shape[:2]
    m = paper_mask(img)
    def side(get, n, lim):
        k = 0
        while k < lim and get(k).mean() > .5:
            k += 1
        return k
    lim_h, lim_w = int(h * max_trim), int(w * max_trim)
    t = side(lambda k: m[k, :], h, lim_h)
    b = side(lambda k: m[h - 1 - k, :], h, lim_h)
    l = side(lambda k: m[:, k], w, lim_w)
    r = side(lambda k: m[:, w - 1 - k], w, lim_w)
    crop = img[t:h - b, l:w - r]
    # keep the original proportions: trim the longer remaining side, centred
    ch, cw = crop.shape[:2]
    if cw / ch > w / h:
        nw = int(ch * w / h); x0 = (cw - nw) // 2; crop = crop[:, x0:x0 + nw]
    else:
        nh = int(cw * h / w); y0 = (ch - nh) // 2; crop = crop[y0:y0 + nh, :]
    out = cv2.resize(crop, (w, h), interpolation=cv2.INTER_CUBIC)
    # whatever paper is still showing in the outer margin is painted over from
    # its neighbours — only near the edge, never on the subject
    m2 = paper_mask(out)
    band = np.zeros_like(m2); e = int(min(h, w) * .16)
    band[:e, :] = 1; band[-e:, :] = 1; band[:, :e] = 1; band[:, -e:] = 1
    m2 = cv2.morphologyEx(m2 & band, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m2 = cv2.dilate(m2, np.ones((5, 5), np.uint8))
    if m2.any():
        small = cv2.resize(out, (w // 2, h // 2)); sm = cv2.resize(m2, (w // 2, h // 2), interpolation=cv2.INTER_NEAREST)
        filled = cv2.inpaint(small, sm, 9, cv2.INPAINT_TELEA)
        filled = cv2.resize(filled, (w, h), interpolation=cv2.INTER_CUBIC)
        a = cv2.GaussianBlur(m2.astype(np.float32), (0, 0), 3)[..., None]
        out = (out * (1 - a) + filled * a).astype(np.uint8)
    return out, dict(top=t, bottom=b, left=l, right=r, patched=int(m2.sum()))
