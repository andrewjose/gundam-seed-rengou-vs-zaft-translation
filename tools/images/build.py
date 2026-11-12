#!/usr/bin/env python3
"""Apply specs/*.json to YOUR extracted GIM sub-files -> new GIMs (<work>/images/gim_new), before/after previews
(<work>/images/preview, local only, never commit them) and rebuilt AFS entries (<work>/afs_new/afs_<i>.bin).

Inputs: <work>/xd_out/<afs>_<sub>.bin from tools/xdata/unpack.py. Entries that the glyph builders already changed
(<work>/glyph/afs/afs_<i>.bin: label models, pilot-name sheets) are used as the base for those indices.
Each spec region = box (x0,y0,x1,y1 in texels), erase box/mode, English text and style; glyphs are rendered from
the fonts at build time and quantised into the picture's existing 256-colour palette.
usage: build.py [specs/a.json ...]   (no args: all specs + AFS entries)"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys, os, json, glob, struct, numpy as np
from PIL import Image
import gimcodec, engine, lz, pack, repack
import afs as afsmod

OUT = P.unpacked()
HERE = os.path.dirname(os.path.abspath(__file__))
WD = P.work('images')
for _d in ('gim_new', 'preview'): os.makedirs(os.path.join(WD, _d), exist_ok=True)
os.makedirs(P.afs_new(), exist_ok=True)
# Base AFS entries produced by the glyph builders (tools/glyph): edits are applied on top of these.
BASES = {}
for _i in [2, 11, 12, 124, 129, 130, 134, 135, 137, 138, 140]:
    _p = P.work('glyph', 'afs', 'afs_%d.bin' % _i)
    if os.path.exists(_p): BASES[_i] = _p

def load_sub(f):
    a, s = f.split('_', 1)
    a = int(a)
    if a in BASES and s != 'raw':
        subs, _ = pack.parse(open(BASES[a], 'rb').read())
        sb = subs[int(s)]
        return lz.decompress(sb['raw']) if sb['flags'] & 1 else sb['raw']
    return open('%s/%s.bin' % (OUT, f), 'rb').read()
DRAWKEYS = {'ss','color','fname','align','valign','outline','outline_w','shadow','shadow_off','mode','size','minsize','min_squeeze','tracking','yoff','xoff','maxsize','rotate'}

def tup(v): return tuple(v) if isinstance(v, list) else v

def auto_style(orig, box):
    x0, y0, x1, y1 = box
    reg = orig[y0:y1, x0:x1].reshape(-1, 4).astype(np.int32)
    op = reg[reg[:, 3] > 200]
    if len(op) < 4: return {'color': [255, 255, 255], 'outline': None}
    lum = op[:, :3].max(1)
    bright = op[lum >= np.percentile(lum, 70)]
    col = np.median(bright[:, :3], 0).astype(int).tolist()
    dark = op[lum < 90]
    outline = None
    # count outline only when the box background is transparent (opaque dark pixels = outline)
    trans = (reg[:, 3] < 30).mean()
    if trans > 0.15 and len(dark) > 0.12 * len(op):
        outline = np.median(dark[:, :3], 0).astype(int).tolist()
    return {'color': col, 'outline': outline}

def apply_pic(pic, spec):
    canvas = gimcodec.rgba(pic).copy(); orig = canvas.copy()
    dflt = spec.get('defaults', {})
    em = spec.get('erase', 'transparent')
    for r in spec['regions']:
        if r.get('keep'): continue
        st = auto_style(orig, r['box'])
        r.setdefault('color', dflt.get('color', st['color']))
        if 'outline' not in r and 'outline' not in dflt and st['outline'] is not None: r['outline'] = st['outline']
    for r in spec['regions']:
        if r.get('keep'): continue
        eb = r.get('erase_box', r['box'])
        if eb:
            mode = r.get('erase', em)
            ek = {k[6:]: tup(v) for k, v in {**dflt, **r}.items() if k.startswith('erase_') and k not in ('erase_box',)}
            engine.erase(canvas, eb, mode, **{k: v for k, v in ek.items()})
    for r in spec['regions']:
        if r.get('keep') or not r.get('en') or r.get('custom'): continue
        kw = {k: tup(v) for k, v in {**dflt, **r}.items() if k in DRAWKEYS}
        r['_fit'] = engine.draw_text(canvas, r.get('draw_box', r['box']), r['en'], **kw)
    for r in spec['regions']:
        if r.get('custom'):
            import custom_ops
            r['_fit'] = getattr(custom_ops, r['custom'])(canvas, orig, r, {**dflt, **r})
    changed = (canvas != orig).any(-1)
    err = engine.quantize(pic, canvas, changed)
    return orig, canvas, err

def preview(name, orig, new_rgba, out):
    def comp(a):
        im = Image.fromarray(a, 'RGBA'); bg = Image.new('RGBA', im.size, (20, 20, 90, 255)); bg.alpha_composite(im); return bg.convert('RGB')
    a, b = comp(orig), comp(new_rgba)
    sc = 2 if a.width <= 512 else 1
    W, H = a.width * sc, a.height * sc
    S = Image.new('RGB', (W * 2 + 8, H), (255, 0, 255))
    S.paste(a.resize((W, H), Image.NEAREST), (0, 0)); S.paste(b.resize((W, H), Image.NEAREST), (W + 8, 0))
    S.save(out)

def build_file(specfile):
    spec = json.load(open(specfile))
    f = spec['file']
    d = load_sub(f)
    pics = gimcodec.decode(d)
    log = []
    for k, ps in spec['pics'].items():
        p = pics[int(k)]
        orig, canvas, err = apply_pic(p, ps)
        preview('%s_%s' % (f, k), orig, gimcodec.rgba(p), os.path.join(WD, 'preview', '%s_%s.png' % (f, k)))
        log.append((k, err))
    nd = gimcodec.encode(d, pics)
    open(os.path.join(WD, 'gim_new', '%s.bin' % f), 'wb').write(nd)
    # verify decode
    chk = gimcodec.decode(nd)
    for k in spec['pics']:
        assert np.array_equal(chk[int(k)].idx, pics[int(k)].idx)
    return spec, log

def build_afs_entries(files):
    fobj, ents, _ = afsmod.read(repack.AFS_DEFAULT)
    by = {}
    for f in files:
        a, s = f.split('_', 1); by.setdefault(int(a), []).append(s)
    report = []
    order = sorted(range(len(ents)), key=lambda i: ents[i][0])
    for idx, subs in sorted(by.items()):
        off, size = ents[idx]
        if idx in BASES:
            orig = open(BASES[idx], 'rb').read(); base = BASES[idx]
        else:
            fobj.seek(off); orig = fobj.read(size); base = 'original X_DATA.BIN'
        if subs == ['raw']:
            new = open(os.path.join(WD, 'gim_new', '%d_raw.bin' % idx), 'rb').read()
        else:
            rep = {int(s): open(os.path.join(WD, 'gim_new', '%d_%s.bin' % (idx, s)), 'rb').read() for s in subs}
            new = repack.rebuild_pack(orig, rep)
            nxt0 = min([ents[i][0] for i in range(len(ents)) if ents[i][0] > off] or [os.path.getsize(repack.AFS_DEFAULT)])
            if len(new) > nxt0 - off:
                new = repack.rebuild_pack(orig, rep, compressor=lambda b: lz.compress_opt(b, tries=4096))
        open(P.afs_new(idx), 'wb').write(new)
        nxt = min([ents[i][0] for i in range(len(ents)) if ents[i][0] > off] or [os.path.getsize(repack.AFS_DEFAULT)])
        slot = nxt - off
        report.append({'afs': idx, 'orig_size': size, 'new_size': len(new), 'slot': slot, 'fits': len(new) <= slot, 'subs': subs, 'base': base})
    return report

if __name__ == '__main__':
    specs = sys.argv[1:] or sorted(glob.glob(os.path.join(HERE, 'specs', '*.json')))
    done = []; tl = {}
    for sf in specs:
        spec, log = build_file(sf)
        done.append(spec['file'])
        for k, ps in spec['pics'].items():
            tl['%s_%s' % (spec['file'], k)] = [r.get('en', '') for r in ps['regions'] if r.get('en')]
        print(sf, ' '.join('pic%s err=%.1f' % l for l in log))
    if len(sys.argv) == 1:
        rep = build_afs_entries(done)
        json.dump(rep, open(os.path.join(WD, 'slot_report.json'), 'w'), indent=1)
        json.dump(tl, open(os.path.join(WD, 'labels_en.json'), 'w'), indent=1)
        for r in rep: print(r)
