#!/usr/bin/env python3
"""Image polish of v0.4.4-v0.4.6, run as one build step (build/build.py step 'polish').
The polish rounds were made on top of the v0.4.2 pictures; here the base is YOUR v0.4.2-level build:
 1. X_DATA_base.BIN = original X_DATA + <work>/afs_new (glyph/images/atlas/text steps), unpacked to <work>/polish/out
 2. round 1 fixes.py (help bar, map labels, location banners, Options grid, credits, copyright line) and
    round 2 fixes2.py (PMF2 quad re-layout of the ad hoc lobby / VS prompts / link status lines, help words);
    the English copyright subs are folded into subs/ (as in the release); build_afs.py -> afs_out/
 3. rounds 3-6 (fixes3.py, fixes3.py banner, fixes4.py, fixes5.py, fixes6.py) -> afs_out_r3 .. afs_out_r6,
    each entry built on the newest earlier round's entry
 4. the newest version of every entry is copied to <work>/afs_polish/ (the xdata step installs it over afs_new)
usage: run.py [--keep]   (--keep: do not rebuild X_DATA_base.BIN / out/ if they exist)"""
import os, sys, glob, shutil, subprocess, json, argparse
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
import ppaths
from gseed import paths as P
import repack, afs, pack, lz

def sh(*args):
    print('  $ polish/' + ' '.join(args)); subprocess.run([sys.executable, os.path.join(H, args[0])] + list(args[1:]), check=True, cwd=H)

def unpack(src, out):
    os.makedirs(out, exist_ok=True)
    f, ents, _ = afs.read(src)
    for i, (o, s) in enumerate(ents):
        f.seek(o); d = f.read(s)
        if pack.is_pack(d):
            subs, _ = pack.parse(d)
            for j, sb in enumerate(subs):
                if not sb['sectors']: continue
                open('%s/%d_%d.bin' % (out, i, j), 'wb').write(lz.decompress(sb['raw']) if sb['flags'] & 1 else sb['raw'])
        else:
            open('%s/%d_raw.bin' % (out, i), 'wb').write(d)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--keep', action='store_true'); a = ap.parse_args()
    W = ppaths.W
    if not (a.keep and os.path.exists(ppaths.BASE_XDATA) and os.path.isdir(ppaths.OUT)):
        if not os.environ.get('GSEED_POLISH_BASE'):
            rep = {int(fn[4:-4]): open(os.path.join(P.afs_new(), fn), 'rb').read()
                   for fn in os.listdir(P.afs_new()) if fn.startswith('afs_') and fn.endswith('.bin')}
            print('  base: original X_DATA + %d entries from afs_new' % len(rep))
            repack.rebuild_afs(P.xdata_orig(), rep, ppaths.BASE_XDATA)
        if not os.environ.get('GSEED_POLISH_OUT'):
            shutil.rmtree(ppaths.OUT, ignore_errors=True); unpack(ppaths.BASE_XDATA, ppaths.OUT)
    for d in glob.glob(W + '/subs*') + glob.glob(W + '/afs_out*'): shutil.rmtree(d)
    os.makedirs(W + '/subs'); os.makedirs(W + '/previews', exist_ok=True)
    for fn in ('fixes_log.json',):
        if os.path.exists(os.path.join(W, fn)): os.remove(os.path.join(W, fn))
    sh('fixes.py'); sh('fixes2.py')
    for p in glob.glob(W + '/subs_opt/*.bin'): shutil.copy(p, W + '/subs/')       # English copyright (2_16, 9_9)
    sh('build_afs.py')
    sh('fixes3.py'); sh('fixes3.py', 'banner'); sh('fixes4.py'); sh('fixes5.py'); sh('fixes6.py')
    final = {}
    for d in ('afs_out', 'afs_out_r3', 'afs_out_r4', 'afs_out_r5', 'afs_out_r6'):
        for p in sorted(glob.glob('%s/%s/afs_*.bin' % (W, d))): final[os.path.basename(p)] = p
    outd = P.work('afs_polish'); shutil.rmtree(outd, ignore_errors=True); os.makedirs(outd)
    for fn, p in final.items(): shutil.copy(p, os.path.join(outd, fn))
    print('  %d polished entries -> %s' % (len(final), outd))

if __name__ == '__main__':
    main()
