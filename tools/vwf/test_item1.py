import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,json; from emu import *
def fw(s):
    FW={' ':'\u3000','.':'\uff0e','-':'\uff0d',"'":'\u2019','!':'\uff01','?':'\uff1f'}  # full-width punctuation
    return b''.join((chr(ord(c)+0xfee0) if c.isalnum() else FW[c]).encode('cp932') for c in s)
def run_generic(elf,name,adv=12.5):
    e=Emu(elf); SP=0x9f00000; END=0x8804000
    draws=[]
    def vcopy(e): e.wr(e.r('a0'),e.rd(e.r('a1'),16)); e.ret()
    def draw(e):
        if e.r('a0')==e.r('a0'):  # record pen x of drawer frame
            draws.append((e.rf(DSP[0]+0x60), e.rf(0x8ecd110)))
        e.ret()
    DSP=[0]
    def enter(e): DSP[0]=e.r('sp')-0xc0
    e.hooks={0x8848de0:lambda e:e.ret(),0x89be494:vcopy,0x88483a8:lambda e:e.ret(),0x8903178:draw,0x89be334:enter}
    s=fw(name)+b'\0\0'
    e.wr(0x9e00000,s); e.w('sp',SP); e.w('ra',END)
    e.w('a0',0x9e10000); e.w('a1',0x9e00000)
    e.run(0x89be0d4,END); n=e.r('v0')
    codes=e.rd(0x9e10000,2*n+2)
    obj=0x9e20000
    e.wr(obj,bytes(0x30)); e.wf(obj,100.0); e.wf(obj+0x20,adv); e.wr(obj+0x24,struct.pack('<i',n)); e.wr(obj+0x28,struct.pack('<i',1))
    for k in (0x10,0x14,0x18): e.wf(obj+k,1.0)
    e.w('a0',0x9e10000); e.w('a1',obj); e.w('sp',SP); e.w('ra',END)
    e.run(0x89be334,END)
    return codes,draws
if __name__=='__main__':
    base=open(P.stage('eboot_v03d.elf'),'rb').read()
    pat=apply(P.stage('eboot_v03d.elf'),[os.path.join(P.TOOLS,'vwf','item1','patch.json')])
    for nm in ['Kira','A.Strike','G.Wasp','ZAKU W','Mu']:
        c0,d0=run_generic(base,nm); c1,d1=run_generic(pat,nm)
        print(nm,c1.hex(),'orig x',[round(x[0],2) for x in d0],'new x',[round(x[0],2) for x in d1])
