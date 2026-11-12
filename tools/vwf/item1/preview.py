import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,json; import numpy as np, gimm
from PIL import Image
from test_item1 import run_generic, fw
from emu import apply
base=open(P.stage('eboot_v03d.elf'),'rb').read()
pat=apply(P.stage('eboot_v03d.elf'),[os.path.join(P.TOOLS,'vwf','item1','patch.json')])
def sheet(afs,sub,k):
    d=open(P.work('glyph','pn')+'/%d_%d.bin'%(afs,sub),'rb').read()
    idx,pal,m=gimm.read(d,k); return pal[idx]
SC=3
def render(codes,xs,sh,P,A,y0=0):
    W=int((max(xs)+A*2-min(xs)+10)*SC); H=int(A*1.3*SC)
    img=Image.new('RGBA',(W,H),(30,30,70,255))
    for (c,pg),x in zip(codes,xs):
        if c>=0x80: continue
        r,col=divmod(c,15)
        cell=Image.fromarray(np.ascontiguousarray(sh[y0+r*P:y0+r*P+P,col*P:col*P+P]),'RGBA').resize((int(A*SC),int(A*SC)),Image.BILINEAR)
        img.alpha_composite(cell,(int((x-min(xs)+5)*SC),int(0.15*A*SC)))
    return img
rows=[]
s22=sheet(2,2,0)
for nm in ['Kira','Athrun','A.Strike','G.Wasp','ZAKU W','Skygrasp','Waltfeld','Murrue','Archangl','M1Astray','Lacus','Cagalli']:
    for elf,tag in ((base,'orig'),(pat,'new')):
        c,dr=run_generic(elf,nm)
        codes=[(c[2*i],c[2*i+1]) for i in range(len(c)//2) if c[2*i]<0x80][:len(dr)]
        rows.append(render(codes,[x for x,_ in dr],s22,14,12.5))
W=max(r.width for r in rows); H=sum(r.height+4 for r in rows)
out=Image.new('RGB',(W,H),(0,0,0)); y=0
for r in rows: out.paste(r,(0,y)); y+=r.height+4
out.save(P.ensure(P.work('preview','preview_generic14_G1.png'))); print('saved',out.size)
# 18px (AFS 137_1_0, y0=54) and 14px medium (AFS 124_1_0): pens from the same formula as VW_CORE (checked against emulation)
lay=json.load(open(os.path.join(P.TOOLS,'vwf','item1','layout.json')))
import struct
d=bytes(pat)
def tab(g):
    o=int(lay['tables'][g],16)-0x8804000+0x54; return d[o:o+104]
from conv import convert
def pens(nm,g,A):
    T=tab(g); cs=[c for c,p in convert(fw(nm))]
    H=lambda c: T[c] if c<100 else (T[85] if c==255 else T[101])
    xs=[0.0]
    for i,c in enumerate(cs[:-1]): xs.append(xs[-1]+A*(H(c)+H(cs[i+1])+T[100])/64)
    return [(c,0) for c in cs],xs
rows=[]
for (afs,sub,k,y0,P,A,g) in [(137,1,0,54,18,13.0,'T18'),(124,1,0,0,14,13.0,'G2')]:
    sh=sheet(afs,sub,k)
    for nm in ['Kira','A.Strike','Gunner','Waltfeld']:
        cs,xs=pens(nm,g,A)
        o=[(c,0) for c in cs]; xo=[A*i for i in range(len(cs))]
        keep=[i for i,(c,_) in enumerate(cs) if c<0x80]
        rows.append(render([cs[i] for i in keep],[xo[i] for i in keep],sh,P,A,y0))
        rows.append(render([cs[i] for i in keep],[xs[i] for i in keep],sh,P,A,y0))
W=max(r.width for r in rows); H=sum(r.height+4 for r in rows)
out=Image.new('RGB',(W,H),(0,0,0)); y=0
for r in rows: out.paste(r,(0,y)); y+=r.height+4
out.save(P.ensure(P.work('preview','preview_18px_and_14px_medium.png'))); print('saved',out.size)
