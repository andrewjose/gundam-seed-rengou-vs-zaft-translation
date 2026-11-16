#!/usr/bin/env python3
"""v0.4.4 image polish, round 2. Built on v0.4.2 sub-files (out/) or round-1 subs (subs/) where round 1 already
changed the file. Writes subs/<afs>_<sub>.bin (decompressed GIM or PMF2), previews/, appends to fixes_log.json.

KEY FINDING (round 2): the menu/lobby/help "messages" are NOT assembled by EBOOT code from piece IDs. Each message is
its own object in the screen's PMF2 layout model (sub 0 of the same AFS entry): a GE display list of textured quads
(vtype 0x102: u16 u, u16 v, s16 x, s16 y, s16 z; prim 4 = triangle strip of 4 verts per quad). The texture index is
the u32 at object+0x74 (0 = sub-1 pic0, 1 = pic1, ...). UV is normalised: u16 = texel * 32768 / texture_width.
So the Japanese word order lives in the PMF2 quads' xy positions, and the fix is a data edit:
- redraw whole English phrases into free texture space,
- rewrite the message object's quads in place (same prim count, same byte length) to point at the new pieces in
  English order; unused quads become zero-area (all 4 verts identical -> nothing rasterised).
No EBOOT change is needed.

Usage: fixes2.py [name ...]   (default: all)"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import ppaths  # repo tool paths + work folders (see ppaths.py)
import sys, os, json, struct, numpy as np, cv2
from PIL import Image
import gimcodec, engine, pmf
import fixes as F                                   # round-1 helpers: load/place/fit_sq/baseline_of/commit/finish
W = F.W; OUT = F.OUT; SUBS = W + '/subs'
F.LOG.clear()
PLOG = {}

def wplain(text, fn, sz, ss):
    return engine.render_line(text, fn, sz, 1.0, 0, ss)[0].shape[1]

def gap(t1, t2, fn, sz, ss):
    """ink gap between two words as the font sets them in one line"""
    return wplain(t1 + ' ' + t2, fn, sz, ss) - wplain(t1, fn, sz, ss) - wplain(t2, fn, sz, ss)

# ---------------------------------------------------------------- PMF2 quad editing
def pmf_objs(d):
    out = {}
    for o in pmf.objects(d):
        try: ob = pmf.parse_obj(d, o)
        except Exception: continue
        ob['tex'], = struct.unpack_from('<I', d, o + 0x74)
        out[ob['name']] = ob
    return out

def obj_quads(ob):
    i = 0; res = []
    for t, n in ob['prims']:
        res.append((i, n)); i += n
    return res

def obj_scale(ob, TW, TH):
    """raw xy units per texel, from the object's widest original quad"""
    best = None
    for i, n in obj_quads(ob):
        vv = ob['verts'][i:i + n]
        du = (max(v[0] for v in vv) - min(v[0] for v in vv)) * TW / 32768
        dv = (max(v[1] for v in vv) - min(v[1] for v in vv)) * TH / 32768
        dx = max(v[2] for v in vv) - min(v[2] for v in vv); dy = max(v[3] for v in vv) - min(v[3] for v in vv)
        if du > 4 and dv > 4 and (best is None or du > best[0]): best = (du, dx / du, dy / dv)
    return best[1], best[2]

def set_quads(d, ob, quads, TW, TH, rest='zero'):
    """quads: list of dict(tx, ty, tw, th [texels; quad covers u tx+.5..tx+tw+.5], X [raw left], Yt [raw top], sx, sy).
    Rewrites the object's prims in order; surplus prims become zero-area. Byte length unchanged."""
    qs = obj_quads(ob)
    assert len(quads) <= len(qs), (ob['name'], len(quads), len(qs))
    vs = ob['vsize']; csz = vs - 10                      # 0 (vtype 0x102) or 2 (0x11a: 16-bit colour, kept as is)
    rec = []
    for k, (i, n) in enumerate(qs):
        vv = ob['verts'][i:i + n]
        if k >= len(quads) and rest == 'keep':
            rec.append({'q': k, 'unchanged': True}); continue
        if k < len(quads) and quads[k] is None:
            rec.append({'q': k, 'unchanged': True}); continue
        if k < len(quads):
            assert n == 4, (ob['name'], k, n)
            q = quads[k]
            xL = int(round(q['X'])); xR = int(round(q['X'] + q['tw'] * q['sx']))
            yT = int(round(q['Yt'])); yB = int(round(q['Yt'] - q['th'] * q['sy']))
            u0 = int(round((q['tx'] + .5) * 32768 / TW)); u1 = int(round((q['tx'] + q['tw'] + .5) * 32768 / TW))
            v0 = int(round((q['ty'] + .5) * 32768 / TH)); v1 = int(round((q['ty'] + q['th'] + .5) * 32768 / TH))
            mx = (min(v[2] for v in vv) + max(v[2] for v in vv)) / 2; my = (min(v[3] for v in vv) + max(v[3] for v in vv)) / 2
            new = []
            for (u, v, x, y, z) in vv:
                L = x < mx; T = y > my
                new.append((u0 if L else u1, v0 if T else v1, xL if L else xR, yT if T else yB, z))
            rec.append({'q': k, 'uv': [q['tx'], q['ty'], q['tw'], q['th']], 'x': [xL, xR], 'y': [yB, yT]})
        else:
            f = new[0]
            new = [f] * n
            rec.append({'q': k, 'zero_area': True})
        for j, v in enumerate(new):
            struct.pack_into('<HH', d, ob['vaddr'] + vs * (i + j), v[0], v[1])
            struct.pack_into('<hhh', d, ob['vaddr'] + vs * (i + j) + 4 + csz, v[2], v[3], v[4])
    return rec

def check_pmf(old, new, changed_objs):
    """same length, identical outside the changed objects' vertex data, all objects still parse"""
    assert len(old) == len(new)
    oo = pmf_objs(old); no = pmf_objs(new)
    assert sorted(oo) == sorted(no)
    diff = np.nonzero(np.frombuffer(old, np.uint8) != np.frombuffer(new, np.uint8))[0]
    allowed = np.zeros(len(old), bool)
    for n in changed_objs:
        ob = oo[n]; nv = sum(c for _, c in ob['prims'])
        allowed[ob['vaddr']:ob['vaddr'] + ob['vsize'] * nv] = True
    assert allowed[diff].all(), 'PMF bytes changed outside the edited vertex arrays'
    return len(diff)

def layout(pieces, order, gapf, sx, start_px_screen=None, center=None, left=None, margin=1, outline=0):
    """pieces: name -> dict(x (plain ink left in texture), w (plain width)); order: list of names left->right.
    Returns list of (name, quad_left_raw). Quad = [x-margin-outline, x+w+margin+outline)."""
    m = margin + outline
    tot = 0; pos = []
    for k, n in enumerate(order):
        pos.append(tot)                                           # plain-ink left, in texels from line start
        tot += pieces[n]['w'] + (gapf(order[k], order[k + 1]) if k + 1 < len(order) else 0)
    if center is not None: base = center - tot * sx / 2
    else: base = left + m * sx
    return [(n, base + (p - m) * sx) for n, p in zip(order, pos)]

def quad_of(piece, Xraw, Yt, th, sx, sy, ty, margin=1, outline=0):
    m = margin + outline
    return dict(tx=piece['x'] - m, ty=ty, tw=piece['w'] + 2 * m, th=th, X=Xraw, Yt=Yt, sx=sx, sy=sy)

def clear(cv, rects):
    for x0, y0, x1, y1 in rects: cv[y0:y1, x0:x1] = 0

def save_pmf(f, new, note):
    open('%s/%s.bin' % (SUBS, f), 'wb').write(bytes(new))

def preview_rows(f, k, tag, box, src_new=SUBS, scale=3):
    a = gimcodec.decode(open('%s/%s.bin' % (OUT, f), 'rb').read())[k]
    b = gimcodec.decode(open('%s/%s.bin' % (src_new, f), 'rb').read())[k]
    ims = []
    for p in (a, b):
        im = Image.fromarray(p.pal[p.idx], 'RGBA').crop(box)
        bg = Image.new('RGBA', im.size, (24, 24, 96, 255)); bg.alpha_composite(im)
        ims.append(bg.convert('RGB').resize((im.width * scale, im.height * scale), Image.NEAREST))
    S = Image.new('RGB', (ims[0].width, ims[0].height * 2 + 6), (255, 0, 255))
    S.paste(ims[0], (0, 0)); S.paste(ims[1], (0, ims[0].height + 6))
    S.save('%s/previews/%s_%d_%s.png' % (W, f, k, tag))

def render_messages(f, k, msgs, tex_name=None):
    """simulate what each edited PMF object draws (texel-accurate, 1 texel = 1 px): previews/<f>_<k>_msg_<obj>.png"""
    pic = gimcodec.decode(open('%s/%s.bin' % (SUBS, f), 'rb').read())[k]
    rgba = pic.pal[pic.idx]; TH, TW = rgba.shape[:2]
    a = f.split('_')[0]
    d = open('%s/%s_0.bin' % (SUBS, a), 'rb').read()
    obs = pmf_objs(d)
    rows = []
    for name in msgs:
        ob = obs[name]; sx, sy = obj_scale(ob, TW, TH)
        quads = []
        for i, n in obj_quads(ob):
            vv = ob['verts'][i:i + n]
            xs = [v[2] for v in vv]; ys = [v[3] for v in vv]
            if max(xs) == min(xs) or max(ys) == min(ys): continue
            us = [v[0] * TW / 32768 for v in vv]; vs_ = [v[1] * TH / 32768 for v in vv]
            quads.append((min(xs), max(ys), min(us), min(vs_), max(us), max(vs_)))
        x0 = min(q[0] for q in quads); y0 = max(q[1] for q in quads)
        canvas = Image.new('RGBA', (420, 24), (24, 24, 96, 255))
        for X, Y, u0, v0, u1, v1 in quads:
            crop = Image.fromarray(rgba[int(v0):int(round(v1)), int(u0):int(round(u1))], 'RGBA')
            canvas.alpha_composite(crop, (int(round((X - x0) / sx)) + 2, int(round((y0 - Y) / sy)) + 2))
        rows.append(canvas.resize((900, 72), Image.NEAREST))
    S = Image.new('RGB', (1260, 74 * len(rows)), (255, 0, 255))
    for i, r in enumerate(rows): S.paste(r.convert('RGB'), (0, 74 * i))
    S.save('%s/previews/%s_%d_messages.png' % (W, f, k))

# ---------------------------------------------------------------- 129: Ad Hoc lobby messages
def fix_129():
    """AFS 129 (Ad Hoc lobby). sub 0 = PMF2 'lobby_lXX', sub 1 pic1 = message texture (256x256).
    JP messages and their pieces (texel rects), as found in the PMF2:
      l1a tsuushin|taisen-wo|shuuryou|shitemo-yoroshii-desu-ka?      -> End the link battle?
      l1b tsuushin|kyouryoku|sen-wo|shuuryou|shitemo-yoroshii-desu-ka?    -> End the co-op battle?
      l1c kono-menbaa-de|taisen-wo|kaishi|shitemo-yoroshii-desu-ka? -> Start the battle with these members?
      l26 kono-menbaa-de|kyouryoku|sen-wo|kaishi|shitemo-yoroshii-desu-ka? -> Start co-op play with these members?
      l1d heya-wo|kaisan|shitemo-yoroshii-desu-ka?             -> Disband the room?
      l1e heya|ga|kaisan|saremashita                       -> The room was disbanded.
      l1f 2-4nin|chiimu-taisen:|sanka-suru-heya-wo-erande-kudasai -> Team Battle (2-4 players): Choose a room to join
      l20 2|nin|kyouryoku-aakeedo-moodo:|sanka-suru-heya-wo…    -> Co-op Arcade (2 players): Choose a room to join
    (v0.4.2 showed l1f as '2-4 players Team Battle: Choose a room to join' and l20 as '2' + 'rs' + 'Co-op Arcade:' ...)
    New pieces: Roboto Condensed Bold 16 (same face/size as the lobby labels in pic0), colour 250, 1 px black
    outline, 4x supersampled; 18-texel slots, baseline at slot top + 13."""
    f = '129_1'; data, pics = F.load(f); k = 1; p = pics[k]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    FN, SZ, SS = 'rc', 16, 4
    clear(cv, [(0, 104, 237, 124), (0, 124, 97, 146), (0, 146, 237, 182), (0, 182, 216, 218), (0, 218, 220, 230),
               (96, 230, 220, 256), (220, 235, 256, 256)])
    # (text, slot top, plain-ink left x)
    P = {'h': ('Team Battle (2-4 players):', 105, 2), 'Start': ('Start', 105, 174),
         'cob': ('co-op battle?', 124, 2),
         'i': ('Co-op Arcade (2 players):', 146, 2), 'tb': ('the battle', 146, 171),
         'j': ('Choose a room to join', 164, 2), 'cop': ('co-op play', 164, 146),
         'g': ('The room was disbanded.', 182, 2),
         'e': ('with these members?', 200, 2), 'Et': ('End the', 200, 144),
         'f': ('Disband the room?', 219, 99),
         'a': ('End the link battle?', 238, 100)}
    slots = {105: 237, 124: 97, 146: 237, 164: 237, 182: 216, 200: 216, 219: 220, 238: 256}
    pieces = {}
    for n, (t, top, x) in P.items():
        w = F.place(cv, x, top + 13, t, FN, SZ, color=(250, 250, 250), outline=(0, 0, 0), ss=SS)
        assert x - 2 >= (96 if top >= 219 else 0) and x + w + 2 <= slots[top], (t, x, w, slots[top])
        pieces[n] = {'x': x, 'w': w, 'y': top, 't': t}
    # texture-level overlap check between pieces on the same row (quad rects incl. 1px margin + outline)
    for r in set(v['y'] for v in pieces.values()):
        rr = sorted((v['x'] - 2, v['x'] + v['w'] + 2) for v in pieces.values() if v['y'] == r)
        for (a0, a1), (b0, b1) in zip(rr, rr[1:]): assert a1 <= b0, (r, rr)
    commit('129_lobby', f, data, pics, k, cv, before, 'Ad Hoc lobby messages: whole English phrases, rc16 + outline')
    F.finish(f, data, pics, 'fix'); preview_rows(f, k, 'lobby', (0, 100, 256, 256))
    # PMF2
    d0 = open('%s/129_0.bin' % OUT, 'rb').read(); d = bytearray(d0); obs = pmf_objs(d0)
    TW, TH = 256, 256
    msgs = {'lobby_l1a': ['a'], 'lobby_l1b': ['Et', 'cob'], 'lobby_l1c': ['Start', 'tb', 'e'],
            'lobby_l26': ['Start', 'cop', 'e'], 'lobby_l1d': ['f'], 'lobby_l1e': ['g'],
            'lobby_l1f': ['h', 'j'], 'lobby_l20': ['i', 'j']}
    texts = {'lobby_l1a': 'End the link battle?', 'lobby_l1b': 'End the co-op battle?',
             'lobby_l1c': 'Start the battle with these members?', 'lobby_l26': 'Start co-op play with these members?',
             'lobby_l1d': 'Disband the room?', 'lobby_l1e': 'The room was disbanded.',
             'lobby_l1f': 'Team Battle (2-4 players): Choose a room to join',
             'lobby_l20': 'Co-op Arcade (2 players): Choose a room to join'}
    log = PLOG.setdefault('129', {'scale': {}, 'objects': {}})
    gf = lambda a, b: gap(pieces[a]['t'].split()[-1], pieces[b]['t'].split()[0], FN, SZ, SS)
    for name, order in msgs.items():
        ob = obs[name]; assert ob['tex'] == 1
        sx, sy = obj_scale(ob, TW, TH); log['scale'][name] = (sx, sy)
        xs = [v[2] for v in ob['verts']]; ys = [v[3] for v in ob['verts']]
        c = (min(xs) + max(xs)) / 2; Yt = max(ys)
        lay = layout(pieces, order, gf, sx, center=c, outline=1)
        qs = [quad_of(pieces[n], X, Yt, 18, sx, sy, pieces[n]['y'], outline=1) for n, X in lay]
        log['objects'][name] = {'en': texts[name], 'pieces': [pieces[n]['t'] for n in order],
                                'quads': set_quads(d, ob, qs, TW, TH)}
    nd = check_pmf(d0, bytes(d), list(msgs))
    log['bytes_changed'] = int(nd)
    save_pmf('129_0', d, '')
    render_messages(f, k, list(msgs))

def commit(name, f, data, pics, k, cv, before, note):
    return F.commit(name, f, data, pics, k, cv, before, note)

# ---------------------------------------------------------------- 124: VS lobby / menu prompts
def fix_124():
    """AFS 124 (VS settings / link lobby). sub 0 = PMF2 'selvs01_kXX', sub 1 pic0 = texture.
      k60 menyuu-gamen|ni-modottemo-yoroshii-desu-ka|(full-width ?) -> 'Return to the Main Menu?'  (v0.4.2: 'Main Menu — return there? Are you sure?')
      k61 robii|gamen|ni-modottemo-yoroshii-desu-ka?   -> 'Return to the lobby?'      (v0.4.2: 'Lobby Menu — return there? Are you sure?')
      k63 tsuushin-taisen-wo|shuuryou-shimasu|ka?              -> 'End the link battle?'      (v0.4.2: 'Ending the link battle. sure?')
      k62 shutsugeki-fukanou:|chiimu-ga-hitotsu-shika-arimasen -> "Can't launch: There is only one team." (JP full-width colon gap fixed)
      k64 tsuushin-taisen-wo|shuuryou-shimasu -> 'Ending the link battle.' (unchanged)
    Pieces in DejaVu Sans Bold 12 hinted, white, like the other v0.4.2 lines of this texture; baseline = row top + 13 (same as 'There is only one team.')."""
    f = '124_1'; data, pics = F.load(f); k = 0; p = pics[k]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    FN, SZ, SS = 'sans', 12, 1
    clear(cv, [(0, 126, 97, 146), (0, 146, 243, 166), (109, 166, 200, 186)])
    P = {'rt': ('Return to the', 126, 2), 'mm': ('Main Menu?', 146, 2), 'end': ('End the link battle?', 146, 88),
         'lob': ('lobby?', 237, 197), 'cl': ("Can't launch:", 166, 111)}
    lim = {'rt': (0, 97), 'mm': (0, 243), 'end': (0, 243), 'lob': (194, 256), 'cl': (109, 200)}
    pieces = {}
    for n, (t, top, x) in P.items():
        w = F.place(cv, x, top + 13, t, FN, SZ, ss=SS)
        assert x - 1 >= lim[n][0] and x + w + 1 <= lim[n][1], (t, x, w)
        pieces[n] = {'x': x, 'w': w, 'y': top, 't': t}
    assert pieces['mm']['x'] + pieces['mm']['w'] + 1 <= pieces['end']['x'] - 1
    commit('124_prompts', f, data, pics, k, cv, before, 'menu/lobby prompts as whole English phrases; "Can\'t launch:" colon')
    F.finish(f, data, pics, 'fix'); preview_rows(f, k, 'prompts', (0, 100, 256, 256))
    d0 = open('%s/124_0.bin' % OUT, 'rb').read(); d = bytearray(d0); obs = pmf_objs(d0)
    TW, TH = 256, 256
    gf = lambda a, b: gap(pieces[a]['t'].split()[-1], pieces[b]['t'].split()[0], FN, SZ, SS)
    log = PLOG.setdefault('124', {'scale': {}, 'objects': {}})
    msgs = {'selvs01_k60': (['rt', 'mm'], 'Return to the Main Menu?'),
            'selvs01_k61': (['rt', 'lob'], 'Return to the lobby?'),
            'selvs01_k63': (['end'], 'End the link battle?')}
    for name, (order, en) in msgs.items():
        ob = obs[name]; assert ob['tex'] == 0
        sx, sy = obj_scale(ob, TW, TH); log['scale'][name] = (sx, sy)
        xs = [v[2] for v in ob['verts']]; ys = [v[3] for v in ob['verts']]
        c = (min(xs) + max(xs)) / 2; Yt = max(ys)
        lay = layout(pieces, order, gf, sx, center=c)
        qs = [quad_of(pieces[n], X, Yt, 18, sx, sy, pieces[n]['y']) for n, X in lay]
        log['objects'][name] = {'en': en, 'pieces': [pieces[n]['t'] for n in order], 'quads': set_quads(d, ob, qs, TW, TH)}
    # k62: keep q0 ('There is only one team.', unchanged) and re-seat q1 on the new "Can't launch:" piece
    ob = obs['selvs01_k62']; sx, sy = obj_scale(ob, TW, TH); log['scale']['selvs01_k62'] = (sx, sy)
    qq = obj_quads(ob); i0, _ = qq[0]; v0 = ob['verts'][i0:i0 + 4]
    q0 = dict(tx=min(v[0] for v in v0) * TW / 32768 - .5, ty=min(v[1] for v in v0) * TH / 32768 - .5,
              tw=(max(v[0] for v in v0) - min(v[0] for v in v0)) * TW / 32768,
              th=(max(v[1] for v in v0) - min(v[1] for v in v0)) * TH / 32768,
              X=min(v[2] for v in v0), Yt=max(v[3] for v in v0), sx=sx, sy=sy)
    one_ink = 1                                         # 'There is only one team.' ink starts at texel x=1
    inkL = q0['X'] + (one_ink - (q0['tx'] + .5)) * sx
    g = gap("launch:", 'There', FN, SZ, SS)
    cl = pieces['cl']
    X1 = inkL - g * sx - cl['w'] * sx - 1 * sx
    q1 = quad_of(cl, X1, q0['Yt'], 19, sx, sy, 166)
    rec = set_quads(d, ob, [None, q1], TW, TH)
    
    log['objects']['selvs01_k62'] = {'en': "Can't launch: There is only one team.", 'pieces': ["Can't launch:", '(unchanged) There is only one team.'], 'quads': rec}
    nd = check_pmf(d0, bytes(d), list(msgs) + ['selvs01_k62'])
    log['bytes_changed'] = int(nd)
    save_pmf('124_0', d, '')
    render_messages(f, k, list(msgs) + ['selvs01_k62', 'selvs01_k64'])

# ---------------------------------------------------------------- 11 / 130 / 133: help pieces in the 2_0 style
HELP = dict(fn='rc', sz=12, shadow=(0, 0, 0, 170))

def help_piece(cv, x, y, w, h, t):
    """2_0 style (round 1): Roboto Condensed Bold 12, 4x ss, white + soft dark shadow, left-aligned at x+1,
    cap block vertically centred, squeeze only if the rect forces it (>= 0.8)."""
    cap = F.baseline_of(HELP['fn'], HELP['sz'])
    sq, iw = F.fit_sq(t, HELP['fn'], HELP['sz'], w - 2)
    F.place(cv, x + 1, y + (h + cap) // 2, t, HELP['fn'], HELP['sz'], shadow=HELP['shadow'], squeeze=sq)
    return round(sq, 2)

def fix_11():
    """AFS 11 (link-battle waiting screen). sub 1 pic1.
    Help bars (PMF2 sel11_k7a..k7d): words were DejaVu 10/11, mixed sizes -> 2_0 style. 'Select' slot widened
    0-27 -> 0-30 in texture and on screen (k7b/k7c/k7d q3; the on-screen gap to the next icon allows it).
    Status line k70 was shutsugeki|no-junbi-wo-shiteimasu shown as 'Launch' + 'stage select...' (piece 103-255 shared with k71)
    -> now 'Preparing' + 'to launch...'; k71 'Preparing' + 'stage select...'. DejaVu Sans Bold 12 hinted like the
    other status lines, all three pieces in row 190."""
    f = '11_1'; data, pics = F.load(f); k = 1; p = pics[k]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    # help words
    clear(cv, [(86, 220, 168, 237), (0, 238, 31, 255), (48, 238, 76, 255), (96, 238, 199, 255)])
    sq = {}
    for x, y, w, h, t in ((86, 220, 27, 16, 'Move'), (114, 220, 26, 16, 'Enter'), (141, 220, 26, 16, 'Back'),
                          (0, 238, 30, 16, 'Select'), (48, 238, 27, 16, 'OK'), (96, 238, 102, 16, 'Back to menu')):
        sq[t] = help_piece(cv, x, y, w, h, t)
    # status pieces
    clear(cv, [(192, 170, 256, 190), (0, 190, 256, 210)])
    FN, SZ, SS = 'sans', 12, 1
    P = {'prep': ('Preparing', 190, 1), 'ss': ('stage select...', 190, 69), 'tl': ('to launch...', 190, 167)}
    pieces = {}
    for n, (t, top, x) in P.items():
        w = F.place(cv, x, top + 13, t, FN, SZ, ss=SS)
        pieces[n] = {'x': x, 'w': w, 'y': top, 't': t}
    rr = sorted((v['x'] - 1, v['x'] + v['w'] + 1) for v in pieces.values())
    for (a0, a1), (b0, b1) in zip(rr, rr[1:]): assert a1 <= b0, rr
    assert rr[-1][1] <= 256 and rr[0][0] >= 0
    commit('11_help', f, data, pics, k, cv, before, 'help words 2_0 style ' + json.dumps(sq) + '; status pieces Preparing/stage select.../to launch...')
    F.finish(f, data, pics, 'fix'); preview_rows(f, k, 'help_status', (0, 145, 256, 256))
    d0 = open('%s/11_0.bin' % OUT, 'rb').read(); d = bytearray(d0); obs = pmf_objs(d0)
    TW, TH = 256, 256
    log = PLOG.setdefault('11', {'scale': {}, 'objects': {}})
    gf = lambda a, b: gap(pieces[a]['t'].split()[-1], pieces[b]['t'].split()[0], FN, SZ, SS)
    for name, order, en in (('sel11_k70', ['prep', 'tl'], 'Preparing to launch...'),
                            ('sel11_k71', ['prep', 'ss'], 'Preparing stage select...')):
        ob = obs[name]; assert ob['tex'] == 1
        qq = obj_quads(ob)
        # q0 = 'Please wait...' line (unchanged); q1,q2 = the second line
        i0, _ = qq[0]; v0 = ob['verts'][i0:i0 + 4]
        q0 = dict(tx=min(v[0] for v in v0) * TW / 32768 - .5, ty=min(v[1] for v in v0) * TH / 32768 - .5,
                  tw=(max(v[0] for v in v0) - min(v[0] for v in v0)) * TW / 32768,
                  th=(max(v[1] for v in v0) - min(v[1] for v in v0)) * TH / 32768,
                  X=min(v[2] for v in v0), Yt=max(v[3] for v in v0))
        sx, sy = obj_scale(ob, TW, TH); q0['sx'] = sx; q0['sy'] = sy; log['scale'][name] = (sx, sy)
        line2 = [ob['verts'][i:i + 4] for i, n in qq[1:]]
        L = min(v[2] for vv in line2 for v in vv); Yt = max(v[3] for vv in line2 for v in vv)
        lay = layout(pieces, order, gf, sx, left=L)
        qs = [None] + [quad_of(pieces[n], X, Yt, 19, sx, sy, 190) for n, X in lay]
        log['objects'][name] = {'en': en, 'pieces': ['(unchanged) Please wait...'] + [pieces[n]['t'] for n in order],
                                'quads': set_quads(d, ob, qs, TW, TH)}
        assert d[ob['vaddr']:ob['vaddr'] + 40] == d0[ob['vaddr']:ob['vaddr'] + 40], name + ' q0 changed'
    # widen 'Select' quads (uv 0.5-27.5 -> 0.5-30.5) in k7b/k7c/k7d
    wid = []
    for name in ('sel11_k7b', 'sel11_k7c', 'sel11_k7d'):
        ob = obs[name]
        for qi, (i, n) in enumerate(obj_quads(ob)):
            vv = ob['verts'][i:i + n]
            if min(v[0] for v in vv) == 64 and max(v[0] for v in vv) == 3520 and min(v[1] for v in vv) == 30528:
                sxq = (max(v[2] for v in vv) - min(v[2] for v in vv)) / 27
                xL = min(v[2] for v in vv); xR = int(round(xL + 30 * sxq))
                # next element on screen must still start right of the widened quad
                others = [min(w[2] for w in ob['verts'][j:j + m]) for j, m in obj_quads(ob) if j != i]
                nxt = min(o for o in others if o > xL)
                assert xR < nxt, (name, xR, nxt)
                for j, (u, v, x, y, z) in enumerate(vv):
                    if u == 3520:
                        struct.pack_into('<HHhhh', d, ob['vaddr'] + 10 * (i + j), 3904, v, xR, y, z)
                wid.append({'obj': name, 'q': qi, 'x_right': [max(v[2] for v in vv), xR], 'next_on_screen': nxt})
    log['select_widened'] = wid
    assert len(wid) == 3
    nd = check_pmf(d0, bytes(d), ['sel11_k70', 'sel11_k71', 'sel11_k7b', 'sel11_k7c', 'sel11_k7d'])
    log['bytes_changed'] = int(nd)
    save_pmf('11_0', d, '')
    render_messages(f, k, ['sel11_k70', 'sel11_k71', 'sel11_k7a', 'sel11_k7b', 'sel11_k7c'])

def fix_130():
    """AFS 130 pic0 (soft keyboard texture; copy of the 11_1 pic1 layout). Its own PMF2 (softkbd) does not reference
    the help rows, so only the help words are restyled in place (same rects as 11, 'Select' not widened)."""
    f = '130_1'; data, pics = F.load(f); k = 0; p = pics[k]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    clear(cv, [(0, 238, 28, 255), (48, 238, 76, 255), (96, 238, 199, 255)])
    sq = {}
    for x, y, w, h, t in ((0, 238, 27, 16, 'Select'), (48, 238, 27, 16, 'OK'), (96, 238, 102, 16, 'Back to menu')):
        sq[t] = help_piece(cv, x, y, w, h, t)
    commit('130_help', f, data, pics, k, cv, before, 'help words 2_0 style ' + json.dumps(sq))
    F.finish(f, data, pics, 'fix'); preview_rows(f, k, 'help', (0, 210, 256, 256))

def fix_133():
    """AFS 133 (level/affiliation select). pic6 help words (PMF2 selmi02_si14/si24: Select 164-194, OK 195-225,
    Back 226-255 at rows 24-41; si32 Next 222-252 at rows 64-81) -> 2_0 style. pic8 (round 1, rc13) redone in rc12
    so both help rows of this screen match the title-screen help bar."""
    f = '133_1'; data, pics = F.load(f)
    k = 6; p = pics[k]; cv = gimcodec.rgba(p).copy(); before = cv.copy()
    clear(cv, [(164, 24, 256, 42), (222, 64, 256, 82)])
    sq = {}
    for x, y, w, h, t in ((164, 24, 30, 18, 'Select'), (195, 24, 30, 18, 'OK'), (226, 24, 29, 18, 'Back'),
                          (222, 64, 30, 18, 'Next')):
        sq[t] = help_piece(cv, x, y, w, h, t)
    commit('133_help', f, data, pics, k, cv, before, 'pic6 help words 2_0 style ' + json.dumps(sq))
    k = 8; p = pics[k]; cv = gimcodec.rgba(p).copy(); before = cv.copy()
    cv[79:102, 0:128] = 0
    sq8 = {}
    for i, t in enumerate(('Move', 'Enter', 'Back', 'OK')):
        sq8[t] = help_piece(cv, 32 * i, 80, 32, 20, t)
    commit('133_help', f, data, pics, k, cv, before, 'pic8 help row Move/Enter/Back/OK in rc12 (was rc13 in round 1) ' + json.dumps(sq8))
    F.finish(f, data, pics, 'fix')
    preview_rows(f, 6, 'help', (150, 18, 256, 86)); preview_rows(f, 8, 'helprow', (0, 76, 128, 104))

# ---------------------------------------------------------------- credits artist names
def fix_credits_names():
    """1684_raw pic3 (credits, built on round-1 subs/1684_raw.bin with the INVOKE quote fix):
    'T. M. Revolution' -> 'T.M.Revolution' (spaces after the periods closed to 2 px, right edge unchanged);
    'See—Saw' -> 'See-Saw' (12 px dash -> 5 px hyphen, 1 px gaps, right edge unchanged). Pixel moves only."""
    f = '1684_raw'; data, pics = F.load(f, SUBS); k = 3; p = pics[k]
    cv = gimcodec.rgba(p).copy(); before = cv.copy()
    y0, y1 = 92, 107
    A = cv[y0:y1, 93:107].copy(); B = cv[y0:y1, 112:127].copy()
    cv[y0:y1, 93:127] = 0
    bx = 132 - 2 - B.shape[1]; ax = bx - 2 - A.shape[1]
    cv[y0:y1, bx:bx + B.shape[1]] = B; cv[y0:y1, ax:ax + A.shape[1]] = A
    y0, y1 = 222, 237
    See = cv[y0:y1, 140:167].copy(); dash = cv[y0:y1, 170:175].copy()
    cv[y0:y1, 140:179] = 0
    cv[y0:y1, 173:178] = dash
    cv[y0:y1, 145:172] = See
    commit('credits_names', f, data, pics, k, cv, before, 'T.M.Revolution / See-Saw (pixel moves, right-aligned)')
    F.finish(f, data, pics, 'fix'); preview_rows(f, k, 'artists', (80, 85, 220, 240))

FIXES = {'129': fix_129, '124': fix_124, '11': fix_11, '130': fix_130, '133': fix_133, 'credits_names': fix_credits_names}
if __name__ == '__main__':
    names = sys.argv[1:] or list(FIXES)
    for n in names:
        FIXES[n](); print(n, 'ok')
    old = json.load(open(W + '/fixes_log.json')) if os.path.exists(W + '/fixes_log.json') else {}
    old.update(F.LOG); json.dump(old, open(W + '/fixes_log.json', 'w'), indent=1, ensure_ascii=False)
    pl = json.load(open(W + '/pmf_edits.json')) if os.path.exists(W + '/pmf_edits.json') else {}
    pl.update(PLOG); json.dump(pl, open(W + '/pmf_edits.json', 'w'), indent=1, ensure_ascii=False)
