import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,os; sys.path[:0]=[os.path.join(P.TOOLS,'vwf')]
from emu import *
from test_item1 import fw
def pens(elf,name):
    e=Emu(elf); SP=0x9f00000; s=fw(name); e.wr(0x9e00000,s+b'\0\0'); xs=[]
    e.w('sp',SP); e.wr(SP+0x20,b'\xaa'*4); e.wr(SP+0x7c,b'\x55\x55')
    for i in range(len(name)):
        e.w('s2',i); e.w('s3',0x9e00000+2*i); e.w('ra',0x5555); e.w('sp',SP)
        e.run(0x899c060,0x899c090)
        xs.append(round(e.rf(SP+0x20),2))
    return xs
if __name__=='__main__':
    v04=open(P.stage('eboot_v04.elf'),'rb').read()
    new=apply(P.stage('eboot_v04.elf'),[os.path.join(P.TOOLS,'vwf','itemA','patch.json')])
    for n in ['Kira','Athrun','Waltfeld','Cagalli','Lacus']:
        print(n,pens(v04,n),pens(new,n))
    from PIL import Image
    import importlib.util
    spec=importlib.util.spec_from_file_location('pv',os.path.join(P.TOOLS,'vwf','item1','preview.py'))
