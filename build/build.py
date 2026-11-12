#!/usr/bin/env python3
"""Build the English patch v0.4.1 of Kidou Senshi Gundam SEED: Rengou vs. Z.A.F.T. Portable (ULJM05238)
from YOUR OWN files. Nothing from the game is stored in this repository.

    python3 build/build.py --iso <your ULJM05238.iso> --eboot-dump <decrypted EBOOT.BIN> --workdir work [--chd]

Steps (run all, or a subset with --steps a,b,c):
  extract  copy X_DATA.BIN out of the ISO into <work>/iso/ (verifies the ISO MD5 unless --skip-md5)
  eboot    insert translations/eboot_strings.json, apply patches/eboot_v041.json  -> <work>/stage/EBOOT.BIN
  text     missions (AFS 174-473) + unit descriptions (AFS 172/173)                -> <work>/afs_new/
  unpack   unpack + LZ-decompress every AFS entry                                    -> <work>/xd_out/
  glyph    label models (AFS 12/140) + pilot-name glyph sheets (2,11,124,...)       -> <work>/glyph/afs/
  images   ~110 menu/HUD pictures redrawn from tools/images/specs                   -> <work>/afs_new/
  atlas    VWF glyph atlases for dialogue (AFS 1677) and tutorial (AFS 10)          -> <work>/afs_new/
  xdata    rebuild X_DATA.BIN with every entry in <work>/afs_new/                   -> <work>/stage/X_DATA.BIN
  iso      copy the ISO and patch X_DATA.BIN + EBOOT.BIN into the copy             -> <work>/out/*.iso
  chd      (with --chd) convert the patched ISO to CHD v5 and verify it              -> <work>/out/*.chd

The EBOOT step is exact: the result is checked against the MD5 of the tested v0.4.1 EBOOT. The graphics steps
regenerate the pictures from fonts on your machine; they match the tested build visually but not necessarily
byte-for-byte (see docs/technical.md, "Reproducibility").
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
STEPS = ['extract', 'eboot', 'text', 'unpack', 'glyph', 'images', 'atlas', 'xdata', 'iso', 'chd']
ISO_MD5 = '0d4dd06ba223f7ff60e05d9f61483905'          # retail ULJM05238 UMD image
EBOOT_V041_MD5 = '1667c483ad06c3cfbe3455389aba9ce9'   # decrypted EBOOT after this patch (tested in PPSSPP)
VERSION = 'v0.4.1'

def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for c in iter(lambda: f.read(8 << 20), b''): h.update(c)
    return h.hexdigest()

def run(env, *args):
    print('  $ python3', ' '.join(os.path.relpath(a, ROOT) if os.path.isabs(a) and a.startswith(ROOT) else a for a in args))
    subprocess.run([sys.executable] + list(args), check=True, env=env, cwd=ROOT)

def tool(*p): return os.path.join(ROOT, 'tools', *p)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--iso', help='your ULJM05238 ISO (needed for extract / iso)')
    ap.add_argument('--eboot-dump', help='decrypted EBOOT.BIN dumped by PPSSPP (needed for eboot)')
    ap.add_argument('--workdir', default=os.path.join(ROOT, 'work'))
    ap.add_argument('--steps', default=','.join(STEPS[:-1]), help='comma list, default: everything except chd')
    ap.add_argument('--chd', action='store_true', help='also write a CHD of the patched ISO')
    ap.add_argument('--skip-md5', action='store_true', help='do not verify the input ISO MD5 (not recommended)')
    a = ap.parse_args()
    steps = a.steps.split(',') + (['chd'] if a.chd and 'chd' not in a.steps else [])
    bad = [s for s in steps if s not in STEPS]
    if bad: raise SystemExit('unknown step(s): %s' % bad)
    W = os.path.abspath(a.workdir)
    for d in ('iso', 'stage', 'afs_new', 'glyph/afs', 'out'): os.makedirs(os.path.join(W, d), exist_ok=True)
    env = dict(os.environ, GSEED_WORK=W, GSEED_XDATA=os.path.join(W, 'iso', 'X_DATA.BIN'),
               GSEED_EBOOT=os.path.abspath(a.eboot_dump) if a.eboot_dump else os.path.join(W, 'iso', 'EBOOT_dec.BIN'))
    xdata = env['GSEED_XDATA']
    out_iso = os.path.join(W, 'out', 'Gundam SEED Rengou vs ZAFT Portable (English %s).iso' % VERSION)
    t0 = time.time()

    if 'extract' in steps:
        print('[extract]')
        if not a.iso: raise SystemExit('--iso is required')
        if not a.skip_md5:
            m = md5(a.iso)
            if m != ISO_MD5: raise SystemExit('ISO MD5 %s != %s (expected the retail ULJM05238 image; use --skip-md5 to force)' % (m, ISO_MD5))
            print('  ISO MD5 ok')
        import pycdlib
        iso = pycdlib.PyCdlib(); iso.open(a.iso)
        with open(xdata, 'wb') as f:
            try: iso.get_file_from_iso_fp(f, iso_path='/PSP_GAME/USRDIR/X_DATA.BIN')
            except Exception: iso.get_file_from_iso_fp(f, iso_path='/PSP_GAME/USRDIR/X_DATA.BIN;1')
        iso.close(); print('  X_DATA.BIN: %d bytes' % os.path.getsize(xdata))

    if 'eboot' in steps:
        print('[eboot]')
        if not os.path.exists(env['GSEED_EBOOT']): raise SystemExit('--eboot-dump is required (see README: dumping the decrypted EBOOT)')
        p = json.load(open(os.path.join(ROOT, 'patches', 'eboot_v041.json')))
        have = hashlib.sha1(open(env['GSEED_EBOOT'], 'rb').read()).hexdigest()
        if have != p['input_sha1']:
            raise SystemExit('decrypted EBOOT sha1 %s != expected %s - dump it again from the unmodified game' % (have, p['input_sha1']))
        s1 = os.path.join(W, 'stage', 'eboot_strings.elf'); fin = os.path.join(W, 'stage', 'EBOOT.BIN')
        run(env, tool('eboot', 'insert_strings.py'), env['GSEED_EBOOT'], s1)
        run(env, tool('eboot', 'apply_patch.py'), s1, fin, os.path.join(ROOT, 'patches', 'eboot_v041.json'))
        assert md5(fin) == EBOOT_V041_MD5, 'final EBOOT MD5 mismatch'
        print('  EBOOT.BIN MD5 %s (matches the tested v0.4.1 EBOOT)' % EBOOT_V041_MD5)

    if 'text' in steps:
        print('[text]'); run(env, tool('text', 'insert_text.py'))
    if 'unpack' in steps:
        print('[unpack]'); run(env, tool('xdata', 'unpack.py'))
    if 'glyph' in steps:
        print('[glyph]')
        for s in (('glyph', 'labels', 'build12.py'), ('glyph', 'labels', 'build140.py'), ('glyph', 'labels', 'assemble.py'),
                  ('glyph', 'pilotname', 'build_tex.py'), ('glyph', 'pilotname', 'assemble.py')):
            run(env, tool(*s))
        g = os.path.join(W, 'glyph', 'afs')
        for fn in os.listdir(g):
            if fn.startswith('afs_') and fn.endswith('.bin'): shutil.copyfile(os.path.join(g, fn), os.path.join(W, 'afs_new', fn))
    if 'images' in steps:
        print('[images]'); run(env, tool('images', 'build.py'))
    if 'atlas' in steps:
        print('[atlas]'); run(env, tool('vwf', 'atlas_vwf.py'))

    if 'xdata' in steps:
        print('[xdata]')
        from gseed import paths  # noqa: E402  (after env is known)
        os.environ.update(env); paths.setup()
        import repack
        rep = {int(fn[4:-4]): open(os.path.join(W, 'afs_new', fn), 'rb').read()
               for fn in os.listdir(os.path.join(W, 'afs_new')) if fn.startswith('afs_') and fn.endswith('.bin')}
        out = os.path.join(W, 'stage', 'X_DATA.BIN')
        repack.rebuild_afs(xdata, rep, out)
        print('  %d entries replaced -> %s (%d bytes)' % (len(rep), out, os.path.getsize(out)))

    if 'iso' in steps:
        print('[iso]')
        if not a.iso: raise SystemExit('--iso is required')
        print('  copying ISO ...'); shutil.copyfile(a.iso, out_iso)
        run(env, tool('core', 'build_iso.py'), a.iso, out_iso, os.path.join(W, 'stage', 'X_DATA.BIN'), os.path.join(W, 'stage', 'EBOOT.BIN'))
        print('  -> %s' % out_iso)

    if 'chd' in steps:
        print('[chd]')
        chd = os.path.splitext(out_iso)[0] + '.chd'
        run(env, tool('chd', 'iso2chd.py'), out_iso, chd)
        run(env, tool('chd', 'chdverify.py'), chd, '--against', out_iso)
        print('  -> %s' % chd)
    print('done in %.0f s' % (time.time() - t0))

if __name__ == '__main__':
    main()
