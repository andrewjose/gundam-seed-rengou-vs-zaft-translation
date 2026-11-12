import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,os
import numpy as np
from PIL import Image
import gimw,quant,repack,gim
OUT=P.work('glyph','afs'); os.makedirs(OUT+'/preview',exist_ok=True)
f,ents=repack.read_afs()
def entry(i):
    off,size=ents[i]; f.seek(off); return f.read(size)
def onbg(a):
    im=Image.fromarray(a,'RGBA'); bg=Image.new('RGBA',im.size,(0,0,60,255)); bg.alpha_composite(im); return bg.convert('RGB')
for afs,pmfp,texp in [(12,'work_12_0.bin','work_12_tex.npy'),(140,'work_140_0.bin','work_140_tex.npy')]:
    d1=open(P.unpacked()+'/%d_1.bin'%afs,'rb').read()
    t=np.load(P.work('glyph')+'/'+texp)
    idx,pal,err=quant.quantize(t)
    new1=gimw.write(d1,idx,pal)
    assert len(new1)==len(d1)
    i2,p2,_=gimw.read(new1)
    oi,op,_=gimw.read(d1)
    onbg(op[oi]).save(OUT+'/preview/afs%d_tex_before.png'%afs)
    onbg(p2[i2]).save(OUT+'/preview/afs%d_tex_after.png'%afs)
    new0=open(P.work('glyph')+'/'+pmfp,'rb').read()
    orig=entry(afs)
    e=repack.rebuild_pack(orig,{0:new0,1:new1})
    open(OUT+'/afs_%d.bin'%afs,'wb').write(e)
    print(afs,'quant err',err,'entry',len(orig),'->',len(e))
