import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,json,struct,os; sys.path[:0]=[os.path.join(P.TOOLS,'vwf'),os.path.join(P.TOOLS,'vwf','item3'),]
from emu import *
import numpy as np
from PIL import Image
import gimtex, pack as packmod, lz
from text import load
HERE=os.path.join(P.TOOLS,'vwf','item3')
def run(elf,s_va,count=15,x=100.0,y=50.0):
    e=Emu(elf); END=0x8804000; quads=[]
    def gdraw(e):
        a0=e.r('a0'); vp=struct.unpack('<I',e.rd(a0+0x14,4))[0]; up=struct.unpack('<I',e.rd(a0+0x28,4))[0]
        x0,y0=struct.unpack('<2f',e.rd(vp,8)); x1,y1=struct.unpack('<2f',e.rd(vp+0x10,8))
        uv=struct.unpack('<4H',e.rd(up,8)); quads.append((x0,y0,x1,y1)+uv); e.ret()
    e.hooks={0x8902694:gdraw}
    buf=0x9e00000; e.wr(buf,b'\xff'*0x1e)
    e.w('sp',0x9f00000); e.w('ra',END); e.w('a0',buf); e.w('a1',s_va); e.run(0x8988c84,END,count=100000)
    e.w('sp',0x9f00000); e.w('ra',END); e.w('a0',count); e.w('a1',buf); e.setf(12,x); e.setf(13,y)
    for k,r in enumerate(['s0','s1','s2','s3','s4']): e.w(r,0x1234+k)
    e.setf(20,3.0); e.setf(21,4.0); e.setf(22,5.0)
    e.run(0x8988edc,END,count=200000)
    assert [e.r(r) for r in ['s0','s1','s2','s3','s4']]==[0x1234+k for k in range(5)]
    assert (e.f(20),e.f(21),e.f(22))==(3.0,4.0,5.0)
    return quads,e.r('v0')
def tex(entry):
    subs,_=packmod.parse(entry); g=lz.decompress(subs[0]['raw']) if subs[0]['flags']&1 else subs[0]['raw']
    i,p=gimtex.read_indices(g); return p[i]
def render(quads,T,SC=3,W=200,H=16):
    img=Image.new('RGBA',(W*SC,H*SC),(20,30,90,255))
    for x0,y0,x1,y1,u0,v0,u1,v1 in quads:
        if x1<=x0: continue
        cell=Image.fromarray(np.ascontiguousarray(T[v0:v1,u0:u1]),'RGBA').resize((max(1,int(round((x1-x0)*SC))),int(round((y1-y0)*SC))),Image.BILINEAR)
        img.alpha_composite(cell,(int(round((x0-100+3)*SC)),int(round((y0-50+1)*SC))))
    return img
if __name__=='__main__':
    base=open(P.stage('eboot_v03d.elf'),'rb').read()
    new=apply(P.stage('eboot_v03d.elf'),[HERE+'/patch.json'])
    from atlas_vwf import original_entry
    Told=tex(original_entry(1677)); Tnew=tex(open(P.work('vwf','afs_1677.bin'),'rb').read())
    T=load()['dialogue']
    import random; random.seed(1)
    pick=sorted(T,key=lambda x:-len(x['en']))[:4]+random.sample(T,8)
    rows=[]
    for x in pick:
        q0,r0=run(base,x['va']); q1,r1=run(new,x['va'])
        print(x['id'],repr(x['en']),'ret',r0,r1,'old right edge %.1f new right edge %.1f'%(max(q[2] for q in q0)-100,max(q[2] for q in q1)-100))
        rows+= [render(q0,Told),render(q1,Tnew)]
    # partial count (typewriter count=1 -> 2 chars)
    q,r=run(new,pick[0]['va'],count=1); print('count=1 draws',len(q),'ret',r)
    out=Image.new('RGB',(rows[0].width,sum(r.height+6 for r in rows)),(0,0,0)); y=0
    for r in rows: out.paste(r,(0,y)); y+=r.height+6
    out.save(P.ensure(P.work('preview','preview_dialogue.png'))); print(out.size)
