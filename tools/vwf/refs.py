import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import struct,sys
from asm import L
import re
d=open(P.stage('eboot_v03d.elf'),'rb').read()
def code_refs(lo,hi):
    # track lui per register within a window (simple): any lui r,H followed within 40 insns by op using r with imm
    out=[]
    for i,(a,w,m,ops) in enumerate(L):
        if m!='lui': continue
        r=ops.split(',')[0]; H=int(ops.split(',')[1],16)
        for j in range(i+1,min(i+60,len(L))):
            a2,w2,m2,o2=L[j]
            if r+')' in o2 or o2.split(',')[-1].strip()==r or (', '+r+',') in o2:
                imm=w2&0xffff
                if imm>=0x8000: imm-=0x10000
                v=(H<<16)+imm
                if lo<=v<hi: out.append((a,a2,hex(v)))
    return out
def data_refs(lo,hi):
    out=[]
    for o in range(0x1d0758,len(d)-3,4):
        v,=struct.unpack_from('<I',d,o)
        if lo<=v<hi: out.append((hex(o),hex(v)))
    return out
if __name__=='__main__':
    lo=int(sys.argv[1],16);hi=int(sys.argv[2],16)
    print(code_refs(lo,hi)[:50]); print(data_refs(lo,hi)[:50])
