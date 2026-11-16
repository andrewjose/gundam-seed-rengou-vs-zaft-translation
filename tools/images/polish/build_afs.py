#!/usr/bin/env python3
"""Build afs_out/afs_<idx>.bin ON TOP of the v0.4.2 entries: extract entry from X_DATA_v042.BIN, replace only the
changed sub-files (subs/<afs>_<sub>.bin), keep every other sub-file's on-disk bytes. Verifies each rebuilt entry:
pack parses, changed subs decompress to the new bytes, untouched subs byte-identical to v0.4.2.
Round 2: subs/ also holds PMF2 layout edits (<afs>_0.bin) and the copyright subs; one output set (afs_out/)."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import ppaths  # repo tool paths + work folders (see ppaths.py)
import sys, os, glob, json, struct
import afs, lz, pack, repack
W = ppaths.W
SRC = ppaths.BASE_XDATA
f, ents, _ = afs.read(SRC)

def entry(i):
    o, s = ents[i]; f.seek(o); return f.read(s)

def build(subdirs, outdir):
    os.makedirs(outdir, exist_ok=True)
    rep = {}
    for d in subdirs:
        for p in sorted(glob.glob(d + '/*.bin')):
            a, s = os.path.basename(p)[:-4].split('_', 1)
            rep.setdefault(int(a), {})[s] = open(p, 'rb').read()
    report = {}
    for i, subs in sorted(rep.items()):
        old = entry(i)
        if 'raw' in subs:
            new = subs['raw']; assert len(new) == len(old) and not pack.is_pack(old)
        else:
            r = {int(k): v for k, v in subs.items()}
            new = repack.rebuild_pack(old, r)
            assert pack.is_pack(new)
            so, _ = pack.parse(old); sn, _ = pack.parse(new)
            assert len(so) == len(sn)
            for j, (x, y) in enumerate(zip(so, sn)):
                if j in r:
                    got = lz.decompress(y['raw']) if y['flags'] & 1 else y['raw'][:len(r[j])]
                    assert got == r[j], (i, j)
                    assert y['flags'] == x['flags']
                else:
                    assert x['raw'] == y['raw'] and x['entry'] == y['entry'], (i, j)
        open('%s/afs_%d.bin' % (outdir, i), 'wb').write(new)
        report[i] = {'subs': sorted(subs), 'old_size': len(old), 'new_size': len(new), 'delta': len(new) - len(old)}
    return report

# round 2: the English copyright (subs_opt/2_16, 9_9) is folded into subs/, so afs_out/ is the single set.
# afs_optional/ is left as the round-1 artefact and no longer rebuilt.
main = build([W + '/subs'], W + '/afs_out')
json.dump({'main': main}, open(W + '/afs_build_report.json', 'w'), indent=1)
print('main', sorted(main), 'total delta', sum(v['delta'] for v in main.values()))
