#!/usr/bin/env python3
"""VWF glyph atlases for battle dialogue (AFS 1677 sub 0) and tutorial captions (AFS 10 sub 1, image 0).
Glyphs are rendered at build time from DejaVu Sans Condensed Bold (tools/vwf/item3/glyphs1.py) and written into
the existing 8bpp swizzled GIM using the alpha ramp already present in its palette.

  1677 sub 0 : cells 0..95, 16 per row, 16x16 texels, ASCII 0x20..0x7F, glyph at texel (+1,+1)
  10 sub 1   : cells 0..95, 13 per row, 14x14 texels, ASCII 0x20..0x7F, glyph at x=+1

The matching EBOOT code (line converter, width tables, drawers) is part of patches/eboot_v041.json; the
generators for it are item3/build.py and item3/build_tut.py.
usage: atlas_vwf.py [--base10 FILE] [--base1677 FILE] [--out DIR]
  defaults: base for 10 = <work>/afs_new/afs_10.bin if the image builder produced it, else your original entry;
            base for 1677 = your original entry. Output: <work>/afs_new/afs_{10,1677}.bin"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P
import os, sys, argparse
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'item3'))
from glyphs1 import glyph
import gimtex, repack, pack as packmod, lz

SPACE = 4

def glyph_set(maxw):
    G = {}; WT = bytearray(96)
    for c in range(0x20, 0x80):
        a, w = glyph(chr(c), maxw=maxw) if c < 0x7f else (np.zeros((14, 0)), 0)
        G[c] = a; WT[c - 0x20] = w
    WT[0] = SPACE
    return G, WT

def _sub(entry, k):
    subs, _ = packmod.parse(entry)
    return lz.decompress(subs[k]['raw']) if subs[k]['flags'] & 1 else subs[k]['raw']

def _lut(idx, pal, region=None):
    reg = idx if region is None else region
    cand = sorted(set(int(i) for i in np.unique(reg)), key=lambda i: pal[i][3])
    alphas = np.array([pal[i][3] for i in cand], float)
    return np.array([cand[int(np.argmin(abs(alphas - a)))] for a in range(256)], np.uint8)

def build_1677(entry, G):
    g = _sub(entry, 0)
    idx, pal = gimtex.read_indices(g)
    lut = _lut(idx, pal); idx = idx.copy()
    for c in range(0x20, 0x80):
        k = c - 0x20; r, col = divmod(k, 16)
        cell = np.zeros((16, 16), np.float32); a = G[c]
        if a.shape[1]: cell[1:15, 1:1 + a.shape[1]] = a
        idx[r * 16:(r + 1) * 16, col * 16:(col + 1) * 16] = lut[np.clip(cell * 255 + 0.5, 0, 255).astype(np.uint8)]
    return repack.rebuild_pack(entry, {0: gimtex.write_indices(g, idx)})

def build_10(entry, G):
    g = _sub(entry, 1)
    idx, pal = gimtex.read_indices(g, 0)
    lut = _lut(idx, pal, idx[0:12 * 14, 0:13 * 14]); idx = idx.copy()
    for c in range(0x20, 0x80):
        k = c - 0x20; r, col = divmod(k, 13)
        cell = np.zeros((14, 14), np.float32); a = G[c]
        if a.shape[1]: cell[:, 1:1 + a.shape[1]] = a
        idx[r * 14:(r + 1) * 14, col * 14:(col + 1) * 14] = lut[np.clip(cell * 255 + 0.5, 0, 255).astype(np.uint8)]
    return repack.rebuild_pack(entry, {1: gimtex.write_indices(g, idx, 0)})

def original_entry(i):
    f, ents = repack.read_afs(); off, size = ents[i]; f.seek(off); return f.read(size)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--base10'); ap.add_argument('--base1677'); ap.add_argument('--out', default=P.afs_new())
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    b10 = open(a.base10, 'rb').read() if a.base10 else (open(P.afs_new(10), 'rb').read() if os.path.exists(P.afs_new(10)) else original_entry(10))
    b1677 = open(a.base1677, 'rb').read() if a.base1677 else original_entry(1677)
    e1677 = build_1677(b1677, glyph_set(14)[0]); e10 = build_10(b10, glyph_set(13)[0])
    open(os.path.join(a.out, 'afs_1677.bin'), 'wb').write(e1677); open(os.path.join(a.out, 'afs_10.bin'), 'wb').write(e10)
    print('atlas 1677: %d -> %d bytes; atlas 10: %d -> %d bytes' % (len(b1677), len(e1677), len(b10), len(e10)))
