"""Single proportional glyphs for the dialogue/tutorial atlases (same face/size as the old pair glyphs)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from gseed import fonts as _fonts
FONT=_fonts.path('dejavu-cond-bold')
SS=8
def glyph(ch, h=14, size_px=12.0, base_y=11.0, maxw=14):
    """-> (alpha float array (h, w), ink width w). Ink left-aligned at x=0."""
    if ch==' ': return np.zeros((h,0)),0
    f=ImageFont.truetype(FONT,int(round(size_px*SS)))
    W=40*SS; im=Image.new('L',(W,h*SS),0); d=ImageDraw.Draw(im)
    d.text((4*SS, base_y*SS), ch, font=f, fill=255, anchor='ls')
    a=np.asarray(im,np.float32)/255
    cols=np.where(a.max(0)>0.02)[0]
    if len(cols)==0: return np.zeros((h,0)),0
    x0=cols[0]; x1=cols[-1]+1
    # snap the ink box to whole texels: keep sub-texel position of the left edge at 0
    wpx=int(np.ceil((x1-x0)/SS))
    wpx=min(wpx,maxw)
    crop=a[:,x0:x0+wpx*SS]
    if crop.shape[1]<wpx*SS: crop=np.pad(crop,((0,0),(0,wpx*SS-crop.shape[1])))
    small=np.asarray(Image.fromarray((crop*255).astype(np.uint8)).resize((wpx,h),Image.BOX),np.float32)/255
    return small,wpx
