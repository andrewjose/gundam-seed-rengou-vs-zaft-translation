import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,struct,glob
import gim,pmf,render
from PIL import Image, ImageDraw
def textures(afs):
    tex=[]
    subs=sorted(glob.glob(P.unpacked()+'/%d_*.bin'%afs),key=lambda p:int(p.split('_')[-1][:-4]) if p.split('_')[-1][:-4].isdigit() else 999)
    for p in subs:
        d=open(p,'rb').read()
        if d[:4]==b'MIG.':
            for ih,im in gim.images(d): tex.append(im.convert('RGBA'))
    return tex
def go(afs,sub,out,cols=3):
    tex=textures(afs)
    d=open(P.unpacked()+'/%d_%d.bin'%(afs,sub),'rb').read()
    sx,sy=struct.unpack_from('<2f',d,0x10)
    ims=[]
    for o in pmf.objects(d):
        r=pmf.parse_obj(d,o); t,=struct.unpack_from('<I',d,o+0x74)
        if t>=len(tex): continue
        T=tex[t]
        # scale raw->texel guess: 1 world unit ~ 1.67 texel ; raw->world = s/32768
        k=1.0
        try: ims.append((r['name']+' t%d'%t,render.render(r,T,sx/32768*k,sy/32768*k)))
        except Exception as e: print(r['name'],e)
    W=min(600,max(i.size[0] for n,i in ims))+110; H=sum(min(i.size[1],300)+2 for n,i in ims)
    big=Image.new('RGB',(W*cols,H//cols+300),(40,40,40)); dr=ImageDraw.Draw(big); y=0;x=0
    for n,i in ims:
        i=i.crop((0,0,min(600,i.size[0]),min(300,i.size[1])))
        if y+i.size[1]>big.size[1]: y=0;x+=W
        dr.text((x,y),n,fill=(255,255,0)); big.paste(i,(x+110,y)); y+=i.size[1]+2
    big.save(out); print(out,big.size,len(ims))
if __name__=='__main__':
    go(int(sys.argv[1]),int(sys.argv[2]),sys.argv[3],int(sys.argv[4]) if len(sys.argv)>4 else 3)
