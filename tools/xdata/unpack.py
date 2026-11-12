#!/usr/bin/env python3
"""Unpack every AFS entry of X_DATA.BIN; parse packs; decompress LZ sub-files.
usage: unpack.py [X_DATA.BIN] [out_dir]   (defaults: your X_DATA from config, <work>/xd_out)
Outputs <out_dir>/<afsidx>_<subidx>.bin (subidx 'raw' for non-pack entries) and <out_dir>/index.tsv"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import afs, lz, pack

AFS = sys.argv[1] if len(sys.argv) > 1 else P.xdata_orig()
OUT = sys.argv[2] if len(sys.argv) > 2 else P.unpacked()
os.makedirs(OUT, exist_ok=True)

def magic(b):
    m = b[:4]
    if len(m) == 4 and all(32 <= c < 127 for c in m): return m.decode()
    return m.hex()

f, ents, _ = afs.read(AFS)
idx = open(os.path.join(OUT, 'index.tsv'), 'w')
idx.write('afs\tsub\tcompressed\tcomp_size\tdecomp_size\tmagic\tnote\n')
stats = {'entries': 0, 'packs': 0, 'raw': 0, 'subs': 0, 'empty': 0, 'lz': 0, 'stored': 0, 'lzfail': 0}
for i, (o, s) in enumerate(ents):
    f.seek(o); d = f.read(s); stats['entries'] += 1
    if pack.is_pack(d):
        stats['packs'] += 1
        subs, _ = pack.parse(d)
        for j, sb in enumerate(subs):
            stats['subs'] += 1
            raw = sb['raw']
            if sb['sectors'] == 0:
                stats['empty'] += 1
                idx.write('%d\t%d\t-\t0\t0\t-\tempty\n' % (i, j)); continue
            note = ''
            if sb['flags'] & 1:
                try:
                    data, used = lz.decompress(raw, return_consumed=True)
                    stats['lz'] += 1; comp = used
                    if any(raw[used:]): note = 'trailing_nonzero'
                except Exception as ex:
                    stats['lzfail'] += 1; data = raw; comp = len(raw); note = 'LZFAIL:%s' % ex
                c = 'Y'
            else:
                stats['stored'] += 1; data = raw; comp = len(raw); c = 'N'
            if pack.is_pack(data): note += ' nested_pack'
            open(os.path.join(OUT, '%d_%d.bin' % (i, j)), 'wb').write(data)
            idx.write('%d\t%d\t%s\t%d\t%d\t%s\t%s\n' % (i, j, c, comp, len(data), magic(data), note.strip()))
    else:
        stats['raw'] += 1
        open(os.path.join(OUT, '%d_raw.bin' % i), 'wb').write(d)
        idx.write('%d\traw\tN\t%d\t%d\t%s\tnot_a_pack\n' % (i, s, s, magic(d)))
idx.close()
print(stats)
