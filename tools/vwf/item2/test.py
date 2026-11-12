import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,json,struct; from emu import *
from PIL import ImageFont
F=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
def metrics(ch):
    if ch==' ': return 0,0
    l,t,r,b=F.getbbox(ch); return l,r-l
def run(elf,lines,x=-1):
    e=Emu(elf); END=0x8804000; calls=[]
    def glyph(e):
        s=e.rd(e.r('a0'),2); ch=chr(s[0]) if s[0]<0x80 else '?'
        l,w=metrics(ch); e.wr(e.r('a2'),struct.pack('<iii',l,w,0)); e.w('v0',1); e.ret()
    def draw(e):
        a0=e.r('a0'); mode=e.r('a1')
        ch=chr(a0) if mode==0 else ('<%04x>'%a0)
        calls.append((ch,mode,e.r('a3')- (1<<32 if e.r('a3')>>31 else 0))); e.ret()
    e.hooks={0x8979f40:glyph,0x88d1bdc:draw}
    T=0x9e00000; ptrs=[]
    for i,l in enumerate(lines):
        a=T+0x100*(i+1); e.wr(a,l+b'\0'); ptrs.append(a)
    e.wr(T,struct.pack('<%dI'%(len(ptrs)+1),*ptrs,0))
    e.wr(0x8a207b4+4*5,struct.pack('<I',T))
    e.w('sp',0x9f00000); e.w('ra',END); e.w('a0',5); e.w('a1',x&0xffffffff); e.w('a2',100); e.w('a3',0x80)
    e.run(0x88d15e8,END,count=5000000)
    return calls
if __name__=='__main__':
    base=open(P.stage('eboot_v03d.elf'),'rb').read()
    pat=apply(P.stage('eboot_v03d.elf'),[os.path.join(P.TOOLS,'vwf','item2','patch.json')])
    L=[b'System data found. Overwrite?',b'%y']
    for tag,elf in (('orig',base),('new',pat)):
        c=run(elf,L)
        print(tag,[(a,x) for a,m,x in c])
    from PIL import Image,ImageDraw
    Fs=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
    Fj=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',14) if __import__('os').path.exists('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc') else Fs
    img=Image.new('RGB',(480,200),(20,30,80)); dr=ImageDraw.Draw(img)
    dr.rectangle((60,20,420,180),outline=(200,200,200))
    for row,(tag,elf) in enumerate((('orig',base),('new',pat))):
        c=run(elf,L)
        y0=40+row*70; line=0; prev=1e9
        for ch,m,x in c:
            if x<prev-60: line+=0
            yy=y0+(0 if ch.isascii() and m==0 and len(ch)==1 and c.index((ch,m,x))<29 else 20)
            if m==0:
                if tag=='orig':
                    g=Image.new('L',(14,18),0); ImageDraw.Draw(g).text((0,0),ch,font=Fs,fill=255)
                    g=g.resize((7,18)); img.paste((255,255,255),(x,yy),g)
                else: dr.text((x,yy),ch,font=Fs,fill=(255,255,255))
            else:
                dr.text((x,yy),bytes.fromhex(ch[1:5]).decode('cp932'),font=Fj,fill=(255,255,255))
        dr.text((4,y0),tag,fill=(255,255,0))
    dr.line((240,20,240,180),fill=(255,0,0))
    img.resize((960,400),Image.NEAREST).save(P.ensure(P.work('preview','preview_msgbox.png')))
