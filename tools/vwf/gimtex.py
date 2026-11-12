"""Read/write the level-0 index plane of an 8bpp (fmt 5) swizzled GIM image, keeping header/palette."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import struct, sys
import numpy as np
import gim

def image_info(d, n=0):
    """returns (img_hdr dict, level0 file offset, palette RGBA (256,4)) for the n-th image."""
    imgs = []
    for bid, off, size, nxt, dat in gim.blocks(d, 0x10, len(d)):
        if bid == 3: imgs.append([None, None])
        if bid == 4: imgs[-1][0] = gim.parse_img_hdr(d, off + dat)
        if bid == 5:
            ph = gim.parse_img_hdr(d, off + dat)
            po = ph['base'] + struct.unpack_from('<I', d, ph['base'] + ph['idxstart'])[0]
            assert ph['fmt'] == 3 and ph['w'] == 256
            imgs[-1][1] = np.frombuffer(d[po:po + 1024], np.uint8).reshape(256, 4).copy()
    ih, pal = imgs[n]
    assert ih['fmt'] == 5 and ih['order'] == 1, 'expect 8bpp swizzled'
    l0 = ih['base'] + struct.unpack_from('<I', d, ih['base'] + ih['idxstart'])[0]
    return ih, l0, pal

def swizzle(arr):
    h, wb = arr.shape
    assert wb % 16 == 0 and h % 8 == 0
    return arr.reshape(h // 8, 8, wb // 16, 16).transpose(0, 2, 1, 3).reshape(-1).tobytes()

def unswizzle(buf, wb, h):
    a = np.frombuffer(buf, np.uint8)[:wb * h]
    return a.reshape(h // 8, wb // 16, 8, 16).transpose(0, 2, 1, 3).reshape(h, wb).copy()

def read_indices(d, n=0):
    ih, l0, pal = image_info(d, n)
    w, h = ih['w'], ih['h']
    return unswizzle(d[l0:l0 + w * h], w, h), pal

def write_indices(d, idx, n=0):
    ih, l0, pal = image_info(d, n)
    w, h = ih['w'], ih['h']
    assert idx.shape == (h, w) and idx.dtype == np.uint8
    b = bytearray(d)
    b[l0:l0 + w * h] = swizzle(idx)
    return bytes(b)

if __name__ == '__main__':
    # self test: unswizzle/swizzle round trip on both atlases
    for n in ('1677_0', '10_1'):
        d = open(P.unpacked()+'/%s.bin' % n, 'rb').read()
        idx, pal = read_indices(d)
        assert write_indices(d, idx) == d
        # compare with xd/gim decode
        ih, im = gim.images(d)[0]
        assert (pal[idx] == np.array(im)).all()
    print('gimtex selftest ok')
