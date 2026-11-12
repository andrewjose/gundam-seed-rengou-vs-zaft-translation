import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,struct
import numpy as np
from PIL import Image
import pmf,render,gimw,draw
from names import MISRES
d0=open(P.unpacked()+'/140_0.bin','rb').read()
d1=open(P.unpacked()+'/140_1.bin','rb').read()
idx,pal,_=gimw.read(d1)
tex=pal[idx].copy()
SX,SY,SZ=struct.unpack_from('<3f',d0,0x10)
RXT=(16457+16163)/222.0
offs=pmf.objects(d0); objs=[pmf.parse_obj(d0,o) for o in offs]
targets={}
for o,r in zip(offs,objs):
    k=int(r['name'][-2:],16)
    if k in MISRES and r['name']!='misres_mir44' and len(r['prims'])==1:
        q=render.quads(r)[0]; targets[k]=(o,r,q)
assert set(targets)==set(MISRES), set(MISRES)^set(targets)
# clear original strips
for k,(o,r,q) in targets.items():
    u0=int(q['u0']//64); u1=int(-(-q['u1']//64)); v0=int(q['v0']//64)
    tex[v0:v0+16,u0:u1+1]=0
alpha=tex[...,3]
MAXSHOW=222
newverts={}; rep=[]
for k,(o,r,q) in sorted(targets.items()):
    u0=int(q['u0']//64); v0=int(q['v0']//64)
    colend=224 if u0<224 else 512
    # available: until first ink in rows v0..v0+16 to the right
    cols=np.where(alpha[v0:v0+16,u0:colend].max(0)>0)[0]
    avail=(cols[0]-3) if len(cols) else (colend-u0-1)
    txt=MISRES[k]
    im=draw.plain(txt,draw.INTER_B,size=13,H=16,baseline=12)
    w=im.size[0]; xs=1.0
    lim=min(avail,MAXSHOW-2)
    if w>lim:
        xs=lim/w; im=draw.plain(txt,draw.INTER_B,size=13,H=16,baseline=12,xscale=xs); w=im.size[0]
    x0=u0+1
    tex[v0:v0+16,x0:x0+w]=np.maximum(tex[v0:v0+16,x0:x0+w],np.asarray(im)) if False else np.asarray(im)
    # new quad: u from u0 (orig 1.0 -> pixel u0) to x0+w+1
    nu1=(x0+w+1)
    rep.append((r['name'],txt,avail,w,round(xs,2)))
    newverts[k]=nu1
# rebuild objects
newobjs=[]
for o,r in zip(offs,objs):
    i=0; prims=[]
    for t,n in r['prims']: prims.append(r['verts'][i:i+n]); i+=n
    k=int(r['name'][-2:],16)
    if k in newverts and r is targets[k][1]:
        q=targets[k][2]; nu1=newverts[k]
        U1=nu1*64; X1=int(round(q['x0']+(nu1-q['u0']/64)*RXT))
        p=[(U1 if v[0]==q['u1'] else v[0],v[1],X1 if v[2]==q['x1'] else v[2],v[3],v[4]) for v in prims[0]]
        newobjs.append(pmf.build_obj(d0[o:o+0x100],[p],SX,SY,SZ))
    else:
        b=bytearray(pmf.build_obj(d0[o:o+0x100],prims,SX,SY,SZ)); b[0x40:0x50]=d0[o+0x40:o+0x50]; newobjs.append(bytes(b))
new0=pmf.build_file(d0,newobjs)
assert len(new0)==len(d0)
for x in rep: print(x)
open(P.work('glyph')+'/work_140_0.bin','wb').write(new0)
np.save(P.work('glyph')+'/work_140_tex.npy',tex)
