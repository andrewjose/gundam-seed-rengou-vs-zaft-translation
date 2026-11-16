#!/usr/bin/env python3
"""v0.4.4 image polish, round 5 -> subs_r5/, afs_out_r5/ (entry built on afs_out_r4 > afs_out_r3 > afs_out > X_DATA).
VS. SETTINGS (AFS 125: sub 0 PMF2 'selvs02_*', sub 1 pic0 512x256 texture; same entry as the round-3 header fix).
(1) Row labels: objects k69 Stage, k6a BGM, k6b/k6c [A|B]+Team Force Gauge, k6d Damage Level, k6e Timer, k6f Boost Gauge,
    k70 Awaken Gauge Rate, k71 Awaken Time; each one quad, left x = -28202, 21-texel rows, same raw/texel scale.
    v0.4.2: Roboto Condensed Bold 14 (cap 10) except 'BGM' = original big art (cap 16). Now all Roboto Condensed Bold 18
    (cap 13), white, Hg block vertically centred in the 21-texel row, left at slot x+1. 'Awaken Time' (96 px) did not fit
    its 80-texel slot: slots re-split on that row (Damage Level 0-104, Awaken Time 105-207) with k6d/k71 quads' uv and right
    x updated (left x unchanged). Other quads untouched (uv/x identical).
(2) BGM value: object k9f = 'Auto' piece (uv 389.5-425.5 row 156) + 'Select' piece (uv 471.5-510.5 row 116), placed at
    their box edges -> ink gap ~14 texels. 'Select' quad moved left so the ink gap is one space of the font (rc13).
    The orange tint and size are the BGM-title style (same pieces/font as the song list); not changed."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import ppaths  # repo tool paths + work folders (see ppaths.py)
import sys, os, json, struct, glob, numpy as np
import fixes2 as X
import fixes3 as R3
F = X.F; gimcodec = X.gimcodec; engine = X.engine
import afs, lz, pack, repack
W = F.W; OUT = F.OUT
S5 = W + '/subs_r5'; A5 = W + '/afs_out_r5'
os.makedirs(S5, exist_ok=True); os.makedirs(A5, exist_ok=True)
LOG = {}
TW, TH = 512, 256

def ink(a, x0, y0, x1, y1):
    r = a[y0:y1, x0:x1] > 40; xs = np.nonzero(r.any(0))[0]; return x0 + xs[0], x0 + xs[-1]

def fix_125():
    f = '125_1'; data, pics = F.load(f, W + '/subs_r3'); p = pics[0]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    # (obj, text, slot x0, x1 (exclusive), row top)
    L = [('selvs02_k6b', 'Team Force Gauge', 36, 176, 112), ('selvs02_k6e', 'Timer', 176, 249, 112),
         ('selvs02_k6d', 'Damage Level', 0, 105, 134), ('selvs02_k71', 'Awaken Time', 105, 208, 134),
         ('selvs02_k6f', 'Boost Gauge', 0, 141, 156), ('selvs02_k69', 'Stage', 141, 218, 156),
         ('selvs02_k70', 'Awaken Gauge Rate', 0, 155, 178), ('selvs02_k6a', 'BGM', 155, 203, 178)]
    clear = [(36, 112, 249, 134), (0, 134, 208, 156), (0, 156, 218, 178), (0, 178, 203, 200)]
    for x0, y0, x1, y1 in clear: cv[y0:y1, x0:x1] = 0
    FN, SZ = 'rc', 18
    a, top, bot, base, capt = engine.render_line('Hg', FN, SZ, 1.0, 0, 4)
    boff = (21 - (bot - top)) // 2 + (base - top)
    sizes = {}
    for ob, t, x0, x1, y in L:
        lx = x0 + (4 if t == 'Team Force Gauge' else 1)      # keep a gap after the 'A'/'B' art piece
        w = F.place(cv, lx, y + boff, t, FN, SZ, ss=4)
        assert lx + w + 1 <= x1, (t, w, x0, x1)
        sizes[t] = w
    F.commit('r5_125', f, data, pics, 0, cv, before, 'VS settings row labels all rc18 (BGM art replaced); Damage/Awaken Time slots re-split')
    R3.S3 = S5; R3.save_gim(f, data, pics)
    R3.prev(f, 0, (0, 108, 256, 202), 'labels', 3)
    os.replace(W + '/previews/r3_125_1_0_labels.png', W + '/previews/r5_125_1_0_labels.png')
    # PMF2
    d0 = open(OUT + '/125_0.bin', 'rb').read(); d = bytearray(d0); obs = X.pmf_objs(d0)
    rec = {}
    for name, (nu0, nu1) in (('selvs02_k6d', (0.5, 104.5)), ('selvs02_k71', (105.5, 207.5))):
        ob = obs[name]; (i, n), = X.obj_quads(ob); vv = ob['verts'][i:i + n]
        u0 = min(v[0] for v in vv) * TW / 32768; u1 = max(v[0] for v in vv) * TW / 32768
        xL = min(v[2] for v in vv); xR = max(v[2] for v in vv); s = (xR - xL) / (u1 - u0)
        nxR = int(round(xL + (nu1 - nu0) * s))
        for j, (u, v, x, y, z) in enumerate(vv):
            L_ = (x == xL)
            struct.pack_into('<HHhhh', d, ob['vaddr'] + 10 * (i + j), int(round((nu0 if L_ else nu1) * 32768 / TW)), v, xL if L_ else nxR, y, z)
        rec[name] = {'uv_x': [nu0, nu1], 'old_uv_x': [u0, u1], 'x': [xL, nxR], 'old_x': [xL, xR]}
    # BGM value gap (k9f)
    ob = obs['selvs02_k9f']; qs = X.obj_quads(ob)
    Q = []
    for i, n in qs:
        vv = ob['verts'][i:i + n]
        Q.append(dict(i=i, n=n, u0=min(v[0] for v in vv) * TW / 32768, u1=max(v[0] for v in vv) * TW / 32768,
                      v0=min(v[1] for v in vv) * TH / 32768, xL=min(v[2] for v in vv), xR=max(v[2] for v in vv)))
    qa = [q for q in Q if q['u0'] < 450][0]; qs_ = [q for q in Q if q['u0'] > 450][0]
    tex = cv[..., 3]
    a0, a1 = ink(tex, int(qa['u0']), int(qa['v0']), int(qa['u1']) + 1, int(qa['v0']) + 19)
    s0, s1 = ink(tex, int(qs_['u0']), int(qs_['v0']), int(qs_['u1']) + 1, int(qs_['v0']) + 19)
    sa = (qa['xR'] - qa['xL']) / (qa['u1'] - qa['u0'])
    gap = X.gap('Auto', 'Select', 'rc', 13, 4)
    auto_end = qa['xL'] + (a1 + 1 - qa['u0']) * sa
    old_gap = ((qs_['xL'] + (s0 - qs_['u0']) * sa) - auto_end) / sa
    newL = auto_end + gap * sa - (s0 - qs_['u0']) * sa
    dx = int(round(newL - qs_['xL']))
    for j in range(qs_['n']):
        off = ob['vaddr'] + ob['vsize'] * (qs_['i'] + j) + 4 + (ob['vsize'] - 10)
        x, = struct.unpack_from('<h', d, off); struct.pack_into('<h', d, off, x + dx)
    rec['selvs02_k9f'] = {'select_dx_raw': dx, 'old_gap_texels': round(old_gap, 1), 'new_gap_texels': gap}
    X.check_pmf(d0, bytes(d), ['selvs02_k6d', 'selvs02_k71', 'selvs02_k9f'])
    open(S5 + '/125_0.bin', 'wb').write(bytes(d))
    LOG['125'] = {'label_widths_rc18': sizes, 'pmf': rec}
    # simulated on-screen rows
    from PIL import Image
    rows = []
    for src, texsrc in ((OUT + '/125_0.bin', W + '/subs_r3/125_1.bin'), (S5 + '/125_0.bin', S5 + '/125_1.bin')):
        pp = gimcodec.decode(open(texsrc, 'rb').read())[0]; t = pp.pal[pp.idx]
        o2 = X.pmf_objs(open(src, 'rb').read())
        img = Image.new('RGBA', (260, 10 * 24 + 4), (24, 24, 96, 255))
        for k, name in enumerate(['selvs02_k69', 'selvs02_k6a', 'selvs02_k6b', 'selvs02_k6c', 'selvs02_k6d', 'selvs02_k6e',
                                  'selvs02_k6f', 'selvs02_k70', 'selvs02_k71', 'selvs02_k9f']):
            ob = o2[name]
            for i, n in X.obj_quads(ob):
                vv = ob['verts'][i:i + n]
                u0 = min(v[0] for v in vv) * TW / 32768; u1 = max(v[0] for v in vv) * TW / 32768
                v0 = min(v[1] for v in vv) * TH / 32768; v1 = max(v[1] for v in vv) * TH / 32768
                xL = min(v[2] for v in vv); xR = max(v[2] for v in vv)
                if u1 - u0 < 2: continue
                c = Image.fromarray(t[int(v0):int(round(v1)), int(u0):int(round(u1))], 'RGBA')
                c = c.resize((max(1, int(round((xR - xL) / 98.9))), c.height), Image.NEAREST)
                img.alpha_composite(c, (int(round((xL + 28300) / 98.9)), 2 + 24 * k))
        rows.append(img.resize((img.width * 2, img.height * 2), Image.NEAREST))
    S = Image.new('RGB', (rows[0].width * 2 + 8, rows[0].height), (255, 0, 255))
    S.paste(rows[0].convert('RGB'), (0, 0)); S.paste(rows[1].convert('RGB'), (rows[0].width + 8, 0))
    S.save(W + '/previews/r5_125_rows_before_after.png')

def build():
    fx, ents, _ = afs.read(ppaths.BASE_XDATA)
    rep = {}
    for pth in sorted(glob.glob(S5 + '/*.bin')):
        a, s = os.path.basename(pth)[:-4].split('_', 1); rep.setdefault(int(a), {})[int(s)] = open(pth, 'rb').read()
    rpt = {}
    for i, subs in sorted(rep.items()):
        for base in ('afs_out_r4', 'afs_out_r3', 'afs_out'):
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
        open('%s/afs_%d.bin' % (A5, i), 'wb').write(new)
        rpt[i] = {'base': base, 'subs': sorted(subs), 'old_size': len(old), 'new_size': len(new), 'delta': len(new) - len(old)}
    return rpt

if __name__ == '__main__':
    fix_125()
    LOG['build'] = build(); LOG['quant'] = F.LOG
    json.dump(LOG, open(W + '/r5_report.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(LOG, default=str))
