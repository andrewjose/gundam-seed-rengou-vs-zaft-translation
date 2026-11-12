import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys; import pack,lz,gimw,render,os
from PIL import Image
PV=P.work('glyph','preview')+'/'; os.makedirs(PV,exist_ok=True)
def subs(e):
    return [lz.decompress(s['raw']) if s['flags']&1 else s['raw'] for s in pack.parse(e)[0]]
for a,sx,sy in [(12,1/77.07,1/403.07),(140,1/146.94,1/258.0)]:
    n=subs(open(P.work('glyph','afs')+'/afs_%d.bin'%a,'rb').read())
    for tag,(p0,p1) in [('after',(n[0],n[1])),('before',(open(P.unpacked()+'/%d_0.bin'%a,'rb').read(),open(P.unpacked()+'/%d_1.bin'%a,'rb').read()))]:
        idx,pal,_=gimw.read(p1); tex=Image.fromarray(pal[idx],'RGBA')
        open(P.work('glyph','tmp_pmf.bin'),'wb').write(p0)
        print(a,tag,render.sheet(P.work('glyph','tmp_pmf.bin'),tex,PV+'afs%d_labels_%s.png'%(a,tag),sx=sx,sy=sy,cols=3))
