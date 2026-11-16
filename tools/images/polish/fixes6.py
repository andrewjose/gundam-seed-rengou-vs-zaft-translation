#!/usr/bin/env python3
"""v0.4.4 image polish, round 6 -> subs_r6/, afs_out_r6/ (entry built on the newest of afs_out_r5/r4/r3/afs_out/X_DATA).
Link-battle RESULT REPORT buttons: AFS 1609 (sub 0 PMF2 'result02_rmXX', sub 1 pic0 128x128 texture; same entry as the
round-3 'OK' fix). Buttons: rm02 'Rematch' (1 quad), rm03 [serekuto|gamen-e] = 'VS Select' + blank piece, rm17
[robii|gamen-e] = 'Lobby' piece + blank piece, rm18 'End Link' (1 quad). (rm04 = [menyuu|gamen-e].)
- v0.4.2 drew 'Lobby Menu' across the robii (1.5-37.5) and menyuu (37.5-85.5) slots of row 80, so rm17 showed 'Lobby M'.
  Now 'Lobby' is centred in the robii slot and 'Menu' in the menyuu slot (rc12, as before).
- rm03/rm17: the text quad sat at the left of the button span (the blank gamen-e quad filled the right half). The text quad
  is now centred on the object's original span and the blank quad is zero-area."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import ppaths  # repo tool paths + work folders (see ppaths.py)
import sys, os, json, struct, glob, numpy as np
import fixes2 as X
import fixes3 as R3
F = X.F; gimcodec = X.gimcodec; engine = X.engine
import afs, lz, pack, repack
W = F.W; OUT = F.OUT
S6 = W + '/subs_r6'; A6 = W + '/afs_out_r6'
os.makedirs(S6, exist_ok=True); os.makedirs(A6, exist_ok=True)
LOG = {}; TW = TH = 128

def fix_1609():
    f = '1609_1'; data, pics = F.load(f, W + '/subs_r3'); p = pics[0]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    cv[80:96, 0:86] = 0
    engine.draw_text(cv, (2, 81, 37, 95), 'Lobby', fname='rc', size=12, ss=4, align='center')
    engine.draw_text(cv, (38, 81, 85, 95), 'Menu', fname='rc', size=12, ss=4, align='center')
    # 'End Link' (rm18, one quad over uv 0.5-57.5 row 96) was left-aligned in its slot -> centred like the other buttons
    cv[96:112, 0:58] = 0
    engine.draw_text(cv, (1, 97, 57, 111), 'End Link', fname='rc', size=12, ss=4, align='center')
    F.commit('r6_1609', f, data, pics, 0, cv, before, "'Lobby Menu' split into centred 'Lobby' / 'Menu' pieces; 'End Link' centred in its slot")
    R3.S3 = S6; R3.save_gim(f, data, pics); R3.prev(f, 0, (0, 62, 128, 112), 'buttons', 4)
    os.replace(W + '/previews/r3_1609_1_0_buttons.png', W + '/previews/r6_1609_1_0_buttons.png')
    d0 = open(OUT + '/1609_0.bin', 'rb').read(); d = bytearray(d0); obs = X.pmf_objs(d0)
    rec = {}
    for name in ('result02_rm03', 'result02_rm17'):
        ob = obs[name]; qs = X.obj_quads(ob)
        Q = []
        for i, n in qs:
            vv = ob['verts'][i:i + n]
            Q.append(dict(i=i, n=n, u0=min(v[0] for v in vv) * TW / 32768, u1=max(v[0] for v in vv) * TW / 32768,
                          xL=min(v[2] for v in vv), xR=max(v[2] for v in vv)))
        blank = [q for q in Q if q['u0'] > 84][0]; txt = [q for q in Q if q['u0'] < 84][0]
        c = (min(q['xL'] for q in Q) + max(q['xR'] for q in Q)) / 2
        w = txt['xR'] - txt['xL']; nL = int(round(c - w / 2)); dx = nL - txt['xL']
        vs = ob['vsize']
        for j in range(txt['n']):
            off = ob['vaddr'] + vs * (txt['i'] + j) + 4 + (vs - 10)
            x, = struct.unpack_from('<h', d, off); struct.pack_into('<h', d, off, x + dx)
        # blank quad -> zero area (all verts = its first vert)
        first = d[ob['vaddr'] + vs * blank['i']: ob['vaddr'] + vs * (blank['i'] + 1)]
        for j in range(blank['n']):
            d[ob['vaddr'] + vs * (blank['i'] + j): ob['vaddr'] + vs * (blank['i'] + j + 1)] = first
        rec[name] = {'text_uv': [txt['u0'], txt['u1']], 'text_dx_raw': dx, 'span_center': c, 'blank_zeroed': [blank['u0'], blank['u1']]}
    X.check_pmf(d0, bytes(d), ['result02_rm03', 'result02_rm17'])
    open(S6 + '/1609_0.bin', 'wb').write(bytes(d))
    LOG['1609'] = rec
    # simulated buttons
    from PIL import Image
    rows = []
    for src, texsrc in ((OUT + '/1609_0.bin', W + '/subs_r3/1609_1.bin'), (S6 + '/1609_0.bin', S6 + '/1609_1.bin')):
        pp = gimcodec.decode(open(texsrc, 'rb').read())[0]; t = pp.pal[pp.idx]
        o2 = X.pmf_objs(open(src, 'rb').read())
        img = Image.new('RGBA', (400, 22), (24, 24, 96, 255))
        for name in ('result02_rm02', 'result02_rm03', 'result02_rm17', 'result02_rm18'):
            ob = o2[name]; xs_all = [v[2] for v in ob['verts']]
            for i, n in X.obj_quads(ob):
                vv = ob['verts'][i:i + n]
                u0 = min(v[0] for v in vv) * TW / 32768; u1 = max(v[0] for v in vv) * TW / 32768
                v0 = min(v[1] for v in vv) * TH / 32768; v1 = max(v[1] for v in vv) * TH / 32768
                xL = min(v[2] for v in vv); xR = max(v[2] for v in vv)
                if xR == xL or u1 - u0 < 2: continue
                cimg = Image.fromarray(t[int(v0):int(round(v1)), int(u0):int(round(u1))], 'RGBA')
                cimg = cimg.resize((max(1, int(round((xR - xL) / 165))), cimg.height), Image.NEAREST)
                img.alpha_composite(cimg, (int(round((xL + 32768) / 165)), 3))
            # button span markers
            a0 = int(round((min(xs_all) + 32768) / 165)); a1 = int(round((max(xs_all) + 32768) / 165))
            for xx in (a0, a1 - 1): img.putpixel((xx, 20), (255, 200, 0, 255)); img.putpixel((xx, 19), (255, 200, 0, 255))
        rows.append(img.resize((img.width * 3, img.height * 3), Image.NEAREST))
    S = Image.new('RGB', (rows[0].width, rows[0].height * 2 + 6), (255, 0, 255))
    S.paste(rows[0].convert('RGB'), (0, 0)); S.paste(rows[1].convert('RGB'), (0, rows[0].height + 6))
    S.save(W + '/previews/r6_1609_buttons_before_after.png')

def build():
    fx, ents, _ = afs.read(ppaths.BASE_XDATA)
    rep = {}
    for pth in sorted(glob.glob(S6 + '/*.bin')):
        a, s = os.path.basename(pth)[:-4].split('_', 1); rep.setdefault(int(a), {})[int(s)] = open(pth, 'rb').read()
    rpt = {}
    for i, subs in sorted(rep.items()):
        for base in ('afs_out_r5', 'afs_out_r4', 'afs_out_r3', 'afs_out'):
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
        open('%s/afs_%d.bin' % (A6, i), 'wb').write(new)
        rpt[i] = {'base': base, 'subs': sorted(subs), 'old_size': len(old), 'new_size': len(new), 'delta': len(new) - len(old)}
    return rpt

def fix_options():
    """Options (AFS 2: sub 19 PMF2 'menu01_gXX', sub 20 pic0 texture; not shared with AFS 125).
    Labels were rc15 word pieces (round 1), several rows composed from JP word pieces (buusuto|geeji|ryou, kakusei|geeji|zoukaritsu,
    kakusei|jikan, ooto|seebu) -> wide gaps; BGM/SE original big art. Now every row label is one Roboto Condensed Bold 18
    piece (the round-5 VS. SETTINGS style; both PMFs draw 1 texel = 0.623 units, so the size matches on screen), one quad
    per label at the object's original left x, surplus quads zero-area. Wording as VS. SETTINGS: Boost Gauge, Awaken Gauge
    Rate, Awaken Time. Load/Save tab: Load, Save, Delete, and 'Auto' + 'Save' ('Automatic' does not fit the 65-texel slot)."""
    f = '2_20'; data, pics = F.load(f, W + '/subs'); p = pics[0]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    for x0, y0, x1, y1 in ((0, 106, 256, 128), (0, 128, 256, 150), (0, 150, 147, 172), (217, 150, 256, 172),
                           (0, 172, 55, 194), (200, 172, 256, 194), (0, 194, 179, 216)):
        cv[y0:y1, x0:x1] = 0
    FN, SZ = 'rc', 18
    a, top, bot, base, capt = engine.render_line('Hg', FN, SZ, 1.0, 0, 4)
    boff = (21 - (bot - top)) // 2 + (base - top)
    P = {'dif': ('Difficulty', 1, 106), 'dam': ('Damage Level', 70, 106), 'tim': ('Timer', 174, 106),
         'agr': ('Awaken Gauge Rate', 1, 128), 'at': ('Awaken Time', 149, 128),
         'bg': ('Boost Gauge', 1, 150), 'bgm': ('BGM', 96, 150), 'se': ('SE', 222, 150),
         'voi': ('Voice', 1, 172), 'del': ('Delete', 205, 172),
         'load': ('Load', 1, 194), 'save': ('Save', 60, 194), 'auto': ('Auto', 116, 194)}
    lim = {'bgm': 147, 'voi': 55, 'load': 57, 'save': 113, 'auto': 179, 'se': 256, 'del': 256}
    pcs = {}
    for k, (t, x, y) in P.items():
        w = F.place(cv, x, y + boff, t, FN, SZ, ss=4)
        assert x + w + 1 <= lim.get(k, 256), (t, x, w)
        pcs[k] = dict(t=t, x=x, w=w, y=y)
    for r in set(v['y'] for v in pcs.values()):
        rr = sorted((v['x'] - 1, v['x'] + v['w'] + 1) for v in pcs.values() if v['y'] == r)
        for (a0, a1), (b0, b1) in zip(rr, rr[1:]): assert a1 <= b0, rr
    F.commit('r6_2_20', f, data, pics, 0, cv, before, 'options labels: one rc18 piece per row label')
    R3.S3 = S6; R3.save_gim(f, data, pics); R3.prev(f, 0, (0, 100, 256, 220), 'labels', 3)
    os.replace(W + '/previews/r3_2_20_0_labels.png', W + '/previews/r6_2_20_0_labels.png')
    d0 = open(OUT + '/2_19.bin', 'rb').read(); d = bytearray(d0); obs = X.pmf_objs(d0)
    M = {'menu01_g28': ['dif'], 'menu01_g29': ['dam'], 'menu01_g2a': ['tim'], 'menu01_g2b': ['bg'], 'menu01_g2c': ['agr'],
         'menu01_g2d': ['at'], 'menu01_g30': ['bgm'], 'menu01_g2f': ['se'], 'menu01_g31': ['voi'], 'menu01_g4e': ['load'],
         'menu01_g4f': ['save'], 'menu01_g50': ['auto', 'save'], 'menu01_g08': ['del']}
    gf = lambda a, b: X.gap(pcs[a]['t'], pcs[b]['t'], FN, SZ, 4)
    rec = {}
    for name, order in M.items():
        ob = obs[name]; assert ob['tex'] == 0
        sx, sy = X.obj_scale(ob, 256, 256)
        Lx = min(v[2] for v in ob['verts']); Yt = max(v[3] for v in ob['verts'])
        lay = X.layout(pcs, order, gf, sx, left=Lx)
        qs = [X.quad_of(pcs[n], Xr, Yt, 21, sx, sy, pcs[n]['y']) for n, Xr in lay]
        rec[name] = {'label': ' '.join(pcs[n]['t'] for n in order), 'left_x': Lx,
                     'right_x': int(round(lay[-1][1] + (pcs[order[-1]]['w'] + 2) * sx)),
                     'old_right_x': max(v[2] for v in ob['verts']), 'quads': X.set_quads(d, ob, qs, 256, 256)}
    X.check_pmf(d0, bytes(d), list(M))
    open(S6 + '/2_19.bin', 'wb').write(bytes(d))
    LOG['2_options'] = rec

if __name__ == '__main__':
    fix_1609(); fix_options()
    LOG['build'] = build(); LOG['quant'] = F.LOG
    json.dump(LOG, open(W + '/r6_report.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(LOG, default=str))
