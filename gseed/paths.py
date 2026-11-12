"""Path/config resolution. Nothing here is machine-specific: every location is derived from
(1) environment variables, (2) config.local.toml (git-ignored), (3) config.example.toml defaults,
all relative to the repository root unless absolute.

Work-directory layout (created by build/build.py):
  <work>/iso/X_DATA.BIN        original X_DATA.BIN extracted from YOUR ISO
  <work>/iso/EBOOT_dec.BIN     decrypted EBOOT you dumped with PPSSPP
  <work>/xd_out/<afs>_<sub>.bin  every AFS entry unpacked + LZ-decompressed (tools/xdata/unpack.py)
  <work>/glyph/                intermediate files of the label / pilot-name glyph builders
  <work>/images/               gim_new/, preview/ of the menu-image builder
  <work>/afs_new/afs_<i>.bin   rebuilt AFS entries (installed by repack.py afs)
  <work>/stage/                EBOOT stages and the final X_DATA.BIN
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, 'tools')
TOOL_DIRS = ['core', 'xdata', 'text', 'eboot', 'images', 'glyph', 'glyph/labels', 'glyph/pilotname',
             'vwf', 'atlas_legacy', 'chd']

def _parse_toml(path):
    try:
        import tomllib
        with open(path, 'rb') as f: return tomllib.load(f)
    except ModuleNotFoundError:      # Python 3.10: tiny fallback for the flat [section] key = "value" files we use
        out = {}; cur = out
        for line in open(path, encoding='utf-8'):
            line = line.split('#', 1)[0].strip()
            if not line: continue
            if line.startswith('['):
                cur = out.setdefault(line.strip('[]').strip(), {}); continue
            k, v = (x.strip() for x in line.split('=', 1))
            cur[k] = v.strip('"\'')
        return out

def config():
    cfg = {}
    for name in ('config.example.toml', 'config.local.toml'):
        p = os.path.join(ROOT, name)
        if os.path.exists(p):
            for sec, vals in _parse_toml(p).items():
                if isinstance(vals, dict): cfg.setdefault(sec, {}).update(vals)
    return cfg

def _get(env, sec, key, default):
    v = os.environ.get(env)
    if v: return v
    v = config().get(sec, {}).get(key)
    return v if v else default

def _abs(p):
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.join(ROOT, p)

def work(*parts):
    """<workdir>/parts... ; workdir from $GSEED_WORK or [paths] workdir (default 'work')."""
    return os.path.join(_abs(_get('GSEED_WORK', 'paths', 'workdir', 'work')), *parts)

def xdata_orig():
    """Original X_DATA.BIN (read-only input)."""
    return _abs(_get('GSEED_XDATA', 'paths', 'xdata', work('iso', 'X_DATA.BIN')))

def eboot_dec():
    """Decrypted original EBOOT (PPSSPP dump)."""
    return _abs(_get('GSEED_EBOOT', 'paths', 'eboot_dump', work('iso', 'EBOOT_dec.BIN')))

def unpacked(name=''):
    """Unpacked sub-files from tools/xdata/unpack.py: unpacked('12_1.bin')."""
    return work('xd_out', name) if name else work('xd_out')

def afs_new(idx=None):
    return work('afs_new', 'afs_%d.bin' % idx) if idx is not None else work('afs_new')

def stage(name=''):
    return work('stage', name)

def ensure(path):
    d = path if not os.path.splitext(path)[1] else os.path.dirname(path)
    os.makedirs(d, exist_ok=True); return path

def setup():
    """Put every tool directory on sys.path (scripts import each other by module name)."""
    for d in TOOL_DIRS:
        p = os.path.join(TOOLS, d)
        if p not in sys.path: sys.path.append(p)
    if ROOT not in sys.path: sys.path.insert(0, ROOT)

setup()
