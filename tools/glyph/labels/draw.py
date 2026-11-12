from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
SS=4
from gseed import fonts as _fonts
POPPINS=_fonts.path('poppins-bold')
INTER_B=_fonts.path('inter-bold')
INTER_SB=_fonts.path('inter-semibold')
_fc={}
def font(path,size):
    k=(path,size)
    if k not in _fc: _fc[k]=ImageFont.truetype(path,size)
    return _fc[k]
def _mask(text,path,size,H,baseline,stroke=0,xscale=1.0,pad=0):
    """render at SS x; returns (fill_mask, stroke_mask) float arrays (H, W) at 1x; width tight + pad"""
    f=font(path,size*SS)
    asc,desc=f.getmetrics()
    l,t,r,b=f.getbbox(text)
    W=int((r-l)+2*stroke*SS+2*pad*SS+SS*2)
    img=Image.new('L',(W,H*SS),0); st=Image.new('L',(W,H*SS),0)
    x=-l+stroke*SS+pad*SS+SS; y=baseline*SS-asc
    ImageDraw.Draw(img).text((x,y),text,font=f,fill=255)
    if stroke:
        ImageDraw.Draw(st).text((x,y),text,font=f,fill=255,stroke_width=int(stroke*SS),stroke_fill=255)
    nw=max(1,int(round(W/SS*xscale)))
    fm=np.asarray(img.resize((nw,H),Image.BOX),np.float32)/255
    sm=np.asarray(st.resize((nw,H),Image.BOX),np.float32)/255 if stroke else None
    return fm,sm
def outlined(text,path=POPPINS,size=21,H=27,baseline=21,stroke=2.6,fill=(255,255,255),edge=(0,150,255),xscale=1.0):
    fm,sm=_mask(text,path,size,H,baseline,stroke,xscale)
    # composite fill over stroke
    a=fm+sm*(1-fm)
    a=np.clip(a,0,1)
    rgb=np.zeros(fm.shape+(3,),np.float32)
    for c in range(3):
        num=fill[c]*fm+edge[c]*sm*(1-fm)
        rgb[...,c]=np.where(a>0,num/np.maximum(a,1e-6),0)
    out=np.dstack([rgb,a*255]).clip(0,255).astype(np.uint8)
    im=Image.fromarray(out,'RGBA')
    bb=im.getbbox()
    if bb: im=im.crop((bb[0],0,bb[2],H))
    return im
def plain(text,path=INTER_B,size=13,H=15,baseline=12,xscale=1.0,color=(255,255,255)):
    fm,_=_mask(text,path,size,H,baseline,0,xscale)
    a=(fm*255).astype(np.uint8)
    out=np.zeros(fm.shape+(4,),np.uint8); out[...,0]=color[0];out[...,1]=color[1];out[...,2]=color[2]; out[...,3]=a
    im=Image.fromarray(out,'RGBA'); bb=im.getbbox()
    if bb: im=im.crop((bb[0],0,bb[2],H))
    return im

def outlined_seq(text,path=POPPINS,size=23,H=28,baseline=20,stroke=2.6,track=1.5,fill=(255,255,255),edge=(0,150,255)):
    """Render text letter-by-letter with tracking; returns (img, xoff, adv) where img's left edge is at pen+xoff."""
    f=font(path,size*SS)
    asc,desc=f.getmetrics()
    # pen positions in SS units
    pens=[];p=0
    for ch in text:
        pens.append(p); p+=f.getlength(ch)+track*SS
    adv_ss=p-track*SS if text else 0
    margin=int((stroke+2)*SS)
    l=min(f.getbbox(ch)[0]+pens[i] for i,ch in enumerate(text))
    r=max(f.getbbox(ch)[2]+pens[i] for i,ch in enumerate(text))
    W=int(r-l)+2*margin
    W+=(-W)%SS
    ox=-l+margin
    fill_m=Image.new('L',(W,H*SS),0); st_m=Image.new('L',(W,H*SS),0)
    df=ImageDraw.Draw(fill_m); ds=ImageDraw.Draw(st_m)
    for i,ch in enumerate(text):
        x=ox+pens[i]; y=baseline*SS-asc
        df.text((x,y),ch,font=f,fill=255)
        ds.text((x,y),ch,font=f,fill=255,stroke_width=int(stroke*SS),stroke_fill=255)
    fm=np.asarray(fill_m.resize((W//SS,H),Image.BOX),np.float32)/255
    sm=np.asarray(st_m.resize((W//SS,H),Image.BOX),np.float32)/255
    a=np.clip(fm+sm*(1-fm),0,1)
    rgb=np.zeros(fm.shape+(3,),np.float32)
    for c in range(3):
        rgb[...,c]=np.where(a>0,(fill[c]*fm+edge[c]*sm*(1-fm))/np.maximum(a,1e-6),0)
    im=Image.fromarray(np.dstack([rgb,a*255]).clip(0,255).astype(np.uint8),'RGBA')
    bb=im.getbbox()
    x0=bb[0] if bb else 0; x1=bb[2] if bb else 1
    im=im.crop((x0,0,x1,H))
    xoff=x0-ox/SS
    return im,xoff,(adv_ss/SS)
