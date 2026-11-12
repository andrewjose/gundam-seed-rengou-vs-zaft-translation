import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,json,struct; from emu import *
from test_item1 import fw
import unicorn.mips_const as MC
lay=json.load(open(os.path.join(P.TOOLS,'vwf','item1','layout.json')))
pat=apply(P.stage('eboot_v03d.elf'),[os.path.join(P.TOOLS,'vwf','item1','patch.json')])
base=open(P.stage('eboot_v03d.elf'),'rb').read()
REGS=['v0','v1','a0','a1','a2','a3','t0','t1','t2','t3','t4','t5','t6','t7','s0','s1','s2','s3','s4','s5','s6','s7','t8','t9','gp','sp','fp','ra','at']
SITES={'A':(0x89b5144,'s0','sp+0x6c'),'B':(0x89a03d8,'s3','sp+0x6c'),'C':(0x89ad124,'s0','sp+0x6c'),
       'D':(0x89b29ac,'s1','code'),'E':(0x89b68bc,'s0','sp+0x6c'),'F':(0x89b6b10,'s0','sp+0x6c')}
def conv(e,sj):
    e.wr(0x9d00000,sj+b'\0\0'); e.w('a0',0x9d10000); e.w('a1',0x9d00000); e.w('ra',0x8804000); e.w('sp',0x9f80000)
    e.run(0x89be1b4,0x8804000); return e.rd(0x9d10000,2)
for n,(X,sreg,cl) in SITES.items():
    for nm in ['Kira','G.Wasp']:
        for elf,tag in ((base,'orig'),(pat,'new')):
            e=Emu(elf); SP=0x9f00000
            s=fw(nm); e.wr(0x9e00000,s+b'\0\0')
            xs=[]
            pen=50.0
            for i in range(len(nm)):
                code=conv(e,s[2*i:2*i+2])
                # state at site
                for k,r in enumerate(REGS): e.w(r,0x1000+k)
                e.w('sp',SP); e.w('ra',0x5555)
                e.wr(SP+0x6c,code)
                if cl=='code':
                    buf=0x9e40000
                    allc=b''.join(conv(e,s[2*j:2*j+2]) for j in range(len(nm)))+b'\xff'*8
                    e.wr(buf+6,allc); e.w('s1',buf+2*i)
                    for k,r in enumerate(REGS):
                        if r not in('s1',): e.w(r,0x1000+k)
                    e.w('sp',SP); e.w('ra',0x5555)
                else:
                    e.w(sreg,0x9e00000+2*i)
                e.setf(1,pen); e.setf(2,7.0); e.setf(3,9.0)
                before={r:e.r(r) for r in REGS}
                e.run(X,X+12)
                after={r:e.r(r) for r in REGS}
                ch=[r for r in REGS if before[r]!=after[r]]
                xs.append(round(pen,2)); pen=e.f(0)
                assert e.f(2)==7.0 and e.f(3)==9.0
            print(n,nm,tag,xs,'changed regs',ch)
