import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys
import pmf
from PIL import Image, ImageDraw
SX=15/1156.; SY=19/7658.
def quads(r):
    out=[];i=0
    for t,n in r['prims']:
        vs=r['verts'][i:i+n]; i+=n
        us=[v[0] for v in vs]; vv=[v[1] for v in vs]; xs=[v[2] for v in vs]; ys=[v[3] for v in vs]
        out.append(dict(u0=min(us),u1=max(us),v0=min(vv),v1=max(vv),x0=min(xs),x1=max(xs),y0=min(ys),y1=max(ys),vs=vs,n=n))
    return out
def render(r,tex,sx=SX,sy=SY,bg=(0,0,60,255)):
    qs=quads(r); W,H=tex.size
    x0=min(q['x0'] for q in qs);x1=max(q['x1'] for q in qs);y0=min(q['y0'] for q in qs);y1=max(q['y1'] for q in qs)
    im=Image.new('RGBA',(int((x1-x0)*sx)+4,int((y1-y0)*sy)+4),bg)
    for q in qs:
        crop=tex.crop((int(q['u0']*W/32768),int(q['v0']*H/32768),int(round(q['u1']*W/32768)),int(round(q['v1']*H/32768))))
        tw=max(1,round((q['x1']-q['x0'])*sx)); th=max(1,round((q['y1']-q['y0'])*sy))
        crop=crop.resize((tw,th))
        im.alpha_composite(crop,(round((q['x0']-x0)*sx)+2,round((y1-q['y1'])*sy)+2))
    return im
def sheet(path_pmf,tex,out,sx=SX,sy=SY,cols=2):
    d=open(path_pmf,'rb').read()
    ims=[]
    for o in pmf.objects(d):
        r=pmf.parse_obj(d,o); ims.append((r['name'],render(r,tex,sx,sy)))
    W=max(i.size[0] for n,i in ims)+90; H=sum(i.size[1]+2 for n,i in ims)
    big=Image.new('RGB',(W*cols,H//cols+60),(40,40,40)); dr=ImageDraw.Draw(big); y=0;x=0
    for n,i in ims:
        if y+i.size[1]>big.size[1]: y=0;x+=W
        dr.text((x,y),n,fill=(255,255,0)); big.paste(i,(x+90,y)); y+=i.size[1]+2
    big.save(out); return big.size
