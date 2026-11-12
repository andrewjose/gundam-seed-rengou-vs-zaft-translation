#!/usr/bin/env python3
"""
Gundam SEED Rengou vs Z.A.F.T. Portable (ULJM05238) - proportional ASCII advance patch
for the SJIS sceFont text renderer at 0x088D2330 (wrapper 0x088D24DC).

usage: python3 patch.py [--mode prop|half] [--spacing N] [in.elf] [out.elf]
  prop (default): ASCII (UCS2 < 0x80) advances by (bitmapLeft + bitmapWidth + N) * size / 20,
                  where 20 = glyph-cache cell size; non-ASCII keeps fixed full-cell advance (size).
                  N (default 1) = extra spacing in 20px-cell pixels.
  half          : 3-word patch; ASCII advances size/2 (like the original space handling).
File offset = vaddr - 0x08804000 + 0x54.
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import struct, sys, argparse
BASE, OFF = 0x08804000, 0x54
def fo(va): return va - BASE + OFF

PROP_START = 0x088D23CC
PROP_ORIG_SHA1 = '13575db8228b562b321a1ce7564e1e9ca47f4bdf'   # sha1 of the 59 original words (little-endian) at PROP_START
PROP_NEW  = [0x10400026, 0xAFA2007C, 0x12400024, 0xC7A10098, 0x46800860, 0x3C0244A0, 0x46150842, 0x44820000, 0x12200012, 0x46000D03, 0xC7A00044, 0x3C023F80, 0x44821000, 0x46001000, 0xC7A10040, 0x3C028000, 0xAFA20070, 0x46011040, 0x27A40050, 0x46140000, 0xE7A10020, 0xE7A00024, 0x46160840, 0x4600A800, 0xE7A10030, 0x0E240A54, 0xE7A00034, 0xC7A00044, 0xC7A10040, 0x27A40050, 0x46140000, 0xE7A10020, 0xAFB20070, 0xE7A00024, 0x46160840, 0x4600A800, 0xE7A10030, 0x0E240A54, 0xE7A00034, 0x2E030080, 0x3C023F80, 0x1060000A, 0x44821000, 0x8FA20090, 0x8FA30094, 0x00431021, 0x24420001, 0x44821000, 0x468010A0, 0x3C0241A0, 0x44821800, 0x46031083, 0xC7A00040, 0x46161082, 0x46020000, 0x8FA300AC, 0x90630000, 0x1460FFBF, 0xE7A00040]
SPACING_VA = 0x088D2484   # addiu $v0,$v0,N  (N = spacing)

HALF = [  # (vaddr, sha1 of original word, new)
    (0x088D23D8, 'db709a58d15893bc07314da3d142dcf243232f29', 0x2E030080),  # delay slot of beql s2==0: addiu v1,zero,0x20 -> sltiu v1,s0,0x80
    (0x088D2478, 'db709a58d15893bc07314da3d142dcf243232f29', 0x2E030080),  # addiu v1,zero,0x20 -> sltiu v1,s0,0x80
    (0x088D247C, '496ad6c8c381805c51e953229dc10e666f476d5f', 0x50600008),  # bnel s0,v1,0x88d24a0 -> beql v1,zero,0x88d24a0
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['prop', 'half'], default='prop')
    ap.add_argument('--spacing', type=int, default=1)
    ap.add_argument('inp', nargs='?', default=P.eboot_dec())
    ap.add_argument('out', nargs='?', default=P.stage('eboot_propfont.elf'))
    a = ap.parse_args()
    b = bytearray(open(a.inp, 'rb').read())
    def rd(va): return struct.unpack_from('<I', b, fo(va))[0]
    def wr(va, w): struct.pack_into('<I', b, fo(va), w)
    if a.mode == 'prop':
        new = list(PROP_NEW)
        i = (SPACING_VA - PROP_START) // 4
        assert new[i] == 0x24420001
        assert -0x8000 <= a.spacing < 0x8000
        new[i] = 0x24420000 | (a.spacing & 0xffff)
        import hashlib
        cur = bytes(b[fo(PROP_START):fo(PROP_START) + 4 * len(new)])
        assert hashlib.sha1(cur).hexdigest() == PROP_ORIG_SHA1, 'original code at %08x does not match (wrong EBOOT?)' % PROP_START
        for k, n in enumerate(new):
            wr(PROP_START + 4 * k, n)
        print('prop patch: %d words at %08x (file 0x%x), spacing=%d' % (len(new), PROP_START, fo(PROP_START), a.spacing))
    else:
        import hashlib
        for va, h, n in HALF:
            assert hashlib.sha1(bytes(b[fo(va):fo(va) + 4])).hexdigest() == h, 'mismatch at %08x' % va
        for va, o, n in HALF:
            wr(va, n)
        print('half patch: %d words' % len(HALF))
    open(a.out, 'wb').write(b)
    print('wrote', a.out)

if __name__ == '__main__':
    main()
