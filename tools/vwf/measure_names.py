import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,numpy as np
import gimm
KB=("ABCDEFGHIJ" "KLMNOPQRST" "UVWXYZabcd" "efghij*k*l" "mnopqrstuv" "wxyz.-'!?")
COPIES=[(2,2,0,14,0,'disp'),(134,1,5,14,0,'disp'),(124,1,0,14,0,'disp'),(129,1,1,14,0,'disp'),
 (11,1,1,18,0,'kbd'),(130,1,0,18,0,'kbd'),(135,1,3,18,0,'disp'),(137,1,0,18,54,'disp'),(138,1,0,18,54,'disp')]
def cells():
    out=[]
    for i,ch in enumerate(KB):
        if ch!='*': out.append((i//10,i%10,ch))
    for n in range(10): out.append((6,n,str(n)))
    return out
def measure(thr=40):
    res={}
    for afs,sub,k,p,y0,mode in COPIES:
        d=open(P.work('glyph','pn')+'/%d_%d.bin'%(afs,sub),'rb').read()
        idx,pal,m=gimm.read(d,k); a=pal[idx][...,3]
        for r,c,ch in cells():
            if mode=='kbd' and r==6: continue
            blk=a[y0+r*p:y0+r*p+p, c*p:c*p+p]
            cols=np.where(blk.max(0)>thr)[0]
            if len(cols)==0: continue
            res.setdefault(ch,{})[(afs,p)]=(cols.min(),cols.max()+1)
    return res
if __name__=='__main__':
    r=measure()
    for ch in sorted(r): print(ch, {k:(v[1]-v[0],v[0]) for k,v in r[ch].items()})
