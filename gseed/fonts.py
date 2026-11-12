"""Font resolver: fonts are NOT stored in the repo except Roboto Condensed (OFL, tiny).
Search order: $GSEED_FONTS dir, <repo>/fonts, <repo>/fonts/fetched (scripts/fetch_fonts.sh), common system dirs.
Versions used for v0.4.1: DejaVu 2.37, Inter 4.0, Poppins (Google Fonts), Roboto Condensed (fontsource 5.3.0)."""
import os, glob
from .paths import ROOT

SYSTEM = ['/usr/share/fonts', '/usr/local/share/fonts', os.path.expanduser('~/.fonts'),
          os.path.expanduser('~/.local/share/fonts'), '/Library/Fonts', os.path.expanduser('~/Library/Fonts'),
          'C:/Windows/Fonts']

FILES = {
    'dejavu-sans-bold': 'DejaVuSans-Bold.ttf',
    'dejavu-sans': 'DejaVuSans.ttf',
    'dejavu-cond-bold': 'DejaVuSansCondensed-Bold.ttf',
    'inter-bold': 'Inter-Bold.otf',
    'inter-semibold': 'Inter-SemiBold.otf',
    'inter-medium': 'Inter-Medium.otf',
    'inter-extrabold': 'Inter-ExtraBold.otf',
    'poppins-bold': 'Poppins-Bold.ttf',
    'poppins-medium': 'Poppins-Medium.ttf',
    'liberation-sans-bold': 'LiberationSans-Bold.ttf',
    'liberation-sans': 'LiberationSans-Regular.ttf',
    'rc700': 'roboto-condensed-latin-700-normal.ttf',
    'rc600': 'roboto-condensed-latin-600-normal.ttf',
}
_cache = {}

def path(key):
    """Absolute path of font `key` (see FILES). Raises FileNotFoundError with a hint."""
    if key in _cache: return _cache[key]
    fn = FILES[key]
    roots = [os.environ.get('GSEED_FONTS', ''), os.path.join(ROOT, 'fonts'), os.path.join(ROOT, 'fonts', 'fetched')] + SYSTEM
    for r in roots:
        if not r or not os.path.isdir(r): continue
        p = os.path.join(r, fn)
        if os.path.exists(p): _cache[key] = p; return p
        hits = glob.glob(os.path.join(r, '**', fn), recursive=True)
        if hits: _cache[key] = sorted(hits)[0]; return _cache[key]
    raise FileNotFoundError('font %s (%s) not found; run scripts/fetch_fonts.sh or install it system-wide' % (key, fn))
