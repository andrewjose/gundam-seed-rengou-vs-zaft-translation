"""Minimal GIM (MIG.00.1PSP) reader -> PIL images (for locating pre-rendered text)."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import struct, numpy as np
from PIL import Image

def blocks(d, off, end):
    while off < end:
        bid, _, size, nxt, dat = struct.unpack_from('<HHIII', d, off)
        yield bid, off, size, nxt, dat
        if bid in (2, 3):
            yield from blocks(d, off + dat, off + size)
        off += size if size else end

def parse_img_hdr(d, base):
    h = struct.unpack_from('<HHHHHHHHHHHHIIII', d, base)
    keys = 'hsize ref fmt order w h bpp palign halign dims r1 r2 idxstart pixstart pixend planemask'.split()
    r = dict(zip(keys, h)); r['base'] = base
    return r

def unswizzle(buf, wbytes, h):
    out = np.zeros((h, wbytes), np.uint8)
    src = np.frombuffer(buf, np.uint8)
    bw = wbytes // 16; i = 0
    for by in range((h + 7) // 8):
        for bx in range(bw):
            blk = src[i:i+128]
            if len(blk) < 128: return out
            blk = blk.reshape(8, 16)
            rows = min(8, h - by*8)
            out[by*8:by*8+rows, bx*16:bx*16+16] = blk[:rows]
            i += 128
    return out

def conv(raw, fmt, n):
    a = np.frombuffer(raw, np.uint8)
    if fmt == 3: return a[:n*4].reshape(-1, 4)
    v = np.frombuffer(raw[:n*2], '<u2').astype(np.uint32)
    if fmt == 0:
        r = (v & 31) << 3; g = ((v >> 5) & 63) << 2; b = ((v >> 11) & 31) << 3; al = np.full_like(v, 255)
    elif fmt == 1:
        r = (v & 31) << 3; g = ((v >> 5) & 31) << 3; b = ((v >> 10) & 31) << 3; al = ((v >> 15) & 1) * 255
    else:
        r = (v & 15) * 17; g = ((v >> 4) & 15) * 17; b = ((v >> 8) & 15) * 17; al = ((v >> 12) & 15) * 17
    return np.stack([r, g, b, al], 1).astype(np.uint8)

BPP = {0: 16, 1: 16, 2: 16, 3: 32, 4: 4, 5: 8, 6: 16, 7: 32}

def images(d):
    if d[:11] != b'MIG.00.1PSP': return []
    imgs = []; pal = None; res = []
    for bid, off, size, nxt, dat in blocks(d, 0x10, len(d)):
        if bid == 3: imgs.append([None, None])
        if bid == 4: imgs[-1][0] = parse_img_hdr(d, off + dat)
        if bid == 5:
            ph = parse_img_hdr(d, off + dat)
            po = ph['base'] + struct.unpack_from('<I', d, ph['base'] + ph['idxstart'])[0]
            imgs[-1][1] = conv(d[po:], ph['fmt'], ph['w'])
    for ih, pal in imgs:
        if ih is None: continue
        fmt, w, h = ih['fmt'], ih['w'], ih['h']
        bpp = BPP.get(fmt, 8)
        lvl0 = ih['base'] + struct.unpack_from('<I', d, ih['base'] + ih['idxstart'])[0]
        pitch = (w * bpp // 8 + 15) & ~15
        ha = (h + 7) & ~7
        raw = d[lvl0:lvl0 + pitch * ha]
        if ih['order'] == 1: arr = unswizzle(raw, pitch, h)
        else:
            arr = np.frombuffer(raw.ljust(pitch*h, b'\0')[:pitch*h], np.uint8).reshape(h, pitch)
        if fmt == 4:
            lo = arr & 15; hi = arr >> 4
            idx = np.stack([lo, hi], 2).reshape(h, -1)[:, :w]
        elif fmt == 5: idx = arr[:, :w]
        else: idx = None
        if idx is not None:
            p = pal if pal is not None else np.stack([np.arange(256)]*3+[np.full(256,255)],1).astype(np.uint8)
            if len(p) < 256: p = np.vstack([p, np.zeros((256-len(p), 4), np.uint8)])
            rgba = p[idx]
        else:
            px = conv(arr.tobytes(), fmt, (pitch*8//BPP[fmt])*h).reshape(h, -1, 4)[:, :w]
            rgba = px
        res.append((ih, Image.fromarray(rgba, 'RGBA')))
    return res
