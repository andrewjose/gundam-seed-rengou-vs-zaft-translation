#!/usr/bin/env python3
"""Item 3: battle-dialogue VWF (single proportional glyphs) - replaces the pair-glyph scheme.
  * 0x08988C84 (line converter) rewritten: stores 0xFE + source string pointer in the 30-byte line buffer
  * 0x08988EDC (line drawer) rewritten in place: draws the ASCII string glyph by glyph, advance = (w+1)*12.5/14
  * width table (96 bytes) in the now-dead lookup 0x08988CD4
  * strings re-written in place (pair-alignment spaces removed); pool layout and pointers unchanged
  * atlas AFS 1677 sub 0: cells 0..95 (rows 0-5, 16x16) = ASCII 0x20..0x7F, glyph left-aligned at texel (+1,+1)
outputs: item3/patch.json, item3/afs_1677.bin, item3/report.txt"""
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
GAP=1; SPACE=4; SX=12.5/14; MAXW=187.5
# ---------- glyphs / widths
G={}; WT=bytearray(96)
for c in range(0x20,0x80):
    a,w=glyph(chr(c)) if c<0x7f else (np.zeros((14,0)),0)
    G[c]=a; WT[c-0x20]=w
WT[0]=SPACE
# ---------- text (in place)
T=load(BASE)
patch=[]; report=[]
def add(va,new,expect=None):
    o=v2o(va)
    if expect is not None: assert _expect(d,o,expect),(hex(va),d[o:o+len(new)].hex())
    patch.append(dict(file_off=o,orig_sha1=hashlib.sha1(d[o:o+len(new)]).hexdigest(),new_hex=bytes(new).hex()))
def width(s): return (sum((WT[ord(c)-0x20] if 0x20<=ord(c)<0x80 else SPACE)+GAP for c in s)-GAP)*SX if s else 0
over=[]
for x in T['dialogue']:
    cur=x['cur'].encode(); en=x['en'].encode()
    assert len(en)<=len(cur) and en.replace(b' ',b'')==cur.replace(b' ',b'')
    if en!=cur: add(x['va'],en+b'\0'*(len(cur)-len(en)))
    w=width(x['en'])
    if w>MAXW: over.append((w,x['id'],x['en']))
report.append('dialogue lines: %d, rewritten in place: %d, widest %.1f px (limit %.1f), over limit: %d'%(
    len(T['dialogue']),len(patch),max(width(x['en']) for x in T['dialogue']),MAXW,len(over)))
for w,i,e in over: report.append('  OVER %.1f id %d %r'%(w,i,e))
# ---------- code
WT_VA=0x8988cac
CONV=0x8988c84
assert hashlib.sha1(bytes(d[v2o(CONV):v2o(CONV)+4])).hexdigest()=='652cc28686d01d788a57c43fb9b6524a83c4106c' and hashlib.sha1(bytes(d[v2o(0x8988cd4):v2o(0x8988cd4)+4])).hexdigest()=='c48a8c05bf4e77b80685720c40cbba7e85b7667f'
conv_src='''
  addiu $v0,$zero,0xfe
  sb $v0,0($a0)
  sb $a1,1($a0)
  srl $v0,$a1,8
  sb $v0,2($a0)
  srl $v0,$a1,16
  sb $v0,3($a0)
  srl $v0,$a1,24
  jr $ra
  sb $v0,4($a0)
'''
conv,_=assemble(conv_src,CONV); assert CONV+len(conv)<=WT_VA
sxb=struct.unpack('<I',struct.pack('<f',SX))[0]
DRAW=0x8988edc
draw_src=f'''
VW_DLG:
  addiu $sp,$sp,-0xa0
  sw $ra,0x2c($sp)
  sw $s4,0x28($sp)
  sw $s3,0x24($sp)
  sw $s2,0x20($sp)
  sw $s1,0x1c($sp)
  sw $s0,0x18($sp)
  swc1 $f21,0x14($sp)
  swc1 $f20,0x10($sp)
  swc1 $f22,0x0c($sp)
  lui $v0,0x8080
  ori $v0,$v0,0x8080
  sw $v0,0x70($sp)
  addiu $v0,$zero,2
  sw $v0,0x80($sp)
  addiu $v0,$zero,0xc
  sh $v0,0x84($sp)
  addiu $v0,$zero,1
  sb $v0,0x88($sp)
  mov.s $f21,$f12
  mov.s $f20,$f13
  lui $v0,{sxb>>16}
  ori $v0,$v0,{sxb&0xffff}
  mtc1 $v0,$f22
  seh $s3,$a0
  sll $s3,$s3,1
  slti $v0,$s3,30
  bnez $v0,1f
  nop
  addiu $s3,$zero,0x7fff
1:
  move $s1,$zero
  addiu $s4,$zero,1
  lbu $v0,0($a1)
  addiu $v1,$zero,0xfe
  bne $v0,$v1,9f
  nop
  lbu $s2,1($a1)
  lbu $v0,2($a1)
  sll $v0,$v0,8
  or $s2,$s2,$v0
  lbu $v0,3($a1)
  sll $v0,$v0,16
  or $s2,$s2,$v0
  lbu $v0,4($a1)
  sll $v0,$v0,24
  or $s2,$s2,$v0
  move $s4,$zero
2:
  slt $v0,$s1,$s3
  beqz $v0,9f
  nop
  lbu $s0,0($s2)
  beqz $s0,7f
  addiu $s2,$s2,1
  addiu $s0,$s0,-0x20
  sltiu $v0,$s0,96
  bnez $v0,3f
  nop
  move $s0,$zero
3:
  lui $v0,{hi(WT_VA)}
  addu $v0,$v0,$s0
  lbu $t1,{lo(WT_VA)}($v0)
  beqz $s0,5f
  nop
  mtc1 $t1,$f0
  cvt.s.w $f0,$f0
  mul.s $f0,$f0,$f22
  add.s $f1,$f21,$f0
  swc1 $f21,0x30($sp)
  swc1 $f20,0x34($sp)
  swc1 $f1,0x40($sp)
  lui $v0,0x4150
  mtc1 $v0,$f0
  add.s $f0,$f0,$f20
  swc1 $f0,0x44($sp)
  lui $v0,0x3f80
  sw $v0,0x38($sp)
  sw $v0,0x48($sp)
  addiu $v0,$sp,0x30
  sw $v0,0x64($sp)
  addiu $v0,$sp,0x98
  sw $v0,0x78($sp)
  sw $zero,0x68($sp)
  lui $v0,0x8ed
  lbu $v0,-0x5f98($v0)
  sll $v0,$v0,2
  lui $v1,0x8ed
  addu $v1,$v1,$v0
  lw $v1,-0x1664($v1)
  sw $v1,0x7c($sp)
  andi $v0,$s0,15
  sll $v0,$v0,4
  addiu $v0,$v0,1
  sh $v0,0x98($sp)
  addu $v0,$v0,$t1
  sh $v0,0x9c($sp)
  srl $v1,$s0,4
  sll $v1,$v1,4
  addiu $v1,$v1,1
  sh $v1,0x9a($sp)
  addiu $v1,$v1,14
  sh $v1,0x9e($sp)
  sw $t1,0x08($sp)
  jal 0x8902694
  addiu $a0,$sp,0x50
  lw $t1,0x08($sp)
5:
  addiu $t1,$t1,{GAP}
  mtc1 $t1,$f0
  cvt.s.w $f0,$f0
  mul.s $f0,$f0,$f22
  add.s $f21,$f21,$f0
  b 2b
  addiu $s1,$s1,1
7:
  addiu $s4,$zero,1
9:
  bnez $s4,10f
  addiu $v0,$zero,1
  addiu $v1,$s3,-1
  slt $v1,$s1,$v1
  xori $v0,$v1,1
10:
  lw $ra,0x2c($sp)
  lw $s4,0x28($sp)
  lw $s3,0x24($sp)
  lw $s2,0x20($sp)
  lw $s1,0x1c($sp)
  lw $s0,0x18($sp)
  lwc1 $f21,0x14($sp)
  lwc1 $f20,0x10($sp)
  lwc1 $f22,0x0c($sp)
  jr $ra
  addiu $sp,$sp,0xa0
'''
draw,syms=assemble(draw_src,DRAW)
DRAW_END=0x89890e4
print('drawer',len(draw),'bytes of',DRAW_END-DRAW)
assert DRAW+len(draw)<=DRAW_END
draw=draw+b'\0'*0  # keep remaining old bytes untouched
add(CONV,conv,'sha1:24:819949738d88c7acf05d0f86ab136caff3465bef')
add(WT_VA,bytes(WT))
assert WT_VA+96<=0x8988d40
add(DRAW,draw,'sha1:8:0441fb5cf7d98c52daf518cf790287e2f98fafd2')
# ---------- atlas
from atlas_vwf import original_entry
orig_entry=original_entry(1677)   # v0.4 was built on the pair-glyph atlas; only cells 0..95 are used now
subs,_=packmod.parse(orig_entry)
g=lz.decompress(subs[0]['raw']) if subs[0]['flags']&1 else subs[0]['raw']
idx,pal=gimtex.read_indices(g)
used=np.unique(idx)
cand=sorted(set(int(i) for i in used),key=lambda i:pal[i][3])
alphas=np.array([pal[i][3] for i in cand],float)
lut=np.array([cand[int(np.argmin(abs(alphas-a)))] for a in range(256)],np.uint8)
idx=idx.copy()
for c in range(0x20,0x80):
    k=c-0x20; r,col=divmod(k,16)
    cell=np.zeros((16,16),np.float32)
    a=G[c]
    if a.shape[1]: cell[1:15,1:1+a.shape[1]]=a
    idx[r*16:(r+1)*16,col*16:(col+1)*16]=lut[np.clip(cell*255+0.5,0,255).astype(np.uint8)]
g2=gimtex.write_indices(g,idx)
newentry=repack.rebuild_pack(orig_entry,{0:g2})
open(P.ensure(P.work('vwf','afs_1677.bin')),'wb').write(newentry)
json.dump(patch,open(os.path.join(HERE,'patch.json'),'w'),indent=0)
json.dump(dict(widths=list(WT),gap=GAP,space=SPACE,sx=SX,draw=hex(DRAW),conv=hex(CONV),wt=hex(WT_VA)),open(os.path.join(HERE,'layout.json'),'w'))
report.append('patches: %d; atlas AFS 1677 sub 0 rows 0-5 replaced (single glyphs); entry %d -> %d bytes'%(len(patch),len(orig_entry),len(newentry)))
open(P.ensure(P.work('vwf','report.txt')),'w').write('\n'.join(report)+'\n'); print('\n'.join(report))
