#!/usr/bin/env python3
"""List every quad of a PMF2 (out/<afs>_0.bin) with its texture index (u32 @obj+0x74) and texel rect.
Usage: pmfuse.py <afs> [tex]"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import ppaths  # repo tool paths + work folders (see ppaths.py)
import sys, struct
import pmfdump
def quads(a):
    d, objs = pmfdump.load(a)
    out = []
    for ob in objs:
        if 'err' in ob: continue
        tex, = struct.unpack_from('<I', d, ob["off"] + 0x74)
        i = 0
        for qi, (t, n) in enumerate(ob['prims']):
            vv = ob['verts'][i:i + n]; i += n
            us = [v[0] / 128 for v in vv]; vs = [v[1] / 128 for v in vv]; xs = [v[2] for v in vv]; ys = [v[3] for v in vv]
            out.append(dict(obj=ob['name'], q=qi, n=n, tex=tex, u0=min(us), v0=min(vs), u1=max(us), v1=max(vs),
                            x0=min(xs), y0=min(ys), x1=max(xs), y1=max(ys)))
    return out
if __name__ == '__main__':
    a = sys.argv[1]; tx = int(sys.argv[2]) if len(sys.argv) > 2 else None
    for q in quads(a):
        if tx is None or q['tex'] == tx:
            print('%-10s q%d n%-2d tex%d uv(%5.1f,%5.1f)-(%5.1f,%5.1f)  xy(%6d,%6d)-(%6d,%6d)' % (q['obj'], q['q'], q['n'], q['tex'], q['u0'], q['v0'], q['u1'], q['v1'], q['x0'], q['y0'], q['x1'], q['y1']))
