"""Custom per-region operations used by build.apply_pic (region key 'custom': '<fn name>').
Each fn(canvas, orig, region, kw) edits canvas (RGBA uint8) in place; orig = canvas before this spec."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys, numpy as np
import engine, gimcodec

OUT = P.unpacked()

def _orig_pic(src, k):
    return gimcodec.rgba(gimcodec.decode(open('%s/%s.bin' % (OUT, src), 'rb').read())[k])

def strip(canvas, orig, r, kw):
    """Stage-name banner (128_1 / 132_1): the game draws the 62x20 slices (x194..255, y0/20/40) side by side
    as ONE line, so render the full name as one 186px line and wrap it into the three slices."""
    x0, sw, pitch, n = r.get('strip_x', 194), r.get('strip_w', 62), r.get('strip_pitch', 20), r.get('strip_n', 3)
    tmp = np.zeros((pitch, sw * n, 4), np.uint8)
    dk = {k: (tuple(v) if isinstance(v, list) else v) for k, v in kw.items() if k in ('color', 'fname', 'size', 'outline', 'min_squeeze', 'tracking', 'shadow', 'ss')}
    fit = engine.draw_text(tmp, (1, 0, sw * n - 1, pitch), r['en'], align='left', **dk)
    for i in range(n):
        canvas[i * pitch:(i + 1) * pitch, x0:x0 + sw] = tmp[:, i * sw:(i + 1) * sw]
    if r.get('restore_cols'):   # undo an earlier over-wide erase that clipped the picture edge
        o = _orig_pic(r['src'], r['pic'])
        for c in r['restore_cols']: canvas[:, c] = o[:, c]
    return fit

def eaf(canvas, orig, r, kw):
    """133_1 pic6: replace the spaced four-character 'Earth Alliance' kanji label (x89-165,y49-62) with 'E. A. F.' built from the
    pixel glyphs of the neighbouring 'Z. A. F. T.' label (same font, same spacing). E = F + Z's bottom bar."""
    o = _orig_pic('133_1', 6)
    y0, y1 = 47, 64
    seg = o[y0:y1, 0:62].copy()                    # 'Z. A. F.' incl. F's tucked dot
    # build E in the Z slot (Z occupies cols 2..12)
    E = np.zeros((y1 - y0, 12, 4), np.uint8); E[..., :3] = 255
    F = o[y0:y1, 47:59].copy()                     # F stroke at col 48 -> E col 1
    F[60 - y0:, 9:] = 0; F[60 - y0:, 9:, :3] = 255  # drop F's tucked dot (cols 56..58, rows 60+)
    E[:, 0:12] = F
    zb = o[60:62, 2:12]                            # Z bottom bar rows 60-61, cols 2..11 (left edge col 2)
    for j in range(2):
        row = zb[j].copy()
        keep = E[60 - y0 + j, 1:11, 3] >= row[:, 3]
        row[keep] = E[60 - y0 + j, 1:11][keep]
        E[60 - y0 + j, 1:11] = row
    seg[:, 1:13] = E
    dx = 87
    canvas[y0:y1, dx:dx + seg.shape[1]] = seg
    return None

def label_rgba(canvas, orig, r, kw):
    """Erase a label sitting over a sprite edge by inpainting RGB *and* alpha from the box border (alpha is then
    snapped to 0/255 so the silhouette outline is rebuilt), then draw r['lines'] = [[box, text], ...]."""
    import cv2
    x0, y0, x1, y1 = r['inpaint_box']
    H, W = canvas.shape[:2]
    m = np.zeros((H, W), np.uint8); m[y0:y1, x0:x1] = 255
    rgb = np.ascontiguousarray(canvas[..., :3][..., ::-1])
    out = cv2.inpaint(rgb, m, 3, cv2.INPAINT_TELEA)[..., ::-1]
    al = cv2.inpaint(np.ascontiguousarray(canvas[..., 3]), m, 3, cv2.INPAINT_TELEA)
    sel = m > 0
    canvas[..., :3][sel] = out[sel]
    canvas[..., 3][sel] = np.where(al[sel] >= 128, 255, 0)
    dk = {k: (tuple(v) if isinstance(v, list) else v) for k, v in kw.items() if k in ('color', 'fname', 'size', 'outline', 'min_squeeze', 'tracking', 'shadow', 'align', 'ss')}
    return [engine.draw_text(canvas, tuple(b), t, **dk) for b, t in r['lines']]
