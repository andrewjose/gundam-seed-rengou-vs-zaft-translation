"""Paths for the v0.4.4-v0.4.6 image polish rounds (tools/images/polish). Nothing machine-specific:
  W          <work>/polish                    every intermediate (subs*/, afs_out*/, previews/, reports)
  BASE_XDATA <work>/polish/X_DATA_base.BIN    X_DATA with the v0.4.2-level pictures (built by run.py from <work>/afs_new)
  OUT        <work>/polish/out                BASE_XDATA unpacked (<afs>_<sub>.bin / <afs>_raw.bin)
  ORIG       <work>/xd_out                    your original X_DATA unpacked (build step 'unpack')
  SPECS      tools/images/specs               v0.4.2 picture specs (boxes, English, fonts)
Environment overrides: GSEED_POLISH_DIR, GSEED_POLISH_BASE, GSEED_POLISH_OUT, GSEED_POLISH_ORIG."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')))
from gseed import paths as P
P.setup()
for d in ('images', 'xdata', 'core', os.path.join('glyph', 'labels'), os.path.join('images', 'polish')):
    p = os.path.join(P.TOOLS, d)
    if p not in sys.path: sys.path.insert(0, p)
W = os.environ.get('GSEED_POLISH_DIR') or P.work('polish')
BASE_XDATA = os.environ.get('GSEED_POLISH_BASE') or os.path.join(W, 'X_DATA_base.BIN')
OUT = os.environ.get('GSEED_POLISH_OUT') or os.path.join(W, 'out')
ORIG = os.environ.get('GSEED_POLISH_ORIG') or P.unpacked()
SPECS = os.path.join(P.TOOLS, 'images', 'specs')
for d in (W, W + '/subs', W + '/previews'): os.makedirs(d, exist_ok=True)
