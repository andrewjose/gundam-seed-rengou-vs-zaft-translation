"""In-place GIM (single 8bpp indexed swizzled image) read/write for 12_1 / 140_1."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,struct,numpy as np
import gim
def info(d):
    out={}
    for bid,off,size,nxt,dat in gim.blocks(d,0x10,len(d)):
        if bid==4: out['img']=gim.parse_img_hdr(d,off+dat)
        if bid==5: out['pal']=gim.parse_img_hdr(d,off+dat)
    return out
def read(d):
    I=info(d); ih=I['img']; ph=I['pal']
    assert ih['fmt']==5 and ih['order']==1
    w,h=ih['w'],ih['h']
    lvl0=ih['base']+struct.unpack_from('<I',d,ih['base']+ih['idxstart'])[0]
    idx=gim.unswizzle(d[lvl0:lvl0+w*h],w,h)
    po=ph['base']+struct.unpack_from('<I',d,ph['base']+ph['idxstart'])[0]
    pal=gim.conv(d[po:],ph['fmt'],ph['w'])
    return idx.copy(),pal.copy(),dict(lvl0=lvl0,po=po,pfmt=ph['fmt'],pw=ph['w'],w=w,h=h)
def swizzle(arr):
    h,wb=arr.shape; out=bytearray()
    for by in range((h+7)//8):
        for bx in range(wb//16):
            blk=arr[by*8:by*8+8,bx*16:bx*16+16]
            out+=blk.astype(np.uint8).tobytes()
    return bytes(out)
def write(d,idx,pal=None):
    _,_,m=read(d); d=bytearray(d)
    s=swizzle(idx); d[m['lvl0']:m['lvl0']+len(s)]=s
    if pal is not None:
        assert m['pfmt']==3
        d[m['po']:m['po']+4*len(pal)]=np.asarray(pal,np.uint8).tobytes()
    return bytes(d)
