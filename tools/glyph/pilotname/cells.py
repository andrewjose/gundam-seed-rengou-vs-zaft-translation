import numpy as np
from PIL import Image, ImageDraw, ImageFont
SS=8
from gseed import fonts as _fonts
FONTS={'bold':'inter-bold','semi':'inter-semibold','med':'inter-medium','xbold':'inter-extrabold'}
GROUPS={
 # name: cell px, cap top row, cap height, font, outline(alpha 0..1 or 0)
 'G1':dict(p=14,top=1,cap=11,font='bold',outline=0.55,ocol=48),
 'G2':dict(p=14,top=3,cap=9,font='med',outline=0,ocol=0),
 'G3':dict(p=18,top=2,cap=14,font='semi',outline=0,ocol=0),
 'G4':dict(p=18,top=2,cap=14,font='xbold',outline=0.75,ocol=56),
}
_f={}
def fnt(name,size):
    k=(name,size)
    if k not in _f: _f[k]=ImageFont.truetype(_fonts.path(FONTS[name]),size)
    return _f[k]
def cell(ch,g):
    G=GROUPS[g]; p=G['p']
    # font size so that 'H' cap height == cap px
    size=int(round(G['cap']/0.727*SS))
    f=fnt(G['font'],size)
    capb=f.getbbox('H'); caph=capb[3]-capb[1]
    scale=(G['cap']*SS)/caph; size=int(round(size*scale)); f=fnt(G['font'],size); capb=f.getbbox('H')
    baseline=(G['top']+G['cap'])*SS
    l,t,r,b=f.getbbox(ch)
    W=p*SS
    img=Image.new('L',(W*2,p*SS),0); dr=ImageDraw.Draw(img)
    y=baseline-capb[3]
    if ch in 'gjpqy':
        desc=b-capb[3]; room=p*SS-baseline
        if desc>room: y-=min(desc-room, 1*SS+SS//2)
    dr.text((W//2-l,y),ch,font=f,fill=255)
    a=np.asarray(img)
    cols=np.where(a.max(0)>0)[0]
    x0,x1=cols.min(),cols.max()+1
    ink=a[:,x0:x1]
    maxw=(p-2)*SS if not G['outline'] else (p-2)*SS
    if ink.shape[1]>maxw:
        ink=np.asarray(Image.fromarray(ink).resize((maxw,ink.shape[0]),Image.LANCZOS))
    canvas=np.zeros((p*SS,W),np.uint8)
    xo=(W-ink.shape[1])//2
    canvas[:,xo:xo+ink.shape[1]]=ink
    fm=np.asarray(Image.fromarray(canvas).resize((p,p),Image.BOX),np.float32)/255
    if G['outline']:
        from scipy.ndimage import maximum_filter
        sm=maximum_filter(fm,size=3)*G['outline']
    else: sm=np.zeros_like(fm)
    a=np.clip(fm+sm*(1-fm),0,1)
    rgbv=np.where(a>0,(255*fm+G['ocol']*sm*(1-fm))/np.maximum(a,1e-6),0)
    out=np.zeros((p,p,4),np.uint8)
    out[...,0]=out[...,1]=out[...,2]=np.clip(rgbv,0,255).astype(np.uint8)
    out[...,3]=(a*255).astype(np.uint8)
    return out
