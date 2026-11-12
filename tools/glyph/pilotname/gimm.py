"""Multi-image GIM helpers (8bpp indexed fmt5 swizzled / linear). image k -> (idx array, palette RGBA, meta)."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,struct,numpy as np
import gim
def pics(d):
    out=[]; cur=None
    for bid,off,size,nxt,dat in gim.blocks(d,0x10,len(d)):
        if bid==3: cur={}; out.append(cur)
        elif bid==4: cur['img']=gim.parse_img_hdr(d,off+dat)
        elif bid==5: cur['pal']=gim.parse_img_hdr(d,off+dat)
    return [p for p in out if 'img' in p]
def read(d,k):
    P=pics(d)[k]; ih=P['img']; ph=P['pal']
    assert ih['fmt']==5, ih
    w,h=ih['w'],ih['h']; pitch=(w+15)&~15; ha=(h+7)&~7
    lvl0=ih['base']+struct.unpack_from('<I',d,ih['base']+ih['idxstart'])[0]
    raw=d[lvl0:lvl0+pitch*ha]
    if ih['order']==1: arr=gim.unswizzle(raw,pitch,h)
    else: arr=np.frombuffer(raw[:pitch*h],np.uint8).reshape(h,pitch)
    po=ph['base']+struct.unpack_from('<I',d,ph['base']+ph['idxstart'])[0]
    assert ph['fmt']==3
    pal=np.frombuffer(d[po:po+4*ph['w']],np.uint8).reshape(-1,4)
    return arr[:, :w].copy(), pal.copy(), dict(lvl0=lvl0,pitch=pitch,order=ih['order'],w=w,h=h)
def write(d,k,idx):
    _,_,m=read(d,k); d=bytearray(d)
    full=np.zeros((m['h'],m['pitch']),np.uint8)
    # keep original padding bytes
    orig_raw=d[m['lvl0']:m['lvl0']+m['pitch']*((m['h']+7)&~7)]
    if m['order']==1:
        o=gim.unswizzle(bytes(orig_raw),m['pitch'],m['h']); full[:]=o
        full[:, :m['w']]=idx
        out=bytearray()
        for by in range((m['h']+7)//8):
            for bx in range(m['pitch']//16):
                out+=full[by*8:by*8+8,bx*16:bx*16+16].tobytes()
    else:
        full=np.frombuffer(bytes(orig_raw[:m['pitch']*m['h']]),np.uint8).reshape(m['h'],m['pitch']).copy()
        full[:, :m['w']]=idx; out=full.tobytes()
    d[m['lvl0']:m['lvl0']+len(out)]=out
    return bytes(d)
