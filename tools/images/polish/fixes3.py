#!/usr/bin/env python3
"""v0.4.4 image polish, round 3 (layered on round 2's afs_out/).
Writes subs_r3/<afs>_<sub>.bin and afs_out_r3/afs_<idx>.bin (built on afs_out/afs_<idx>.bin when round 1/2 changed that
entry, else on X_DATA_v042). Previews in previews/r3_*.

- 2_11 + 2_10 (Pause > Buttons): the combo rows are PMF2 objects keyconf00_kc08..kc11 in AFS 2 sub 10 (texture = sub 11
  pic0, 128x128). Each row = button word quads + '+' icons + one parenthesised label quad. v0.4.2: labels fitted per box
  (Awaken smaller), label quads placed right after the preceding word's rect (Sub Shot touching 'Melee', the others
  20 texels further right). Now: all four labels Roboto Condensed Bold 11, same baseline; '(Awaken)' moved to a free
  43-texel slot (x22, y72) because its old 34-texel slot cannot hold it at size 11; every label quad starts at one
  common column = max(preceding word ink end) + 10 texels (~5 px on screen).
- 125_1 pic0 (VS settings): header words Player/ Team Mobile Suit Level Pilot Play were DejaVu Sans Bold; now Roboto
  Condensed Bold 13 like the setting labels (same boxes, left-aligned; 'Play' fitted to its small box).
- 1609_1 pic0 (result screen): standalone 'OK' (PMF2 result02_rm08, uv 6.5-34.5 x 48.5-63.5) was the original big Latin
  art; now Roboto Condensed Bold 12 like every other word on this texture, centred in its slot."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import ppaths  # repo tool paths + work folders (see ppaths.py)
import sys, os, json, struct, glob, numpy as np
from PIL import Image
import fixes2 as X
F = X.F; engine = X.engine; gimcodec = X.gimcodec
import afs, lz, pack, repack
W = F.W; OUT = F.OUT
S3 = W + '/subs_r3'; A3 = W + '/afs_out_r3'
os.makedirs(S3, exist_ok=True); os.makedirs(A3, exist_ok=True)
LOG = {}

def save_gim(f, data, pics):
    new = gimcodec.encode(data, pics); chk = gimcodec.decode(new)
    for p, q in zip(pics, chk):
        assert np.array_equal(p.idx, q.idx)
    assert gimcodec.encode(new, chk) == new and len(new) == len(data)
    open('%s/%s.bin' % (S3, f), 'wb').write(new)

def prev(f, k, box, tag, scale=3):
    ims = []
    for src in (OUT, S3):
        p = gimcodec.decode(open('%s/%s.bin' % (src, f), 'rb').read())[k]
        im = Image.fromarray(p.pal[p.idx], 'RGBA').crop(box)
        bg = Image.new('RGBA', im.size, (24, 24, 96, 255)); bg.alpha_composite(im)
        ims.append(bg.convert('RGB').resize((im.width * scale, im.height * scale), Image.NEAREST))
    S = Image.new('RGB', (ims[0].width, ims[0].height * 2 + 6), (255, 0, 255))
    S.paste(ims[0], (0, 0)); S.paste(ims[1], (0, ims[0].height + 6)); S.save('%s/previews/r3_%s_%d_%s.png' % (W, f, k, tag))

def ink_x1(a, x0, y0, x1, y1):
    r = a[y0:y1, x0:x1] > 40; xs = np.nonzero(r.any(0))[0]; return x0 + xs[-1]

def fix_2_11():
    f = '2_11'; data, pics = F.load(f); p = pics[0]; TW = TH = 128
    cv = gimcodec.rgba(p).copy(); before = cv.copy(); alpha0 = before[..., 3]
    clear = [(0, 32, 92, 46), (0, 46, 58, 60), (0, 60, 58, 74)]
    for x0, y0, x1, y1 in clear: cv[y0:y1, x0:x1] = 0
    assert not cv[72:86, 20:66, 3].any(), 'awaken slot not free'
    FN, SZ, SS = 'rc', 11, 4
    L = {'sub': ('(Sub Shot)', 0, 32), 'sps': ('(Sp.Shot)', 0, 46), 'spm': ('(Sp.Melee)', 0, 60), 'aw': ('(Awaken)', 22, 72)}
    pcs = {}
    for n, (t, sx_, top) in L.items():
        w = F.place(cv, sx_ + 1, top + 10, t, FN, SZ, ss=SS)
        pcs[n] = dict(t=t, x=sx_ + 1, w=w, y=top)
        assert sx_ + 1 + w + 1 <= (58 if n != 'aw' else 92), (t, w)
    F.commit('r3_2_11', f, data, pics, 0, cv, before, 'paren labels rc11, Awaken moved to slot (22,72)')
    save_gim(f, data, pics); prev(f, 0, (0, 30, 128, 88), 'labels')
    # PMF2 (AFS 2 sub 10)
    d0 = open('%s/2_10.bin' % OUT, 'rb').read(); d = bytearray(d0); obs = X.pmf_objs(d0)
    rows = {'keyconf00_kc08': ('aw', 4, 5), 'keyconf00_kc09': ('sub', 0, 2), 'keyconf00_kc10': ('sps', 0, 2),
            'keyconf00_kc11': ('spm', 0, 2)}           # object: (label, label prim index, preceding-word prim index)
    info = {}
    for name, (lab, li, pi) in rows.items():
        ob = obs[name]; qs = X.obj_quads(ob)
        i, n = qs[li]; vl = ob['verts'][i:i + n]
        assert abs(min(v[1] for v in vl) * TH / 32768 - (L[lab][2] + .5 if lab != 'aw' else 32.5)) < .01, (name, lab)
        sx = (max(v[2] for v in vl) - min(v[2] for v in vl)) / ((max(v[0] for v in vl) - min(v[0] for v in vl)) * TW / 32768)
        sy = (max(v[3] for v in vl) - min(v[3] for v in vl)) / ((max(v[1] for v in vl) - min(v[1] for v in vl)) * TH / 32768)
        j, m = qs[pi]; vp = ob['verts'][j:j + m]
        pu0 = min(v[0] for v in vp) * TW / 32768; pv0 = min(v[1] for v in vp) * TH / 32768
        pu1 = max(v[0] for v in vp) * TW / 32768; pv1 = max(v[1] for v in vp) * TH / 32768
        e = ink_x1(alpha0, int(pu0), int(pv0), int(pu1) + 1, int(pv1) + 1)
        prev_end = min(v[2] for v in vp) + (e + 1 - pu0) * sx
        info[name] = dict(lab=lab, li=li, sx=sx, sy=sy, prev_end=prev_end, Yt=max(v[3] for v in vl),
                          old=[min(v[2] for v in vl), max(v[2] for v in vl)])
    GAP = 10
    col = max(v['prev_end'] for v in info.values()) + GAP * max(v['sx'] for v in info.values())
    rec = {}
    for name, v in info.items():
        pc = pcs[v['lab']]
        q = dict(tx=pc['x'] - 1, ty=pc['y'], tw=pc['w'] + 2, th=13, X=col - 1 * v['sx'], Yt=v['Yt'], sx=v['sx'], sy=v['sy'])
        ql = [None] * v['li'] + [q]
        rec[name] = {'label': pc['t'], 'old_x': v['old'], 'quads': X.set_quads(d, obs[name], ql, TW, TH, rest='keep'),
                     'gap_texels_after_prev_word': round((col - v['prev_end']) / v['sx'], 1)}
    X.check_pmf(d0, bytes(d), list(rows))
    open('%s/2_10.bin' % S3, 'wb').write(bytes(d))
    LOG['2_10_pmf'] = {'column_raw_x': round(col), 'objects': rec}

def fix_125():
    f = '125_1'; data, pics = F.load(f); p = pics[0]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    R = [((237, 1, 296, 16), 'Player/', 13), ((313, 2, 399, 17), 'Mobile Suit', 13), ((405, 2, 468, 17), 'Pilot', 13),
         ((476, 2, 499, 14), 'Play', None), ((237, 20, 281, 35), 'Team', 13), ((286, 21, 329, 35), 'Level', 13)]
    for (x0, y0, x1, y1), t, s in R: cv[y0:y1 + 1, x0:x1 + 1] = 0
    for box, t, s in R:
        engine.draw_text(cv, box, t, fname='rc', size=s, ss=4, maxsize=13)
    F.commit('r3_125', f, data, pics, 0, cv, before, 'header words in Roboto Condensed Bold 13 (Play fitted)')
    save_gim(f, data, pics); prev(f, 0, (230, 0, 512, 40), 'header', 2)

def fix_1609():
    f = '1609_1'; data, pics = F.load(f); p = pics[0]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    cv[48:64, 6:35] = 0
    w = X.wplain('OK', 'rc', 12, 4)
    x = 6 + (29 - w) // 2
    F.place(cv, x, 49 + 11, 'OK', 'rc', 12, ss=4)
    F.commit('r3_1609', f, data, pics, 0, cv, before, 'standalone OK in rc12 like the rest of the texture')
    save_gim(f, data, pics); prev(f, 0, (0, 44, 128, 66), 'ok')

def build():
    fx, ents, _ = afs.read(ppaths.BASE_XDATA)
    rep = {}
    for pth in sorted(glob.glob(S3 + '/*.bin')):
        a, s = os.path.basename(pth)[:-4].split('_', 1); rep.setdefault(int(a), {})[int(s)] = open(pth, 'rb').read()
    rpt = {}
    for i, subs in sorted(rep.items()):
        base_p = '%s/afs_out/afs_%d.bin' % (W, i)
        if os.path.exists(base_p): old = open(base_p, 'rb').read(); base = 'afs_out'
        else: fx.seek(ents[i][0]); old = fx.read(ents[i][1]); base = 'X_DATA_v042'
        new = repack.rebuild_pack(old, subs)
        so, _ = pack.parse(old); sn, _ = pack.parse(new)
        assert len(so) == len(sn)
        for j, (x, y) in enumerate(zip(so, sn)):
            if j in subs:
                got = lz.decompress(y['raw']) if y['flags'] & 1 else y['raw'][:len(subs[j])]
                assert got == subs[j] and y['flags'] == x['flags'], (i, j)
            else:
                assert x['raw'] == y['raw'] and x['entry'] == y['entry'], (i, j)
        open('%s/afs_%d.bin' % (A3, i), 'wb').write(new)
        rpt[i] = {'base': base, 'subs': sorted(subs), 'old_size': len(old), 'new_size': len(new), 'delta': len(new) - len(old)}
    return rpt

if __name__ == '__main__' and 'banner' not in sys.argv:
    fix_2_11(); fix_125(); fix_1609()
    LOG['build'] = build()
    LOG['quant'] = F.LOG
    json.dump(LOG, open(W + '/r3_report.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(LOG['build'], indent=0)); print(json.dumps(LOG['2_10_pmf'], indent=0)[:1500])

def fix_2_15():
    """2_15 pic0 (Arcade phase banner pieces, vertical text). JP pieces: teki-butai / senkan (targets) + wo-gekiha-seyo!
    (order), teki-taagetto (target) + wo-zenmetsu-sasero! (order), teki-mobiru-suutsu (target). The game shows target + order side by
    side, so targets now end with a colon and sit at the end of their rect, orders start at the beginning of theirs:
    ENEMIES: / SHIPS: / ENEMY TARGETS: / ENEMY MOBILE SUITS:  +  DESTROY ALL! / WIPE THEM OUT!
    Same face/size/colour as v0.4.2 (Roboto Condensed Bold 15, 250 grey-white, rotated 270), no squeeze needed."""
    f = '2_15'; data, pics = F.load(f); p = pics[0]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    R = [((181, 105, 204, 173), 'ENEMIES:', 'right', (181, 104, 204, 175)),
         ((181, 176, 204, 224), 'SHIPS:', 'right', (181, 175, 204, 224)),
         ((156, 106, 179, 224), 'DESTROY ALL!', 'left', (156, 106, 179, 224)),
         ((131, 106, 154, 224), 'ENEMY TARGETS:', 'right', (131, 106, 154, 224)),
         ((106, 106, 130, 238), 'WIPE THEM OUT!', 'left', (106, 106, 130, 238)),
         ((82, 104, 105, 254), 'ENEMY MOBILE SUITS:', 'right', (82, 104, 105, 254))]
    for _, t, al, (x0, y0, x1, y1) in R: cv[y0:y1, x0:x1] = 0
    sq = {}
    for box, t, al, _ in R:
        w = X.wplain(t, 'rc', 15, 4); L = box[3] - box[1]
        assert w <= L - 2, (t, w, L)
        engine.draw_text(cv, box, t, color=(250, 250, 250), fname='rc', size=15, ss=4, rotate=270, align=al, min_squeeze=1.0)
    F.commit('r3_2_15', f, data, pics, 0, cv, before, 'phase banner pieces: target-with-colon + order')
    save_gim(f, data, pics); prev(f, 0, (78, 100, 210, 256), 'banner', 3)

if __name__ == '__main__' and 'banner' in sys.argv:
    fix_2_15()
    rep = json.load(open(W + '/r3_report.json'))
    rep['build'] = build(); rep['quant']['r3_2_15'] = F.LOG['r3_2_15']
    json.dump(rep, open(W + '/r3_report.json', 'w'), indent=1, ensure_ascii=False)
    print(rep['build'])
