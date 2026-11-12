import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,os,time,random
import lz
rows=[l.rstrip('\n').split('\t') for l in open(P.unpacked()+'/index.tsv')][1:]
lzrows=[r for r in rows if r[2]=='Y']
random.seed(1); sample=random.sample(lzrows,int(sys.argv[1]) if len(sys.argv)>1 else 300)
t=time.time(); ok=0; tc=0; to=0; worse=0
for r in sample:
    d=open(P.unpacked()+'/%s_%s.bin'%(r[0],r[1]),'rb').read()
    c=lz.compress(d)
    assert lz.decompress(c)==d,(r)
    if len(c)>int(r[3]): worse+=1
    tc+=len(c); to+=int(r[3]); ok+=1
# literal-only on 30
for r in sample[:30]:
    d=open(P.unpacked()+'/%s_%s.bin'%(r[0],r[1]),'rb').read()
    assert lz.decompress(lz.compress(d,0))==d
print('roundtrip ok',ok,'ours/orig size %.3f'%(tc/to),'files larger than original',worse,'%.1fs'%(time.time()-t))
