import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,os,glob
import repack,pack,lz
f,ents=repack.read_afs()
def entry(i):
    off,size=ents[i]; f.seek(off); return f.read(size)
W=P.work('glyph','pn')
by={}
for p in glob.glob(W+'/*.bin'):
    a,s=os.path.basename(p)[:-4].split('_'); by.setdefault(int(a),{})[int(s)]=open(p,'rb').read()
for a,subs in sorted(by.items()):
    orig=entry(a)
    e=repack.rebuild_pack(orig,subs)
    # verify
    ps,_=pack.parse(e)
    for s,data in subs.items():
        r=ps[s]; got=lz.decompress(r['raw']) if r['flags']&1 else r['raw']
        assert got==data
    os_,_=pack.parse(orig)
    for i,(x,y) in enumerate(zip(os_,ps)):
        if i not in subs: assert x['raw']==y['raw']
    open(P.work('glyph','afs')+'/afs_%d.bin'%a,'wb').write(e)
    print(a,sorted(subs),len(orig),'->',len(e))
