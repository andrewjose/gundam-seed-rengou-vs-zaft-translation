import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,os
import numpy as np
from PIL import Image
import gimm,cells
KB=("ABCDEFGHIJ" "KLMNOPQRST" "UVWXYZabcd" "efghij*k*l" "mnopqrstuv" "wxyz.-'!?")
COPIES=[ # (afs,sub,img,group,y0,mode)
 (2,2,0,'G1',0,'disp'),(134,1,5,'G1',0,'disp'),(124,1,0,'G2',0,'disp'),(129,1,1,'G2',0,'disp'),
 (11,1,1,'G3',0,'kbd'),(130,1,0,'G3',0,'kbd'),(135,1,3,'G4',0,'disp'),(137,1,0,'G4',54,'disp'),(138,1,0,'G4',54,'disp')]
def premul(c): c=c.astype(np.float32); return np.concatenate([c[...,:3]*c[...,3:4]/255,c[...,3:4]],-1)
OUT=P.work('glyph','pn'); os.makedirs(OUT,exist_ok=True); os.makedirs(P.work('glyph','preview','pilotname'),exist_ok=True)
def onbg(a):
    im=Image.fromarray(a,'RGBA'); bg=Image.new('RGBA',im.size,(0,0,60,255)); bg.alpha_composite(im); return bg.convert('RGB')
results={}
for afs,sub,k,g,y0,mode in COPIES:
    key='%d_%d'%(afs,sub)
    d=results.get(key) or open(P.unpacked()+'/%s.bin'%key,'rb').read()
    idx,pal,m=gimm.read(d,k)
    rgba=pal[idx]; before=rgba.copy()
    PP=premul(pal)
    transp=int(np.where(pal[:,3]==0)[0][0])
    p=cells.GROUPS[g]['p']
    jobs=[]
    for i,ch in enumerate(KB):
        if ch=='*': continue
        jobs.append((i//10,i%10,ch))
    if mode=='disp':
        for n in range(10): jobs.append((6,n,str(n)))
    for r,c,ch in jobs:
        x,y=c*p,y0+r*p
        glyph=cells.cell(ch,g)
        sub_=premul(glyph).reshape(-1,4)
        dd=((sub_[:,None,:]-PP[None,:,:])**2).sum(-1)
        ii=dd.argmin(1).reshape(p,p)
        ii[glyph[...,3]==0]=transp
        idx[y:y+p,x:x+p]=ii
    d=gimm.write(d,k,idx)
    results[key]=d
    after=pal[gimm.read(d,k)[0]]
    hh=y0+7*p
    a=onbg(before[:hh]); b=onbg(after[:hh])
    im=Image.new('RGB',(a.size[0]*2+8,hh),(40,40,40)); im.paste(a,(0,0)); im.paste(b,(a.size[0]+8,0))
    im.resize((im.size[0]*3,im.size[1]*3),Image.NEAREST).save(P.work('glyph','preview')+'/pilotname/afs%d_sub%d_img%d.png'%(afs,sub,k))
for key,d in results.items(): open(OUT+'/%s.bin'%key,'wb').write(d)
print(sorted(results))
