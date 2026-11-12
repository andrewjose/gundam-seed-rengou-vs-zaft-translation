import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,struct,json
import numpy as np
from PIL import Image
import pmf,render,gimw,draw
from names import SEL12_L,WEAPONS
OUT=P.work('glyph','afs')
d0=open(P.unpacked()+'/12_0.bin','rb').read()
d1=open(P.unpacked()+'/12_1.bin','rb').read()
idx,pal,_=gimw.read(d1)
orig=pal[idx].copy()                       # RGBA 512x512
tex=orig.copy()
SX,SY,SZ=struct.unpack_from('<3f',d0,0x10)
RX=1156/15.0   # raw x per texel (=77.07)
RY=10883/27.0  # raw y per texel (=403.07)

# ---------- 1. free regions in left half ----------
KEEP=[(196,176,228,196),(0,196,228,256),(238,312,254,332),(240,368,256,388),(0,256,112,276)]
keepmask=np.zeros((512,512),bool)
for x0,y0,x1,y1 in KEEP: keepmask[y0:y1,x0:x1]=True
left=np.zeros((512,512),bool); left[:,0:256]=True
clear=left&~keepmask
tex[clear]=0
# shelves (y, height, xmax)
SHELVES=[]
for y in range(0,168,28): SHELVES.append([y,0,256])
SHELVES.append([168,0,194])
for y in range(278,478,28):
    xmax=256
    for x0,y0,x1,y1 in KEEP[2:4]:
        if y<y1 and y+28>y0: xmax=min(xmax,x0-1)
    SHELVES.append([y,0,xmax])
def alloc(w):
    for s in SHELVES:
        if s[1]+w<=s[2]:
            x=s[1]; s[1]+=w+1; return x,s[0]
    return None

# ---------- 2. tokens ----------
mains=[v[0] for v in SEL12_L.values()]; subs=[v[1] for v in SEL12_L.values() if v[1]]
chars=sorted(set(''.join(mains+subs))-{' '})
from collections import Counter
wc=Counter(w for m in mains for w in m.split())
cells={}   # token -> dict(x,y,w,xoff,adv)
def add(tok):
    im,xoff,adv=draw.outlined_seq(tok)
    pos=alloc(im.size[0])
    if pos is None: return False
    x,y=pos
    a=np.asarray(im)
    tex[y:y+28,x:x+im.size[0]]=a
    cells[tok]=dict(x=x,y=y,w=im.size[0],xoff=xoff,adv=adv)
    return True
for ch in chars: assert add(ch),ch
# greedy words by quads saved
cand=sorted([w for w in wc if len(w)>1],key=lambda w:-(wc[w]*(len(w)-1)))
words_added=[]
for w in cand:
    if wc[w]*(len(w)-1)<2: continue
    if add(w): words_added.append(w)
print('chars',len(chars),'words',words_added)
print('shelves used',[(s[0],s[1],s[2]) for s in SHELVES])

# ---------- 3. weapon strips (right half) ----------
d_objs=pmf.objects(d0)
objs=[pmf.parse_obj(d0,o) for o in d_objs]
tex[:,256:512]=0
for r in objs:
    if not r['name'].startswith('sel12_q'): continue
    k=int(r['name'][7:],16); q=render.quads(r)[0]
    cx0=int(q['u0']//64); cx1=int(-(-q['u1']//64)); cy=int(q['v0']//64)
    avail=cx1-cx0-3
    txt=WEAPONS[k]
    im=draw.plain(txt,draw.INTER_B,size=13,H=16,baseline=12)
    if im.size[0]>avail:
        xs=avail/im.size[0]
        im=draw.plain(txt,draw.INTER_B,size=13,H=16,baseline=12,xscale=xs)
        print('squeeze weapon',txt,round(xs,2))
    a=np.asarray(im); w=a.shape[1]
    tex[cy:cy+16,cx1-2-w:cx1-2]=a

# ---------- 4. rebuild sel12_l objects ----------
def layout(main,sub,z):
    """returns list of (cell, xpos_tex(left of ink-cell), scale) in texels, pen advances in texels"""
    items=[];pen=0.0
    SPACE=8.0; TRACK=1.5
    def put_word(w,s):
        nonlocal pen
        if w in cells:
            c=cells[w]; items.append((c,pen+c['xoff']*s,s)); pen+=c['adv']*s
        else:
            for i,ch in enumerate(w):
                c=cells[ch]; items.append((c,pen+c['xoff']*s,s)); pen+=c['adv']*s
                if i<len(w)-1: pen+=TRACK*s
    ws=main.split()
    for i,w in enumerate(ws):
        put_word(w,1.0)
        if i<len(ws)-1: pen+=SPACE
    if sub:
        pen+=SPACE*0.8; s=0.72
        sws=sub.split()
        for i,w in enumerate(sws):
            put_word(w,s)
            if i<len(sws)-1: pen+=SPACE*s
    return items
MAXW=300.0
newobjs=[]; report=[]
for o,r in zip(d_objs,objs):
    i=0; prims=[]
    for t,n in r['prims']: prims.append(r['verts'][i:i+n]); i+=n
    if not r['name'].startswith('sel12_l'):
        b=bytearray(pmf.build_obj(d0[o:o+0x100],prims,SX,SY,SZ)); b[0x40:0x50]=d0[o+0x40:o+0x50]; newobjs.append(bytes(b)); continue
    k=int(r['name'][7:],16); main,sub=SEL12_L[k]
    keep=[p for p in prims if min(v[3] for v in p)>=10681]
    namep=[p for p in prims if min(v[3] for v in p)<10681]
    z=namep[0][0][4]
    items=layout(main,sub,z)
    right=max(x+c['w']*s for c,x,s in items); left=min(x for c,x,s in items)
    width=right-left; sq=min(1.0,MAXW/width)
    newp=[]
    for c,x,s in items:
        u0=(c['x'])*64+32; u1=(c['x']+c['w'])*64-32; v0=c['y']*64+32; v1=(c['y']+28)*64-32
        X0=((x+0.5*s)-right)*sq*RX; X1=((x+(c['w']-0.5)*s)-right)*sq*RX
        if s==1.0: Y1,Y0=10883,0
        else:
            yb=(27.5-20)*RY; Y1=yb+(20-0.5)*RY*s; Y0=yb-(27.5-20)*RY*s
        X0=int(round(X0));X1=int(round(X1));Y0=int(round(Y0));Y1=int(round(Y1))
        newp.append([(u0,v0,X0,Y1,z),(u0,v1,X0,Y0,z),(u1,v0,X1,Y1,z),(u1,v1,X1,Y0,z)])
    report.append((r['name'],main,sub,round(width,1),round(sq,3),len(newp),len(namep)))
    newobjs.append(pmf.build_obj(d0[o:o+0x100],keep+newp,SX,SY,SZ))
new0=pmf.build_file(d0,newobjs)
for x in report: print(x)
print('12_0 size',len(d0),'->',len(new0))
open(P.work('glyph')+'/work_12_0.bin','wb').write(new0)
np.save(P.work('glyph')+'/work_12_tex.npy',tex)
