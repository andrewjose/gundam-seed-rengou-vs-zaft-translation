import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import struct,sys
from asm import L,A
def o2v(o): return o-0x54+0x8804000
def v2o(v): return v-0x8804000+0x54
def find(path,lo,hi):
    d=open(path,'rb').read()
    vlo,vhi=o2v(lo),o2v(hi)
    hit=set()
    for o in range(0x54,len(d)-3,4):
        v=struct.unpack_from('<I',d,o)[0]
        if vlo<=v<vhi: hit.add(v2o(v))
    for i,(a,w,m,ops) in enumerate(L):
        if m=='lui':
            H=int(ops.split(',')[1],16)
            if not (vlo>>16)-1<=H<=(vhi>>16)+1: continue
            for j in range(i+1,min(i+80,len(L))):
                imm=L[j][1]&0xffff
                for v in ((H<<16)+(imm-0x10000 if imm>=0x8000 else imm),(H<<16)|imm):
                    if vlo<=v<vhi: hit.add(v2o(v))
    # strings: segments delimited by NUL; a string is used if any hit inside [start,end]
    spans=[];o=lo
    used=bytearray(hi-lo)
    s=lo
    while s<hi:
        if d[s]==0: s+=1; continue
        e=d.index(b'\0',s)
        if any(s<=h<=e for h in hit): used[s-lo:e+1-lo]=b'\1'*(e+1-s)
        s=e+1
    for h in hit:
        if lo<=h<hi: used[h-lo]=1
    # free = not used; but leave 1 byte guard after used strings (NUL kept)
    i=0;out=[]
    while i<len(used):
        if not used[i]:
            j=i
            while j<len(used) and not used[j]: j+=1
            a=(lo+i+4)&~3   # keep at least one NUL after previous string
            b=(lo+j)&~3
            if b-a>=16: out.append((a,b))
            i=j
        else: i+=1
    return out,d
if __name__=='__main__':
    out,d=find(P.stage('eboot_v03d.elf'),int(sys.argv[1],16),int(sys.argv[2],16))
    for a,b in out: print(hex(a),hex(b),b-a,hex(o2v(a)))
    print(sum(b-a for a,b in out))
