import numpy as np
from PIL import Image
def quantize(rgba, n=256):
    """returns idx (H,W) uint8, pal (n,4) uint8. Fully transparent pixels -> palette entry 0 = (0,0,0,0)."""
    im=Image.fromarray(rgba,'RGBA')
    q=im.quantize(colors=n-1,method=Image.Quantize.FASTOCTREE,dither=Image.Dither.NONE)
    p=np.array(q.getpalette(rawmode='RGBA')[:4*(n-1)],np.uint8).reshape(-1,4)
    pal=np.vstack([np.zeros((1,4),np.uint8),p])
    idx=np.asarray(q,np.uint8).astype(np.int32)+1
    idx[rgba[...,3]==0]=0
    # refine: nearest palette entry in premultiplied space for each unique color
    flat=rgba.reshape(-1,4).astype(np.int32)
    uniq,inv=np.unique(flat,axis=0,return_inverse=True)
    def pm(c): c=c.astype(np.float32); return np.concatenate([c[:,:3]*c[:,3:4]/255,c[:,3:4]],1)
    U=pm(uniq); P=pm(pal)
    best=np.empty(len(uniq),np.int32)
    for i in range(0,len(uniq),2048):
        dd=((U[i:i+2048,None,:]-P[None,:,:])**2).sum(-1); best[i:i+2048]=dd.argmin(1)
    best[uniq[:,3]==0]=0
    idx=best[inv.ravel()].reshape(rgba.shape[:2]).astype(np.uint8)
    err=np.abs(pm(pal[idx.ravel()])-pm(flat)).max()
    return idx,pal,err
