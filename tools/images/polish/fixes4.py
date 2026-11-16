#!/usr/bin/env python3
"""v0.4.4 image polish, round 4 -> subs_r4/, afs_out_r4/ (each entry built on afs_out_r3 > afs_out > X_DATA_v042).
(a) Level-select header (PMF2 133 sub 0, object selmi02_si22, texture 133_1 pic8): two quads 'Choose the' (uv 0.5-121.5,
    row 0) + 'game level' (uv 0.5-115.5, row 18). Each word pair was drawn fitted to its 121/115-texel box, so 'Choose the'
    ink ends at texel 106 and the rest of its quad is empty -> ~15-texel gap. Nothing else is drawn there (the object has
    only these two quads). Fix: x-only shift of the two quads so the ink gap is 4 texels (same as the word gaps of
    'Choose your affiliation', same raw-per-texel scale) and the pair is centred on the object's original centre.
(b) Mission-menu level panel (texture 131_1 pic1; PMF2 131 sub 0: selmi00_mik0d = one quad over '<side> LV.' at uv
    0.5-53.9, mik0c = 'ZAFT' + the shared 'LV.' piece): 'EA' -> 'EAF' (DejaVu Sans Bold 11 hinted, as before), placed so
    the gap to 'LV.' equals the on-screen 'ZAFT'->'LV.' gap (7 texels). 'E.A.F.' (33 px) does not fit the 29-texel slot
    in the same face."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import ppaths  # repo tool paths + work folders (see ppaths.py)
import sys, os, json, struct, glob, numpy as np
import fixes2 as X
import fixes3 as R3
F = X.F; gimcodec = X.gimcodec
import afs, lz, pack, repack
W = F.W; OUT = F.OUT
S4 = W + '/subs_r4'; A4 = W + '/afs_out_r4'
os.makedirs(S4, exist_ok=True); os.makedirs(A4, exist_ok=True)
LOG = {}

def ink(a, x0, y0, x1, y1):
    r = a[y0:y1, x0:x1] > 40; xs = np.nonzero(r.any(0))[0]; return x0 + xs[0], x0 + xs[-1]

def fix_133_header():
    tex = gimcodec.rgba(gimcodec.decode(open(W + '/subs/133_1.bin', 'rb').read())[8])[..., 3]
    c0, c1 = ink(tex, 0, 0, 122, 18); g0, g1 = ink(tex, 0, 18, 116, 36)
    d0 = open(OUT + '/133_0.bin', 'rb').read(); d = bytearray(d0); ob = X.pmf_objs(d0)['selmi02_si22']
    qs = X.obj_quads(ob); vs = ob['vsize']
    Q = []
    for i, n in qs:
        vv = ob['verts'][i:i + n]
        u0 = min(v[0] for v in vv) * 128 / 32768; v0 = min(v[1] for v in vv) * 128 / 32768
        u1 = max(v[0] for v in vv) * 128 / 32768
        x0 = min(v[2] for v in vv); x1 = max(v[2] for v in vv)
        Q.append(dict(i=i, n=n, u0=u0, v0=v0, x0=x0, x1=x1, s=(x1 - x0) / (u1 - u0)))
    qc = [q for q in Q if q['v0'] < 10][0]; qg = [q for q in Q if q['v0'] > 10][0]
    s = qc['s']; GAP = 4
    old_c = (min(q['x0'] for q in Q) + max(q['x1'] for q in Q)) / 2
    # ink positions in a frame where the 'Choose' quad's left edge is 0
    ci0 = (c0 - qc['u0']) * s; ci1 = (c1 + 1 - qc['u0']) * s
    gi0 = ci1 + GAP * s                         # 'game' ink start
    gq0 = gi0 - (g0 - qg['u0']) * s             # 'game level' quad left
    gi1 = gq0 + (g1 + 1 - qg['u0']) * s
    shift = old_c - (ci0 + gi1) / 2
    newx = {id(qc): shift, id(qg): gq0 + shift}
    rec = {}
    for q in (qc, qg):
        dx = int(round(newx[id(q)] - q['x0']))
        for j in range(q['n']):
            off = ob['vaddr'] + vs * (q['i'] + j) + 4 + (vs - 10)
            x, = struct.unpack_from('<h', d, off); struct.pack_into('<h', d, off, x + dx)
        rec['row%d' % int(q['v0'])] = {'dx_raw': dx, 'old_x': [q['x0'], q['x1']]}
    X.check_pmf(d0, bytes(d), ['selmi02_si22'])
    open(S4 + '/133_0.bin', 'wb').write(bytes(d))
    LOG['133_si22'] = {'ink_choose_the': [int(c0), int(c1)], 'ink_game_level': [int(g0), int(g1)],
                       'old_gap_texels': round(((qg['x0'] + (g0 - qg['u0']) * s) - (qc['x0'] + (c1 + 1 - qc['u0']) * s)) / s, 1),
                       'new_gap_texels': GAP, 'quads': rec}

def fix_131_eaf():
    f = '131_1'; data, pics = F.load(f); p = pics[1]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    a = before[..., 3]
    lv0, _ = ink(a, 30, 0, 55, 16); z0, z1 = ink(a, 56, 0, 93, 16)
    d = open(OUT + '/131_0.bin', 'rb').read(); obs = X.pmf_objs(d)
    ob = obs['selmi00_mik0c']; qz = qlv = None
    for i, n in X.obj_quads(ob):
        vv = ob['verts'][i:i + n]; u0 = min(v[0] for v in vv) * 128 / 32768; u1 = max(v[0] for v in vv) * 128 / 32768
        q = (u0, u1, min(v[2] for v in vv), max(v[2] for v in vv))
        if u0 > 55: qz = q
        else: qlv = q
    sz = (qz[3] - qz[2]) / (qz[1] - qz[0])
    gap = ((qlv[2] + (lv0 - qlv[0]) * sz) - (qz[2] + (z1 + 1 - qz[0]) * sz)) / sz
    gap = int(round(gap))
    cv[0:17, 0:31] = 0
    w = X.wplain('EAF', 'sans', 11, 1)
    x = lv0 - gap - w
    assert x >= 1, x
    F.place(cv, x, 11, 'EAF', 'sans', 11, ss=1)
    e0, e1 = ink(cv[..., 3], 0, 0, 31, 17)
    F.commit('r4_131', f, data, pics, 1, cv, before, 'EA -> EAF, gap to LV. = ZAFT->LV. gap (%d texels)' % gap)
    R3.S3 = S4; R3.save_gim(f, data, pics); R3.prev(f, 1, (0, 0, 100, 34), 'eaf', 5)
    LOG['131_eaf'] = {'text': 'EAF', 'ink_x': [int(e0), int(e1)], 'LV_ink_start': int(lv0), 'gap_texels': gap}

def build():
    fx, ents, _ = afs.read(ppaths.BASE_XDATA)
    rep = {}
    for pth in sorted(glob.glob(S4 + '/*.bin')):
        a, s = os.path.basename(pth)[:-4].split('_', 1); rep.setdefault(int(a), {})[int(s)] = open(pth, 'rb').read()
    rpt = {}
    for i, subs in sorted(rep.items()):
        for base in ('afs_out_r3', 'afs_out'):
            bp = '%s/%s/afs_%d.bin' % (W, base, i)
            if os.path.exists(bp): old = open(bp, 'rb').read(); break
        else: fx.seek(ents[i][0]); old = fx.read(ents[i][1]); base = 'X_DATA_v042'
        new = repack.rebuild_pack(old, subs)
        so, _ = pack.parse(old); sn, _ = pack.parse(new)
        for j, (x, y) in enumerate(zip(so, sn)):
            if j in subs:
                got = lz.decompress(y['raw']) if y['flags'] & 1 else y['raw'][:len(subs[j])]
                assert got == subs[j] and y['flags'] == x['flags'], (i, j)
            else: assert x['raw'] == y['raw'] and x['entry'] == y['entry'], (i, j)
        open('%s/afs_%d.bin' % (A4, i), 'wb').write(new)
        rpt[i] = {'base': base, 'subs': sorted(subs), 'old_size': len(old), 'new_size': len(new), 'delta': len(new) - len(old)}
    return rpt

if __name__ == '__main__':
    fix_133_header(); fix_131_eaf()
    LOG['build'] = build(); LOG['quant'] = F.LOG
    json.dump(LOG, open(W + '/r4_report.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(LOG, indent=1, default=str))
