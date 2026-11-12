import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import struct,sys
from asm import L,A
d=open(P.stage('eboot_v03d.elf'),'rb').read()
# function starts: after 'jr $ra' + delay slot
starts=[L[0][0]]
for i,(a,w,m,o) in enumerate(L[:-2]):
    if m=='jr' and o=='$ra': starts.append(L[i+2][0])
starts=sorted(set(starts))
jt=set()
for a,w,m,o in L:
    if m in('jal','j'): jt.add(int(o,16))
# data words
words=set()
for off in range(0x54,len(d)-3,4):
    words.add(struct.unpack_from('<I',d,off)[0])
# lui/addiu pairs
pairs=set()
for i,(a,w,m,o) in enumerate(L):
    if m=='lui':
        r=o.split(',')[0]; H=int(o.split(',')[1],16)
        for j in range(i+1,min(i+40,len(L))):
            w2=L[j][1]; imm=w2&0xffff
            if imm>=0x8000: imm-=0x10000
            pairs.add(((H<<16)+imm)&0xffffffff)
res=[]
for k,s in enumerate(starts[:-1]):
    e=starts[k+1]
    if s in jt or s in words or s in pairs: continue
    res.append((e-s,s,e))
res.sort(reverse=True)
for r in res[:40]: print(r[0],hex(r[1]),hex(r[2]))
print('---refined')
import re
br=[]
for a,w,m,o in L:
    if m.startswith('b') or m in ('j',):
        t=o.split(',')[-1].strip()
        if t.startswith('0x'): br.append((a,int(t,16)))
good=[]
for sz,s,e in res[:200]:
    bad=[x for x in br if s<=x[1]<e and not (s<=x[0]<e)]
    out=[x for x in br if s<=x[0]<e and not (s<=x[1]<e) and L[A[x[0]]][2]!='j']
    if not bad and not out: good.append((sz,s,e))
for g in good[:30]: print(g[0],hex(g[1]),hex(g[2]))
