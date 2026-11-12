"""Exact-layout GIM codec for ULJM05238 (index8 swizzled images, 256-entry RGBA8888/5551 palettes).
decode(d) -> list of Picture(idx[h,w] uint8, pal[256,4] uint8 RGBA, meta)
encode(d, pics) -> bytes : writes indices/palette back into a copy of the ORIGINAL bytes,
   preserving header/chunk layout, pitch/height padding bytes and palette format."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import struct, numpy as np, sys
import gim

class Picture:
    pass

def _lvl0(d, h):
    return h['base'] + struct.unpack_from('<I', d, h['base'] + h['idxstart'])[0]

def _unswz(raw, pitch, rows):
    a = np.frombuffer(raw, np.uint8).reshape(rows // 8, pitch // 16, 8, 16)
    return a.transpose(0, 2, 1, 3).reshape(rows, pitch)

def _swz(arr, pitch, rows):
    return arr.reshape(rows // 8, 8, pitch // 16, 16).transpose(0, 2, 1, 3).reshape(-1).tobytes()

def _pal_dec(raw, fmt, n):
    if fmt == 3:
        return np.frombuffer(raw[:n*4], np.uint8).reshape(n, 4).copy()
    v = np.frombuffer(raw[:n*2], '<u2').astype(np.uint32)
    assert fmt == 1
    r = (v & 31); g = (v >> 5) & 31; b = (v >> 10) & 31; a = (v >> 15) & 1
    return np.stack([(r << 3) | (r >> 2), (g << 3) | (g >> 2), (b << 3) | (b >> 2), a * 255], 1).astype(np.uint8)

def _pal_enc(pal, fmt):
    if fmt == 3: return pal.astype(np.uint8).tobytes()
    p = pal.astype(np.uint32)
    v = (p[:, 0] >> 3) | ((p[:, 1] >> 3) << 5) | ((p[:, 2] >> 3) << 10) | ((p[:, 3] >= 128).astype(np.uint32) << 15)
    return v.astype('<u2').tobytes()

def decode(d):
    pics = []
    for bid, off, size, nxt, dat in gim.blocks(d, 0x10, len(d)):
        if bid == 3: pics.append(Picture())
        elif bid == 4:
            h = gim.parse_img_hdr(d, off + dat); p = pics[-1]
            assert h['fmt'] == 5 and h['order'] == 1
            p.w, p.h = h['w'], h['h']
            p.pitch = (p.w + 15) & ~15; p.rows = (p.h + 7) & ~7
            p.pix_off = _lvl0(d, h)
            full = _unswz(d[p.pix_off:p.pix_off + p.pitch * p.rows], p.pitch, p.rows)
            p.full = full.copy(); p.idx = full[:p.h, :p.w].copy()
        elif bid == 5:
            h = gim.parse_img_hdr(d, off + dat); p = pics[-1]
            p.pal_fmt = h['fmt']; p.pal_n = h['w']; p.pal_off = _lvl0(d, h)
            p.pal = _pal_dec(d[p.pal_off:], p.pal_fmt, p.pal_n)
            p.pal_orig = p.pal.copy()
    return pics

def rgba(p):
    return p.pal[p.idx]

def encode(d, pics):
    out = bytearray(d)
    for p in pics:
        full = p.full.copy(); full[:p.h, :p.w] = p.idx
        out[p.pix_off:p.pix_off + p.pitch * p.rows] = _swz(full, p.pitch, p.rows)
        if not np.array_equal(p.pal, p.pal_orig):
            b = _pal_enc(p.pal, p.pal_fmt); out[p.pal_off:p.pal_off + len(b)] = b
    return bytes(out)
