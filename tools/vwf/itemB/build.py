#!/usr/bin/env python3
"""Item B: centre the %y Yes/No labels in their highlight boxes. Requires item 2. Patch against eboot_v04.elf.
The %y handler calls 0x088FFC78(0, x, y) which puts the two cursor boxes at centres x+21 and x+91
(the original Yes label spans x..x+42 and the No label x+70..x+112).
  * label 1 starts at x+21-w1/2, label 2 at x+91-w2/2 (w = proportional width, VW_STRW from item 2)
  * VW_LW counts %y as 14 again, so the caller's +98 gives the original 112px block and the boxes keep their place"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,os,json,struct
H=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.dirname(H))
from masm import assemble,hi,lo
d=open(P.stage('eboot_v04.elf'),'rb').read()
def _expect(d,o,e):
    """e = 'sha1:<n>:<sha1 of the n original bytes at o>' (no original bytes stored) or '' (no check)."""
    if not e: return True
    _,n,h=e.split(':'); return hashlib.sha1(bytes(d[o:o+int(n)])).hexdigest()==h
def v2o(v): return v-0x8804000+0x54
L2=json.load(open(os.path.join(H,'..','item2','layout.json')))
STRW=int(L2['VW_STRW'],16); LW=int(L2['VW_LW'],16)
CAVE=0x89d71c0; END=0x89d7354
XSAVE=CAVE
src=f'''
  .word 0
VW_Y1:
  addiu $sp,$sp,-32
  sw $ra,0x10($sp)
  lui $at,{hi(XSAVE)}
  sw $s0,{lo(XSAVE)}($at)
  lui $v0,0x8a2
  lw $v0,0x7bc($v0)
  lw $s4,0($v0)
  jal {STRW}
  move $a0,$s4
  sra $v0,$v0,1
  subu $s0,$s0,$v0
  addiu $s0,$s0,21
  lw $ra,0x10($sp)
  jr $ra
  addiu $sp,$sp,32
VW_Y2:
  addiu $sp,$sp,-32
  sw $ra,0x10($sp)
  lui $v0,0x8a2
  lw $v0,0x7bc($v0)
  lw $s4,4($v0)
  jal {STRW}
  move $a0,$s4
  sra $v0,$v0,1
  lui $at,{hi(XSAVE)}
  lw $s0,{lo(XSAVE)}($at)
  subu $s0,$s0,$v0
  addiu $s0,$s0,{91-28}
  lw $ra,0x10($sp)
  jr $ra
  addiu $sp,$sp,32
'''
code,syms=assemble(src,CAVE); assert CAVE+len(code)<=END
patch=[]
def add(va,new,exp):
    o=v2o(va); assert _expect(d,o,exp),(hex(va),d[o:o+len(new)].hex())
    patch.append(dict(file_off=o,orig_sha1=hashlib.sha1(d[o:o+len(new)]).hexdigest(),new_hex=bytes(new).hex()))
def W(s,at=0): return assemble(s,at)[0]
add(CAVE,code,'')
add(0x88d1a38,W(f'jal {syms["VW_Y1"]}\nnop\nnop',0x88d1a38),'sha1:4:d796e5aa9aff9284b5779eaaba2b525be0331091')
add(0x88d1adc,W(f'jal {syms["VW_Y2"]}\nnop\nnop',0x88d1adc),'sha1:4:d796e5aa9aff9284b5779eaaba2b525be0331091')
add(LW+0x64,W('b 0x3c',LW+0x64),'sha1:4:cdc47469c068563f001d22390f000967a76e8621')   # 0x89d7124: bne a1,'y' -> b (count %y as 14)
json.dump(patch,open(os.path.join(H,'patch.json'),'w'),indent=0)
print({k:hex(v) for k,v in syms.items()},len(code))
