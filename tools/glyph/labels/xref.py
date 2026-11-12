import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import pickle,sys
ins=pickle.load(open(P.work('glyph','ins.pkl'),'rb'))
BASE=0x08804000
def xref(target,win=8,slop=0):
    hi=(target+0x8000)>>16; lo=target&0xffff
    res=[]
    for i,w in enumerate(ins):
        if (w>>26)==0xf and (w&0xffff)==hi:
            rt=(w>>16)&31
            for j in range(i+1,min(len(ins),i+win)):
                v=ins[j]; op=v>>26
                if op in (0x9,0x23,0x21,0x25,0x20,0x24,0x2b,0x29,0x28,0x31,0x39) and ((v>>21)&31)==rt:
                    imm=v&0xffff
                    if imm>=0x8000: imm-=0x10000
                    full=(hi<<16)+imm
                    if target-slop<=full<=target+slop: res.append((BASE+4*j,full))
    return res
if __name__=='__main__':
    t=int(sys.argv[1],16); s=int(sys.argv[2],16) if len(sys.argv)>2 else 0
    for a,f in xref(t,12,s): print(hex(a),hex(f))
