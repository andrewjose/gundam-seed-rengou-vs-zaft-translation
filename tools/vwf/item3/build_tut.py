#!/usr/bin/env python3
"""Item 3b: tutorial-caption VWF (0x089C1788 setup / 0x089C1850 converter / 0x089C1A88 drawer, atlas AFS 10 sub 1 img 0).
  * 0x089C1850 rewritten: stores 0xFE + string pointer in the 50-byte line buffer, returns char count and
    writes the line width in 7-unit steps to *a2 (used unchanged by the centring code in 0x089C1980)
  * width table in the dead lookup 0x089C18E4
  * 0x089C1A88 rewritten in place: draws each ASCII glyph with the game's 14x14 cell model (+0x960), glyph
    left-aligned in its cell, pen += (w+1) * scale
  * strings re-written in place (pair-alignment spaces removed)
  * atlas cells 0..95 (13 per row, 14x14) = ASCII 0x20..0x7F, glyph at x=+1
outputs: item3/patch_tut.json, item3/afs_10.bin"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,os,json,struct
import numpy as np
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path[:0]=[HERE]
from masm import assemble,hi,lo
from glyphs1 import glyph
from text import load
import gimtex, repack, pack as packmod, lz
BASE=P.stage('eboot_v03d.elf')
d=open(BASE,'rb').read()
def _expect(d,o,e):
    """e = 'sha1:<n>:<sha1 of the n original bytes at o>' (no original bytes stored) or '' (no check)."""
    if not e: return True
    _,n,h=e.split(':'); return hashlib.sha1(bytes(d[o:o+int(n)])).hexdigest()==h
def v2o(v): return v-0x8804000+0x54
GAP=1; SPACE=4; MAXW=350
G={}; WT=bytearray(96)
for c in range(0x20,0x80):
    a,w=glyph(chr(c),maxw=13) if c<0x7f else (np.zeros((14,0)),0)
    G[c]=a; WT[c-0x20]=w
WT[0]=SPACE
T=load(BASE)
patch=[]; report=[]
def add(va,new,expect=None):
    o=v2o(va)
    if expect is not None: assert _expect(d,o,expect),(hex(va),d[o:o+len(new)].hex())
    patch.append(dict(file_off=o,orig_sha1=hashlib.sha1(d[o:o+len(new)]).hexdigest(),new_hex=bytes(new).hex()))
def width(s): return sum(WT[ord(c)-0x20]+GAP for c in s)-GAP if s else 0
for x in T['tutorial']:
    cur=x['cur'].encode(); en=x['en'].encode()
    assert len(en)<=len(cur) and en.replace(b' ',b'')==cur.replace(b' ',b'')
    if en!=cur: add(x['va'],en+b'\0'*(len(cur)-len(en)))
ws=[(width(x['en']),x) for x in T['tutorial']]
report.append('tutorial lines: %d, rewritten: %d, widest %d px (limit %d), over: %s'%(len(ws),len(patch),max(w for w,_ in ws),MAXW,[x['id'] for w,x in ws if w>MAXW]))
CONV=0x89c1850; WT_VA=0x89c18e4; DRAW=0x89c1a88; DRAW_END=0x89c1c40
conv_src=f'''
  addiu $v0,$zero,0xfe
  sb $v0,0($a0)
  sb $a1,1($a0)
  srl $v0,$a1,8
  sb $v0,2($a0)
  srl $v0,$a1,16
  sb $v0,3($a0)
  srl $v0,$a1,24
  sb $v0,4($a0)
  move $t0,$a1
  move $t1,$zero
  move $v0,$zero
1:
  lbu $t2,0($t0)
  beqz $t2,3f
  addiu $t0,$t0,1
  addiu $t2,$t2,-0x20
  sltiu $t3,$t2,96
  bnez $t3,2f
  nop
  move $t2,$zero
2:
  lui $t3,{hi(WT_VA)}
  addu $t3,$t3,$t2
  lbu $t3,{lo(WT_VA)}($t3)
  addu $t1,$t1,$t3
  addiu $t1,$t1,{GAP}
  b 1b
  addiu $v0,$v0,1
3:
  beqz $v0,4f
  nop
  addiu $t1,$t1,-{GAP}
4:
  addiu $t1,$t1,3
  addiu $t3,$zero,7
  divu $zero,$t1,$t3
  mflo $t1
  jr $ra
  sb $t1,0($a2)
'''
conv,_=assemble(conv_src,CONV); assert CONV+len(conv)<=WT_VA,len(conv)
draw_src=f'''
  addiu $sp,$sp,-0xb0
  sw $ra,0xc($sp)
  sw $s2,8($sp)
  sw $s1,4($sp)
  sw $s0,0($sp)
  move $s0,$a0
  move $s2,$a1
  lui $v0,0x3f80
  sw $v0,0x50($sp)
  sw $v0,0x54($sp)
  sw $v0,0x58($sp)
  sw $zero,0x5c($sp)
  addiu $a0,$sp,0x70
  jal 0x8848de0
  addiu $a1,$sp,0x50
  move $a1,$s0
  jal 0x89c0964
  addiu $a0,$sp,0x60
  lbu $v0,0($s2)
  addiu $v1,$zero,0xfe
  bne $v0,$v1,9f
  nop
  lbu $s0,1($s2)
  lbu $v0,2($s2)
  sll $v0,$v0,8
  or $s0,$s0,$v0
  lbu $v0,3($s2)
  sll $v0,$v0,16
  or $s0,$s0,$v0
  lbu $v0,4($s2)
  sll $v0,$v0,24
  or $s0,$s0,$v0
1:
  lbu $s1,0($s0)
  beqz $s1,9f
  addiu $s0,$s0,1
  addiu $s1,$s1,-0x20
  sltiu $v0,$s1,96
  bnez $v0,2f
  nop
  move $s1,$zero
2:
  beqz $s1,5f
  nop
  addiu $a0,$sp,0x10
  addiu $a1,$sp,0x70
  jal 0x88483a8
  addiu $a2,$sp,0x60
  addiu $a3,$zero,1
  lui $v0,0x8ed
  sb $a3,-0x2ede($v0)
  addiu $v0,$zero,13
  divu $zero,$s1,$v0
  mfhi $a2
  mflo $a0
  mtc1 $a2,$f2
  cvt.s.w $f2,$f2
  lui $v0,0x4160
  mtc1 $v0,$f3
  mul.s $f2,$f3,$f2
  lui $v0,0x4380
  mtc1 $v0,$f1
  div.s $f1,$f2,$f1
  lui $v1,0x8ed
  swc1 $f1,-0x2ef0($v1)
  mtc1 $a0,$f1
  cvt.s.w $f1,$f1
  mul.s $f1,$f3,$f1
  lui $v0,0x4400
  mtc1 $v0,$f0
  div.s $f0,$f1,$f0
  lui $v0,0x8ed
  swc1 $f0,-0x2eec($v0)
  lui $v0,0x8ed
  lw $v0,-0x175c($v0)
  lui $a2,0x8ed
  addiu $a1,$sp,0x10
  addiu $a2,$a2,-0x2f00
  addiu $a0,$v0,0x960
  jal 0x8903178
  addiu $a3,$zero,8
5:
  lui $v0,{hi(WT_VA)}
  addu $v0,$v0,$s1
  lbu $v0,{lo(WT_VA)}($v0)
  addiu $v0,$v0,{GAP}
  mtc1 $v0,$f1
  cvt.s.w $f1,$f1
  lwc1 $f0,0x50($sp)
  mul.s $f0,$f1,$f0
  lwc1 $f2,0x60($sp)
  add.s $f0,$f2,$f0
  b 1b
  swc1 $f0,0x60($sp)
9:
  lui $v1,0x8ed
  sb $zero,-0x2ede($v1)
  lui $v1,0x8ed
  sw $zero,-0x2eec($v1)
  lui $v1,0x8ed
  sw $zero,-0x2ef0($v1)
  lw $ra,0xc($sp)
  lw $s2,8($sp)
  lw $s1,4($sp)
  lw $s0,0($sp)
  jr $ra
  addiu $sp,$sp,0xb0
'''
draw,_=assemble(draw_src,DRAW); print('drawer',len(draw),'of',DRAW_END-DRAW); assert DRAW+len(draw)<=DRAW_END
add(CONV,conv,'sha1:8:efd1082f620f7c7578854b1e01b1a3bfda986f90')
add(WT_VA,bytes(WT),'sha1:4:3488c7ac741aafbf32d2b99240bc11238a015d35'); assert WT_VA+96<=0x89c1980
add(DRAW,draw,'sha1:8:da3236ec9d5184b46d81782e26d0855ff67075b2')
# atlas
orig_entry=open(P.afs_new(10),'rb').read()
subs,_=packmod.parse(orig_entry)
g=lz.decompress(subs[1]['raw']) if subs[1]['flags']&1 else subs[1]['raw']
idx,pal=gimtex.read_indices(g,0)
reg=idx[0:12*14,0:13*14]
cand=sorted(set(int(i) for i in np.unique(reg)),key=lambda i:pal[i][3])
alphas=np.array([pal[i][3] for i in cand],float)
lut=np.array([cand[int(np.argmin(abs(alphas-a)))] for a in range(256)],np.uint8)
idx=idx.copy()
for c in range(0x20,0x80):
    k=c-0x20; r,col=divmod(k,13)
    cell=np.zeros((14,14),np.float32); a=G[c]
    if a.shape[1]: cell[:,1:1+a.shape[1]]=a
    idx[r*14:(r+1)*14,col*14:(col+1)*14]=lut[np.clip(cell*255+0.5,0,255).astype(np.uint8)]
g2=gimtex.write_indices(g,idx,0)
newentry=repack.rebuild_pack(orig_entry,{1:g2})
open(P.ensure(P.work('vwf','afs_10.bin')),'wb').write(newentry)
json.dump(patch,open(os.path.join(HERE,'patch_tut.json'),'w'),indent=0)
report.append('tutorial patches: %d; AFS 10 entry %d -> %d bytes (base xd/img/afs/afs_10.bin)'%(len(patch),len(orig_entry),len(newentry)))
open(P.ensure(P.work('vwf','report_tut.txt')),'w').write('\n'.join(report)+'\n'); print('\n'.join(report))
