import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
from emu import *
from test_item1 import fw
import numpy as np, gimm
from PIL import Image
def pens(elf,name):
    e=Emu(elf); SP=0x9f00000; buf=0x9e10000
    e.wr(buf,b'\xff'*16); s=fw(name)
    for i in range(len(name)):
        e.wr(0x9e00000,s[2*i:2*i+2]+b'\0\0'); e.w('a0',buf+2*i); e.w('a1',0x9e00000); e.w('ra',0x8804000); e.w('sp',SP); e.run(0x89be1b4,0x8804000)
    codes=e.rd(buf,16); out=[]
    for k in range(8):
        if codes[2*k]==0xff: continue
        e.w('s2',k); e.w('s3',buf+2*k); e.w('sp',SP); e.w('ra',0x5555); e.w('s4',0x1234); e.w('s5',0x77)
        e.run(0x899d36c,0x899d390); out.append((codes[2*k],round(e.f(20),2)))
        assert e.r('s4')==0x1234 and e.r('s5')==0x77
    return out
if __name__=='__main__':
    a=open(P.stage('eboot_v041a.elf'),'rb').read(); b=apply(P.stage('eboot_v041a.elf'),[os.path.join(P.TOOLS,'vwf','itemA2','patch.json')])
    dd=open(P.work('glyph','pn','137_1.bin'),'rb').read(); idx,pal,m=gimm.read(dd,0); sh=pal[idx]
    rows=[]
    for n in ['Kira','Mu','Athrun','Waltfeld','ZAKU W','Lacus']:
        for elf in (a,b):
            p=pens(elf,n); print(n,p)
            img=Image.new('RGBA',(360,44),(30,30,70,255))
            for c,x in p:
                r,col=divmod(c,15)
                cell=Image.fromarray(np.ascontiguousarray(sh[54+r*18:54+r*18+18,col*18:col*18+18]),'RGBA').resize((36,36))
                img.alpha_composite(cell,(int((x+4)*2),4))
            rows.append(img)
    out=Image.new('RGB',(360,sum(r.height+4 for r in rows))); y=0
    for r in rows: out.paste(r,(0,y)); y+=r.height+4
    out.save(P.ensure(P.work('preview','preview_pilot_select.png')))
