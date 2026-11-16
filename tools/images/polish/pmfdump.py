#!/usr/bin/env python3
"""Dump PMF2 layout objects (name, prims, vertices) of out/<afs>_0.bin. Usage: pmfdump.py 129 [129 ...]"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import ppaths  # repo tool paths + work folders (see ppaths.py)
import sys, struct
import pmf
W = ppaths.W
def load(a):
    d = open('%s/%s_0.bin' % (ppaths.OUT, a), 'rb').read()
    res = []
    for o in pmf.objects(d):
        try: res.append(pmf.parse_obj(d, o))
        except Exception as ex: res.append({'name': d[o+0x60:o+0x70].split(b'\0')[0].decode(), 'err': str(ex), 'off': o})
    return d, res
if __name__ == '__main__':
    for a in sys.argv[1:]:
        d, objs = load(a)
        for ob in objs:
            if 'err' in ob: print(a, ob['name'], 'ERR', ob['err']); continue
            us = [v[0] for v in ob['verts']]; vs = [v[1] for v in ob['verts']]
            xs = [v[2] for v in ob['verts']]; ys = [v[3] for v in ob['verts']]
            print(a, ob['name'], hex(ob['vtype']), ob['prims'], 'uv', min(us), min(vs), max(us), max(vs), 'xy', min(xs), min(ys), max(xs), max(ys),
                  'hdr', ['%.3g' % h for h in ob['hdr'][:16]])
