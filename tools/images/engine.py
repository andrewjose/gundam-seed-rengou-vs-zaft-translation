"""Text-image translation engine: erase the original text regions, draw English, quantize to GIM palette."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys, json, os, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
import gimcodec

from gseed import fonts as _fonts
# face key -> gseed.fonts key (files are resolved at first use; see scripts/fetch_fonts.sh)
FONTS = {
    'sans': 'dejavu-sans-bold', 'cond': 'dejavu-cond-bold', 'sansr': 'dejavu-sans',
    'inter': 'inter-bold', 'semi': 'inter-semibold',
    'lib': 'liberation-sans-bold', 'libr': 'liberation-sans',
    'pop': 'poppins-bold', 'popm': 'poppins-medium',
    # Roboto Condensed (OFL, shipped in fonts/): natural narrow UI face for tight piece rects
    'rc': 'rc700', 'rc6': 'rc600',
}
_fc = {}
def font(name, size):
    k = (name, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(_fonts.path(FONTS[name]), size)
    return _fc[k]

SS = {}   # fname -> supersample factor (set per region via draw_text(ss=..)); 1 = hinted pixel rendering

def render_line(text, fname, size, squeeze=1.0, tracking=0, ss=1):
    """returns float alpha array (h,w) and baseline y; h covers 'Hg' extents.
    ss>1: render unhinted at ss x size and box-downsample -> natural (non letter-spaced) glyph spacing."""
    if ss and ss > 1:
        a, top, bot, base, capt = render_line(text, fname, size * ss, 1.0, tracking * ss, 1)
        H, W = a.shape; Hp, Wp = -(-H // ss) * ss, -(-W // ss) * ss
        a = np.pad(a, ((0, Hp - H), (0, Wp - W)))
        a = a.reshape(Hp // ss, ss, Wp // ss, ss).mean((1, 3))
        cols = np.nonzero(a.max(0) > 0.02)[0]
        if len(cols): a = a[:, cols[0]:cols[-1] + 1]
        a = np.clip(a, 0, 1).astype(np.float32)
        if squeeze != 1.0:
            nw = max(1, int(round(a.shape[1] * squeeze)))
            a = np.array(Image.fromarray((a * 255).astype(np.uint8)).resize((nw, a.shape[0]), Image.LANCZOS)).astype(np.float32) / 255
        r = lambda v: int(round(v / ss))
        return a, r(top), r(bot), r(base), r(capt)
    f = font(fname, size)
    asc, desc = f.getmetrics()
    # width
    if tracking:
        w = sum(f.getlength(c) for c in text) + tracking * (len(text) - 1)
    else:
        w = f.getlength(text)
    W = int(np.ceil(w)) + 4; H = asc + desc + 2
    im = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(im)
    if tracking:
        x = 1
        for c in text:
            dr.text((x, asc + 1), c, font=f, fill=255, anchor='ls'); x += f.getlength(c) + tracking
    else:
        dr.text((1, asc + 1), text, font=f, fill=255, anchor='ls')
    a = np.array(im).astype(np.float32) / 255
    cols = np.nonzero(a.max(0) > 0)[0]
    if len(cols): a = a[:, cols[0]:cols[-1] + 1]
    if squeeze != 1.0:
        nw = max(1, int(round(a.shape[1] * squeeze)))
        a = np.array(Image.fromarray((a * 255).astype(np.uint8)).resize((nw, a.shape[0]), Image.LANCZOS)).astype(np.float32) / 255
    # vertical ink extents of reference 'Hg' for consistent placement
    hb = f.getbbox('Hg', anchor='ls')  # (x0, top(neg), x1, bottom)
    top = asc + 1 + hb[1]; bot = asc + 1 + hb[3]
    capb = f.getbbox('H', anchor='ls')
    return a, top, bot, asc + 1, asc + 1 + capb[1]

def fit(text, box_w, box_h, fname='sans', minsize=7, maxsize=None, min_squeeze=0.62, mode='hg', tracking=0, size=None, ss=1):
    """choose size/squeeze so text fits box. mode 'hg': ascender..descender fits box_h; 'cap': cap height fits box_h."""
    cand = []
    hi = size or maxsize or 40
    for s in range(hi, minsize - 1, -1):
        a, top, bot, base, capt = render_line(text, fname, s, tracking=tracking, ss=ss)
        hh = (bot - top) if mode == 'hg' else (base - capt)
        if size is None and hh > box_h: continue
        if a.shape[1] <= box_w: return s, 1.0
        sq = box_w / a.shape[1]
        if sq >= min_squeeze: return s, sq
        if size: break
        cand.append((s, sq))
    s = size or minsize
    a = render_line(text, fname, s, tracking=tracking, ss=ss)[0]
    return s, min(1.0, box_w / a.shape[1])

def draw_text(canvas, box, text, color=(255, 255, 255), fname='sans', align='left', valign='center', outline=None,
              outline_w=1, shadow=None, shadow_off=(1, 1), mode='hg', size=None, minsize=7, min_squeeze=0.62,
              tracking=0, yoff=0, xoff=0, maxsize=None, rotate=0, ss=1):
    x0, y0, x1, y1 = box; bw, bh = x1 - x0, y1 - y0
    if rotate:
        tmp = np.zeros((bw, bh, 4), np.uint8)
        r = draw_text(tmp, (0, 0, bh, bw), text, color, fname, align, valign, outline, outline_w, shadow, shadow_off,
                      mode, size, minsize, min_squeeze, tracking, yoff, xoff, maxsize, 0, ss)
        t = np.rot90(tmp, rotate // 90).astype(np.float32)
        dst = canvas[y0:y1, x0:x1].astype(np.float32)
        sa = t[..., 3:4] / 255; da = dst[..., 3:4] / 255; oa = sa + da * (1 - sa)
        rgb = np.where(oa > 0, (t[..., :3] * sa + dst[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6), 0)
        canvas[y0:y1, x0:x1, :3] = np.clip(rgb + .5, 0, 255).astype(np.uint8)
        canvas[y0:y1, x0:x1, 3] = np.clip(oa[..., 0] * 255 + .5, 0, 255).astype(np.uint8)
        return r
    pad = (outline_w if outline else 0)
    s, sq = fit(text, bw - 2 * pad, bh - 2 * pad if mode == 'hg' else bh - 2 * pad, fname, minsize, maxsize, min_squeeze, mode, tracking, size, ss)
    a, top, bot, base, capt = render_line(text, fname, s, sq, tracking, ss)
    h, w = a.shape
    if align == 'left': ox = x0 + pad
    elif align == 'right': ox = x1 - pad - w
    else: ox = x0 + (bw - w) // 2
    if mode == 'hg': oy = y0 + (bh - (bot - top)) // 2 - top
    else: oy = y0 + (bh - (base - capt)) // 2 - capt
    if valign == 'top': oy = y0 + pad - (top if mode == 'hg' else capt)
    ox += xoff; oy += yoff
    H, W = canvas.shape[:2]
    layers = []
    if shadow is not None:
        layers.append((a, shadow, shadow_off))
    if outline is not None:
        k = np.ones((2 * outline_w + 1, 2 * outline_w + 1), np.uint8)
        ap = np.pad(a, outline_w + 1)
        dil = cv2.dilate(ap, k)
        layers.append((dil, outline, (-(outline_w + 1), -(outline_w + 1))))
    layers.append((a, color, (0, 0)))
    for alpha, col, (dx, dy) in layers:
        hh, ww = alpha.shape
        for yy in range(hh):
            Y = oy + yy + dy
            if Y < 0 or Y >= H: continue
            xs = ox + dx; xe = xs + ww
            ca, cb = max(0, xs), min(W, xe)
            if ca >= cb: continue
            al = alpha[yy, ca - xs:cb - xs][:, None]
            src = np.array(col[:3], np.float32)[None, :]
            sa = al * (col[3] / 255 if len(col) > 3 else 1)
            dst = canvas[Y, ca:cb].astype(np.float32)
            da = dst[:, 3:4] / 255
            oa = sa + da * (1 - sa)
            orgb = np.where(oa > 0, (src * sa + dst[:, :3] * da * (1 - sa)) / np.maximum(oa, 1e-6), 0)
            canvas[Y, ca:cb, :3] = np.clip(orgb + 0.5, 0, 255).astype(np.uint8)
            canvas[Y, ca:cb, 3] = np.clip(oa[:, 0] * 255 + 0.5, 0, 255).astype(np.uint8)
    return s, sq

def erase(canvas, box, mode='transparent', pad=1, fill=None, thr=None, rad=3, orig=None):
    x0, y0, x1, y1 = box
    H, W = canvas.shape[:2]
    a0, b0, a1, b1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
    if mode == 'transparent':
        canvas[b0:b1, a0:a1] = 0
    elif mode == 'fill':
        canvas[b0:b1, a0:a1] = fill
    elif mode in ('inpaint', 'inpaint_bright', 'inpaint_box', 'inpaint_label', 'inpaint_dark', 'inpaint_bw'):
        rgb = canvas[..., :3].copy()
        m = np.zeros((H, W), np.uint8)
        if mode == 'inpaint_box':
            m[b0:b1, a0:a1] = 255
        elif mode == 'inpaint_dark':
            reg = rgb[b0:b1, a0:a1].astype(np.int32)
            al = canvas[b0:b1, a0:a1, 3]
            t = thr if thr is not None else 70
            mm = ((reg.max(2) <= t) & (al > 100)).astype(np.uint8) * 255
            mm = cv2.dilate(mm, np.ones((3, 3), np.uint8), iterations=1)
            m[b0:b1, a0:a1] = mm
        elif mode == 'inpaint_bw':
            reg = rgb[b0:b1, a0:a1].astype(np.int32)
            mm = ((reg.min(2) > 200) | (reg.max(2) < 70)).astype(np.uint8) * 255
            mm = cv2.dilate(mm, np.ones((3, 3), np.uint8), iterations=1)
            m[b0:b1, a0:a1] = mm
        elif mode == 'inpaint_label':
            reg = rgb[b0:b1, a0:a1].astype(np.int32)
            sat = reg.max(2) - reg.min(2)
            mm = ((sat > 80) | (reg.min(2) > 190)).astype(np.uint8) * 255
            mm = cv2.dilate(mm, np.ones((3, 3), np.uint8), iterations=1)
            m[b0:b1, a0:a1] = mm
        else:
            reg = rgb[b0:b1, a0:a1].astype(np.int32)
            lum = reg.max(2)
            t = thr if thr is not None else 150
            mm = (lum >= t).astype(np.uint8) * 255
            mm = cv2.dilate(mm, np.ones((3, 3), np.uint8), iterations=1)
            m[b0:b1, a0:a1] = mm
        out = cv2.inpaint(np.ascontiguousarray(rgb[..., ::-1]), m, rad, cv2.INPAINT_TELEA)[..., ::-1]
        canvas[..., :3] = np.where(m[..., None] > 0, out, rgb)
    elif mode == 'rows':
        # copy column-wise from row just above the box (good for flat/gradient horizontal bands)
        src = canvas[b0 - 1] if b0 > 0 else canvas[b1]
        for y in range(b0, b1): canvas[y, a0:a1] = src[a0:a1]
    elif mode == 'cols':
        src = canvas[:, a0 - 1] if a0 > 0 else canvas[:, a1]
        for x in range(a0, a1): canvas[b0:b1, x] = src[b0:b1]
    elif mode == 'none':
        pass

def quantize(pic, canvas, changed, extra_slots=True):
    """map changed pixels to palette; may allocate unused palette entries for new colours."""
    pal = pic.pal.astype(np.float32)
    binary_alpha = pic.pal_fmt == 1
    px = canvas[changed].astype(np.float32)
    if binary_alpha:
        px[:, 3] = np.where(px[:, 3] >= 128, 255, 0)
    def prem(c):
        a = c[..., 3:4] / 255
        return np.concatenate([c[..., :3] * a, c[..., 3:4]], -1)
    used = np.zeros(256, bool); used[np.unique(pic.idx[~changed])] = True
    P = prem(pal); X = prem(px)
    def assign():
        d = ((X[:, None, :] - P[None, :, :]) ** 2).sum(-1)
        j = d.argmin(1); return j, d[np.arange(len(j)), j]
    j, err = assign()
    if extra_slots:
        free = [i for i in range(pic.pal_n) if not used[i] and i not in set(j.tolist())]
        # greedily add worst colours
        it = 0
        while free and err.max() > 300 and it < 64:
            k = err.argmax(); slot = free.pop(0)
            col = px[k].copy()
            if binary_alpha: col = np.where(np.arange(4) < 3, np.floor(col / 8) * 8 + 4 if False else col, col)
            pal[slot] = col; P[slot] = prem(col[None])[0]
            j, err = assign(); it += 1
            free = [i for i in free if i not in set(j.tolist())]
    newpal = np.clip(pal + 0.5, 0, 255).astype(np.uint8)
    # unused-but-allocated slots keep their new colours; slots never used retain old values unless reassigned
    pic.pal = newpal
    pic.idx = pic.idx.copy(); pic.idx[changed] = j.astype(np.uint8)
    return float(np.sqrt(err.mean())) if len(err) else 0.0
