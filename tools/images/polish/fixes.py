#!/usr/bin/env python3
"""v0.4.4 image polish fixes, built on the v0.4.2 sub-files (out/<afs>_<sub>.bin).
Writes subs/<afs>_<sub>.bin (decompressed GIM), previews/<afs>_<sub>_<pic>.png (before|after, 2x/3x),
and fixes_log.json. Every result is round-trip checked (decode(encode) == intended indices/palette).
Usage: fixes.py [name ...]   (default: all)"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import ppaths  # repo tool paths + work folders (see ppaths.py)
import sys, os, json, numpy as np, cv2
from PIL import Image
import gimcodec, engine

W = ppaths.W
OUT, ORIG = ppaths.OUT, ppaths.ORIG
SPECS = ppaths.SPECS
os.makedirs(W + '/subs', exist_ok=True); os.makedirs(W + '/previews', exist_ok=True)
LOG = {}

def load(f, src=OUT):
    d = open('%s/%s.bin' % (src, f), 'rb').read()
    return d, gimcodec.decode(d)

def spec(f):
    return json.load(open('%s/%s.json' % (SPECS, f)))

def place(canvas, x, base, text, fname, size, color=(255, 255, 255), shadow=None, shadow_off=(1, 1), ss=4,
          squeeze=1.0, outline=None, outline_w=1):
    """draw text with its left ink edge at x and baseline at `base` (pixel row of baseline)."""
    a, top, bot, b0, capt = engine.render_line(text, fname, size, squeeze, 0, ss)
    oy = base - b0
    layers = []
    if shadow is not None: layers.append((a, shadow, shadow_off))
    if outline is not None:
        k = np.ones((2 * outline_w + 1, 2 * outline_w + 1), np.uint8)
        layers.append((cv2.dilate(np.pad(a, outline_w + 1), k), outline, (-(outline_w + 1), -(outline_w + 1))))
    layers.append((a, color, (0, 0)))
    H, Wd = canvas.shape[:2]
    for alpha, col, (dx, dy) in layers:
        hh, ww = alpha.shape
        for yy in range(hh):
            Y = oy + yy + dy
            if Y < 0 or Y >= H: continue
            xs = x + dx; ca, cb = max(0, xs), min(Wd, xs + ww)
            if ca >= cb: continue
            al = alpha[yy, ca - xs:cb - xs][:, None] * ((col[3] / 255) if len(col) > 3 else 1)
            src = np.array(col[:3], np.float32)[None]
            dst = canvas[Y, ca:cb].astype(np.float32); da = dst[:, 3:4] / 255
            oa = al + da * (1 - al)
            rgb = np.where(oa > 0, (src * al + dst[:, :3] * da * (1 - al)) / np.maximum(oa, 1e-6), 0)
            canvas[Y, ca:cb, :3] = np.clip(rgb + .5, 0, 255); canvas[Y, ca:cb, 3] = np.clip(oa[:, 0] * 255 + .5, 0, 255)
    return a.shape[1]

def width(text, fname, size, ss=4):
    return engine.render_line(text, fname, size, 1.0, 0, ss)[0].shape[1]

def fit_sq(text, fname, size, maxw, ss=4, floor=0.8):
    w = width(text, fname, size, ss)
    sq = min(1.0, maxw / w)
    assert sq >= floor - 1e-6, (text, w, maxw, sq)
    return sq, int(round(w * sq))

def baseline_of(fname, size, ss=4):
    a, top, bot, b0, capt = engine.render_line('H', fname, size, 1.0, 0, ss)
    return b0 - capt          # cap height in px

def commit(name, f, data, pics, k, canvas, before, note, src_pic=None):
    pic = pics[k]
    changed = (canvas != before).any(-1) if src_pic is None else np.ones(canvas.shape[:2], bool)
    err = engine.quantize(pic, canvas, changed)
    LOG.setdefault(name, []).append({'file': f, 'pic': k, 'note': note, 'quant_rms': round(err, 2),
                                     'changed_px': int(changed.sum())})
    return err

def finish(f, data, pics, tag):
    new = gimcodec.encode(data, pics)
    chk = gimcodec.decode(new)
    for p, q in zip(pics, chk):
        assert np.array_equal(p.idx, q.idx), f
        if p.pal_fmt == 3: assert np.array_equal(p.pal[:p.pal_n], q.pal[:q.pal_n]), f
        assert np.array_equal(gimcodec.encode(new, chk), new), f
    assert len(new) == len(data)
    open('%s/subs/%s.bin' % (W, f), 'wb').write(new)
    return new

def preview(f, k, tag):
    a = gimcodec.decode(open('%s/%s.bin' % (OUT, f), 'rb').read())[k]
    b = gimcodec.decode(open('%s/subs/%s.bin' % (W, f), 'rb').read())[k]
    def comp(p):
        im = Image.fromarray(p.pal[p.idx], 'RGBA'); bg = Image.new('RGBA', im.size, (24, 24, 96, 255)); bg.alpha_composite(im)
        return bg.convert('RGB')
    A, B = comp(a), comp(b)
    sc = 3 if max(A.size) <= 128 else 2
    A = A.resize((A.width * sc, A.height * sc), Image.NEAREST); B = B.resize(A.size, Image.NEAREST)
    S = Image.new('RGB', (A.width * 2 + 8, A.height), (255, 0, 255)); S.paste(A, (0, 0)); S.paste(B, (A.width + 8, 0))
    S.save('%s/previews/%s_%d_%s.png' % (W, f, k, tag))

# ---------------------------------------------------------------- fixes
def fix_2_0():
    """Title/help-bar legend pieces (2_0 pic0). Rects from the EBOOT sprite table at file 0x1de925 (8-byte
    records x,y,w,h,0,0,0,1). Were hinted DejaVu Condensed, squeezed 0.6-0.7, mixed baselines, 'Move' tinted.
    Now: one face/size (Roboto Condensed Bold 12, 4x supersampled), white + soft dark shadow like the JP original,
    left aligned in each rect, common baseline per row."""
    f = '2_0'; data, pics = load(f); k = 0; p = pics[k]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    R = [  # (x, y, w, h, text) from EBOOT 0x1de925..0x1de9c5
        (0, 18, 32, 18, 'Select'), (48, 18, 32, 18, 'OK'), (96, 18, 30, 18, 'Back'), (144, 18, 31, 18, 'Next'),
        (192, 18, 31, 18, 'Enter'), (223, 18, 32, 18, 'Launch'),
        (0, 36, 31, 18, 'Move'), (48, 36, 29, 18, 'Yes'), (96, 36, 42, 18, 'No'), (144, 36, 32, 18, 'Change'),
        (0, 54, 102, 18, 'Reset to default'), (120, 54, 60, 18, 'Done'),
        (0, 72, 120, 18, 'Back to menu'), (120, 72, 52, 18, 'Menu'), (173, 72, 46, 18, 'Switch'),
        (0, 90, 60, 18, 'Ready'), (76, 90, 79, 18, 'Start battle'), (154, 90, 61, 18, 'CPU select'),
        (0, 108, 69, 18, 'Page'), (0, 126, 69, 18, 'No change')]
    FN, SZ = 'rc', 12
    cap = baseline_of(FN, SZ)
    sq_all = {}
    for x, y, w, h, t in R:
        cv[y:y + h, x:x + w] = 0
    for x, y, w, h, t in R:
        sq, iw = fit_sq(t, FN, SZ, w - 2)
        base = y + (h + cap) // 2           # cap block vertically centred in the 18px cell
        place(cv, x + 1, base, t, FN, SZ, shadow=(0, 0, 0, 170), squeeze=sq)
        sq_all[t] = round(sq, 2)
    commit('2_0', f, data, pics, k, cv, before, 'help-bar legends: rc12 ss4 + shadow, squeeze ' + json.dumps(sq_all))
    finish(f, data, pics, 'fix'); preview(f, k, 'helpbar')

def fix_133_8():
    """Level-select help row (133_1 pic8, y80-100): 'Enter' had an opaque dark box behind it (erase used a fill),
    and the four words were in two different faces. Four 32px pieces (idou/nyuuryoku/modoru/kettei)."""
    f = '133_1'; data, pics = load(f); k = 8; p = pics[k]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    cv[79:102, 0:128] = 0
    FN, SZ = 'rc', 13
    cap = baseline_of(FN, SZ)
    for i, t in enumerate(('Move', 'Enter', 'Back', 'OK')):
        x = 32 * i
        sq, iw = fit_sq(t, FN, SZ, 30)
        place(cv, x + 1, 80 + (20 + cap) // 2, t, FN, SZ, shadow=(0, 0, 0, 170), squeeze=sq)
    commit('133_8', f, data, pics, k, cv, before, 'help row Move/Enter/Back/OK: removed dark box, one face')
    finish(f, data, pics, 'fix'); preview(f, k, 'helprow')

def fix_1608():
    """'New enemy unit / inbound !' (1608_1 pic0): the full-width JP '(full-width !)' was kept with a gap. Redraw line 2."""
    f = '1608_1'; data, pics = load(f); k = 0; p = pics[k]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    reg = cv[104:123, 0:72]
    m = (reg[..., 0].astype(int) - reg[..., 1] < 60)     # everything except the red underline
    reg[m] = 0
    place(cv, 1, 116, 'inbound!', 'sans', 12)
    commit('1608', f, data, pics, k, cv, before, 'line 2 redrawn as "inbound!" (sans bold 12, same as line 1)')
    finish(f, data, pics, 'fix'); preview(f, k, 'inbound')

def fix_maps():
    """Mission map labels 562-578 (pic0): sizes were cond 11/12/13 (Onogoro Island, South Pacific, Red Sea,
    Indian Ocean smaller). All 17 now Roboto Condensed Bold 13 (cap 9 px, same as cond 13), same baseline,
    squeeze only where the label rect forces it (Red Sea 0.88, Indian Ocean 0.90). Boxes unchanged."""
    out = {}
    for i in range(562, 579):
        f = '%d_1' % i; data, pics = load(f); k = 0; p = pics[k]
        cv = gimcodec.rgba(p).copy(); before = cv.copy()
        r = spec(f)['pics']['0']['regions'][0]
        x0, y0, x1, y1 = r['erase_box']; cv[y0:y1, x0:x1] = 0
        bx = r['box']
        sq, iw = fit_sq(r['en'], 'rc', 13, bx[2] - bx[0])
        place(cv, bx[0], 14, r['en'], 'rc', 13, squeeze=sq)
        out[r['en'] + '@%d' % i] = round(sq, 2)
        commit('maps', f, data, pics, k, cv, before, 'map label rc13: %s sq %.2f' % (r['en'], sq))
        finish(f, data, pics, 'fix'); preview(f, k, 'maplabel')
    return out

def fix_banners():
    """Location banners 105-121 (pic0): the v0.3 inpaint mask touched the underline row, leaving white smudges
    between the name and the underline. Rebuilt from the ORIGINAL texture: inpaint only the JP text (underline
    rows replaced by the row below during inpainting and restored afterwards), then the same English/style as v0.4.2
    (DejaVu Sans Bold 13, white, shadow 30,30,30,200, right-aligned to x=250)."""
    for i in range(105, 122):
        f = '%d_1' % i
        data, pics = load(f)               # v0.4.2 bytes (layout identical to the original)
        od, opics = load(f, ORIG)
        k = 0; p = pics[k]; o = opics[k]
        cv = gimcodec.rgba(o).copy()
        r = spec(f)['pics']['0']['regions'][0]
        ex0, ey0, ex1, ey1 = r['erase_box']
        rgb = cv[..., :3].copy()
        # locate underline rows (bright, long) just under the text
        ul = [y for y in range(234, 242) if (rgb[y, 60:250].min(1) > 200).sum() > 60]
        tmp = rgb.copy()
        for y in ul: tmp[y] = tmp[max(ul) + 1]
        m = np.zeros(rgb.shape[:2], np.uint8)
        reg = tmp[ey0:min(ey1, min(ul) if ul else ey1), ex0:ex1].astype(int)
        mm = (reg.min(2) >= 150).astype(np.uint8) * 255
        mm = cv2.dilate(mm, np.ones((3, 3), np.uint8))
        m[ey0:ey0 + mm.shape[0], ex0:ex1] = mm
        for y in ul: m[y] = 0
        inp = cv2.inpaint(np.ascontiguousarray(tmp[..., ::-1]), m, 3, cv2.INPAINT_TELEA)[..., ::-1]
        new = np.where(m[..., None] > 0, inp, rgb)
        cv[..., :3] = new
        dflt = spec(f)['pics']['0']['defaults']
        kw = dict(fname=dflt.get('fname', 'sans'), size=dflt.get('size', 13), color=tuple(dflt.get('color', (255, 255, 255))),
                  shadow=tuple(dflt['shadow']) if dflt.get('shadow') else None, align='right')
        engine.draw_text(cv, r['box'], r['en'], **kw)
        # quantize the whole picture against the ORIGINAL palette (free slots may be reused)
        o.pal = o.pal.copy()
        changed = (cv != gimcodec.rgba(o)).any(-1)
        err = engine.quantize(o, cv, changed)
        p.idx = o.idx; p.pal = o.pal
        LOG.setdefault('banners', []).append({'file': f, 'pic': 0, 'en': r['en'], 'underline_rows': ul,
                                              'quant_rms': round(err, 2)})
        finish(f, data, pics, 'fix'); preview(f, k, 'banner')

def fix_2_20():
    """Options grid (2_20 pic0): grid words were DejaVu Sans Condensed 14 except Awaken/Delete/Load/Save/
    Automatic in Roboto Condensed -> two faces in one menu. All grid words now Roboto Condensed Bold 15
    (cap height of cond 14), 4x supersampled, inside the same boxes as v0.4.2 (piece joins unchanged)."""
    f = '2_20'; data, pics = load(f); k = 0; p = pics[k]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    regs = spec(f)['pics']['0']['regions']
    grid = [r for r in regs if 104 <= r['box'][1] <= 200]
    FN, SZ = 'rc', 15
    cap = baseline_of(FN, SZ)
    rows = {}
    for r in grid:
        x0, y0, x1, y1 = r['box']; cv[y0:y1, x0:x1] = 0
    sqs = {}
    for r in grid:
        if not r.get('en'): continue
        x0, y0, x1, y1 = r['box']
        sq, iw = fit_sq(r['en'], FN, SZ, x1 - x0)
        # common baseline per row: rows start at 107/129/151/173/195
        rowy = min((107, 129, 151, 173, 195), key=lambda v: abs(v - y0))
        place(cv, x0 + (1 if iw < x1 - x0 else 0), rowy + (19 + cap) // 2, r['en'], FN, SZ, squeeze=sq)
        sqs[r['en'] + '@%d,%d' % (x0, y0)] = round(sq, 2)
    commit('2_20', f, data, pics, k, cv, before, 'options grid rc15 ss4: ' + json.dumps(sqs))
    finish(f, data, pics, 'fix'); preview(f, k, 'options')


def fix_copyright():
    """OPTIONAL (decision): Japanese copyright line redrawn in English, '©SOTSU AGENCY · SUNRISE · MBS'
    (the official English form of the Japanese Sotsu Agency / Sunrise / MBS line). Inter SemiBold 14, white.
    2_16 pic0 = title screen (480x272, line at x202-461 y250-261, over artwork: inpainted);
    9_9 pic5 = title-logo atlas copy split over two 128px slices (row 1 y2-12, row 2 y18-29, read as one line).
    Written to subs_opt/ so the integrator can choose."""
    T = '\u00a9SOTSU AGENCY \u00b7 SUNRISE \u00b7 MBS'
    os.makedirs(W + '/subs_opt', exist_ok=True)
    # title screen
    f = '2_16'; data, pics = load(f); p = pics[0]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    rgb = cv[..., :3].copy(); m = np.zeros(rgb.shape[:2], np.uint8)
    reg = rgb[246:265, 196:468].astype(int)
    mm = (reg.min(2) >= 120).astype(np.uint8) * 255
    m[246:265, 196:468] = cv2.dilate(mm, np.ones((3, 3), np.uint8))
    inp = cv2.inpaint(np.ascontiguousarray(rgb[..., ::-1]), m, 4, cv2.INPAINT_TELEA)[..., ::-1]
    cv[..., :3] = np.where(m[..., None] > 0, inp, rgb)
    w = width(T, 'semi', 14)
    # round 2: PPSSPP showed the line clipped at the right screen edge (title texture is drawn ~22 px right of 1:1);
    # right edge moved from x=461 to x=444 (17 px left; JP line ended at 461) -> ends >= 6 px inside the screen.
    place(cv, 444 - w + 1, 261, T, 'semi', 14, shadow=(0, 0, 0, 140))
    commit('copyright', f, data, pics, 0, cv, before, 'title-screen copyright in English (optional)')
    new = gimcodec.encode(data, pics); assert np.array_equal(gimcodec.decode(new)[0].idx, pics[0].idx)
    open(W + '/subs_opt/%s.bin' % f, 'wb').write(new)
    # logo atlas copy: draw on a 256-wide strip, split at x=128 into the two rows
    f = '9_9'; data, pics = load(f); p = pics[5]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    cv[0:32, :] = 0
    strip = np.zeros((16, 256, 4), np.uint8)
    # round 2: atlas copy kept inside the JP line's extent (JP ended at strip x=224; was 239 in round 1):
    # Inter SemiBold 13 squeezed to 207 px -> x 2..208, the same 17/260 right-margin share as the title line.
    sq13 = 207 / width(T, 'semi', 13)
    place(strip, 2, 12, T, 'semi', 13, squeeze=sq13)
    cv[0:16, 0:128] = strip[:, :128]; cv[16:32, 0:128] = strip[:, 128:]
    commit('copyright', f, data, pics, 5, cv, before, 'logo-atlas copyright (2 slices) in English (optional)')
    new = gimcodec.encode(data, pics); assert np.array_equal(gimcodec.decode(new)[5].idx, pics[5].idx)
    open(W + '/subs_opt/%s.bin' % f, 'wb').write(new)
    for f, k in (('2_16', 0), ('9_9', 5)):
        a = gimcodec.decode(open('%s/%s.bin' % (OUT, f), 'rb').read())[k]
        b = gimcodec.decode(open('%s/subs_opt/%s.bin' % (W, f), 'rb').read())[k]
        A = Image.fromarray(a.pal[a.idx], 'RGBA'); B = Image.fromarray(b.pal[b.idx], 'RGBA')
        if f == '2_16': A = A.crop((180, 236, 480, 268)); B = B.crop((180, 236, 480, 268))
        else: A = A.crop((0, 0, 128, 32)); B = B.crop((0, 0, 128, 32))
        S = Image.new('RGBA', (A.width * 3, A.height * 6 + 6), (24, 24, 96, 255))
        S.alpha_composite(A.resize((A.width * 3, A.height * 3), Image.NEAREST), (0, 0))
        S.alpha_composite(B.resize((A.width * 3, A.height * 3), Image.NEAREST), (0, A.height * 3 + 6))
        S.convert('RGB').save('%s/previews/OPTIONAL_%s_%d_copyright.png' % (W, f, k))

def fix_credits():
    """Credits (1684_raw pic3): the quote marks around the original 'INVOKE' art were placed 9 px away from the
    word (reads as '" INVOKE "'). Shift the existing quote pixels to a 3 px gap."""
    f = '1684_raw'; data, pics = load(f); k = 3; p = pics[k]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    L = cv[16:24, 72:80].copy(); R = cv[16:24, 174:182].copy()
    cv[16:24, 72:80] = 0; cv[16:24, 174:182] = 0
    cv[16:24, 78:86] = np.where(L[..., 3:4] > 0, L, cv[16:24, 78:86])
    cv[16:24, 168:176] = np.where(R[..., 3:4] > 0, R, cv[16:24, 168:176])
    commit('credits', f, data, pics, k, cv, before, 'INVOKE quote marks moved to a 3 px gap')
    finish(f, data, pics, 'fix'); preview(f, k, 'invoke')

FIXES = {'credits': fix_credits, 'copyright': fix_copyright, '2_0': fix_2_0, '133_8': fix_133_8, '1608': fix_1608, 'maps': fix_maps, 'banners': fix_banners, '2_20': fix_2_20}
if __name__ == '__main__':
    names = sys.argv[1:] or list(FIXES)
    for n in names:
        r = FIXES[n](); print(n, 'ok', r if r else '')
    old = json.load(open(W + '/fixes_log.json')) if os.path.exists(W + '/fixes_log.json') else {}
    old.update(LOG); json.dump(old, open(W + '/fixes_log.json', 'w'), indent=1, ensure_ascii=False)
