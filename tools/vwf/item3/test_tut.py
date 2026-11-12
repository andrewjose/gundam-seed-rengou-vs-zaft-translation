import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,json,struct; sys.path[:0]=[os.path.join(P.TOOLS,'vwf'),os.path.join(P.TOOLS,'vwf','item3'),]
from emu import *
import numpy as np
from PIL import Image
import gimtex, pack as packmod, lz
from text import load
HERE=os.path.join(P.TOOLS,'vwf','item3')
def run(elf,s_va):
    e=Emu(elf); END=0x8804000; out=[]; st={}
    def vcopy(e): e.wr(e.r('a0'),e.rd(e.r('a1'),16)); e.ret()
    def mat(e): st['x']=e.rf(e.r('a2')); e.ret()
    def draw(e): out.append((st['x'],e.rf(0x8ecd110)*256/14,e.rf(0x8ecd114)*512/14,e.r('a0')&0xfff)); e.ret()
    e.hooks={0x8848de0:lambda e:e.ret(),0x89c0964:vcopy,0x88483a8:mat,0x8903178:draw}
    e.wr(0x8ece8a4-0x8804000+0x8804000, struct.pack('<I',0x9a00000))
    buf=0x9e00000; e.wr(buf,b'\0'*0x32)
    e.w('sp',0x9f00000); e.w('ra',END); e.w('a0',buf); e.w('a1',s_va); e.w('a2',0x9e00100); e.run(0x89c1850,END,count=100000)
    n=e.r('v0'); wunits=e.rd(0x9e00100,1)[0]
    pos=0x9e00200; e.wr(pos,struct.pack('<4f',10.0,20.0,0,0))
    e.w('sp',0x9f00000); e.w('ra',END); e.w('a0',pos); e.w('a1',buf); e.w('a2',n)
    for k,r in enumerate(['s0','s1','s2']): e.w(r,0x1234+k)
    e.run(0x89c1a88,END,count=500000)
    assert [e.r(r) for r in ['s0','s1','s2']]==[0x1234+k for k in range(3)]
    return n,wunits,out
def tex(p):
    s,_=packmod.parse(open(p,'rb').read()); g=lz.decompress(s[1]['raw']) if s[1]['flags']&1 else s[1]['raw']
    i,pl=gimtex.read_indices(g,0); return pl[i]
if __name__=='__main__':
    base=open(P.stage('eboot_v03d.elf'),'rb').read()
    new=apply(P.stage('eboot_v03d.elf'),[HERE+'/patch_tut.json'])
    To=tex(P.afs_new(10)); Tn=tex(P.work('vwf','afs_10.bin'))
    rows=[]
    for x in load()['tutorial'][:10]:
        for elf,T,tag in ((base,To,'old'),(new,Tn,'new')):
            n,wu,q=run(elf,x['va'])
            img=Image.new('RGBA',(360*2,16*2),(20,30,90,255))
            for px,col,row,m in q:
                c=int(round(col)); r=int(round(row)); w=7 if m==0xa00 else 14
                cell=Image.fromarray(np.ascontiguousarray(T[r*14:r*14+14,c*14:c*14+w]),'RGBA').resize((w*2,28))
                cx=px+7*(50-wu)/2-10   # centring as in 0x089C1980
                img.alpha_composite(cell,(int(round(cx*2)),2))
            rows.append(img)
        print(x['id'],repr(x['en']),'chars',n,'w-units',wu)
    out=Image.new('RGB',(720,sum(r.height+4 for r in rows))); y=0
    for r in rows: out.paste(r,(0,y)); y+=r.height+4
    out.save(P.ensure(P.work('preview','preview_tutorial.png')))
