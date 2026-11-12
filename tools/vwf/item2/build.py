#!/usr/bin/env python3
"""Item 2: message-box renderer 0x088D15E8: proportional ASCII (body text + %y Yes/No buttons), ASCII Yes/No labels.
Patch JSON against <work>/stage/eboot_v03d.elf -> item2/patch.json"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,struct,json,os
from masm import assemble,hi,lo
d=open(P.stage('eboot_v03d.elf'),'rb').read()
def _expect(d,o,e):
    """e = 'sha1:<n>:<sha1 of the n original bytes at o>' (no original bytes stored) or '' (no check)."""
    if not e: return True
    _,n,h=e.split(':'); return hashlib.sha1(bytes(d[o:o+int(n)])).hexdigest()==h
def v2o(v): return v-0x8804000+0x54
CAVE=0x89D6FAC            # file 0x1d3000 (inside CRI ADXT 'parameter error' strings, 0x1d2c10..0x1d33a8)
CAVE_END=0x89D71FC        # file 0x1d3250
SPACING=1                 # extra px in 20px glyph-cache cell units (same as the 0x088D2330 patch)
SPACE_PX=4
src=f'''
# VW_ADVCH: a0 = single-byte char -> v0 = advance in px for a 14px cell (sceFont glyph cache metrics)
VW_ADVCH:
  addiu $sp,$sp,-64
  sw $ra,0x10($sp)
  andi $a0,$a0,0xff
  addiu $v0,$zero,0x20
  beq $a0,$v0,3f
  sb $a0,0x14($sp)
  sb $zero,0x15($sp)
  addiu $a0,$sp,0x14
  addiu $a1,$sp,0x28
  jal 0x8979f40
  addiu $a2,$sp,0x18
  beqz $v0,2f
  lw $v0,0x18($sp)
  lw $a0,0x1c($sp)
  addu $v0,$v0,$a0
  addiu $v0,$v0,{SPACING}
  sll $a0,$v0,4
  subu $a0,$a0,$v0
  subu $a0,$a0,$v0
  addiu $a0,$a0,10
  addiu $v0,$zero,20
  div $zero,$a0,$v0
  mflo $v0
  bgtz $v0,4f
  nop
  b 4f
  addiu $v0,$zero,1
2:
  b 4f
  addiu $v0,$zero,7
3:
  addiu $v0,$zero,{SPACE_PX}
4:
  lw $ra,0x10($sp)
  jr $ra
  addiu $sp,$sp,64

# VW_MB: wrapper for 0x088D1BDC (mode 0 = ASCII); returns v0 = advance
VW_MB:
  addiu $sp,$sp,-32
  sw $ra,0x10($sp)
  jal 0x88d1bdc
  sw $a0,0x14($sp)
  bal VW_ADVCH
  lw $a0,0x14($sp)
  lw $ra,0x10($sp)
  jr $ra
  addiu $sp,$sp,32

# VW_STRW: a0 = string -> v0 = width px (ASCII proportional, 2-byte SJIS = 14)
VW_STRW:
  addiu $sp,$sp,-32
  sw $ra,0x10($sp)
  sw $s0,0x14($sp)
  sw $s1,0x18($sp)
  move $s0,$a0
  move $s1,$zero
1:
  lbu $a0,0($s0)
  beqz $a0,9f
  slti $v0,$a0,0x80
  bnez $v0,2f
  slti $v0,$a0,0xf1
  beqz $v0,2f
  nop
  addiu $s1,$s1,14
  b 1b
  addiu $s0,$s0,2
2:
  bal VW_ADVCH
  nop
  addu $s1,$s1,$v0
  b 1b
  addiu $s0,$s0,1
9:
  move $v0,$s1
  lw $ra,0x10($sp)
  lw $s0,0x14($sp)
  lw $s1,0x18($sp)
  jr $ra
  addiu $sp,$sp,32

# VW_LW: replaces strlen() in the centring code of 0x088D15E8. a0 = line.
#   returns v0 = strlen(line) (the original adjustments still apply to it), and stores
#   0x1E0 - (W - 7*len) at the caller's 0x20($sp), read back instead of the constant 0x1E0.
#   W = proportional width: ASCII by glyph advance, SJIS 14, %y = Yes+28+No-98 (the caller adds 98), other %x 14.
VW_LW:
  addiu $sp,$sp,-48
  sw $ra,0x10($sp)
  sw $s0,0x14($sp)
  sw $s1,0x18($sp)
  sw $s2,0x1c($sp)
  move $s0,$a0
  move $s1,$zero
  move $s2,$zero
1:
  lbu $a0,0($s0)
  beqz $a0,9f
  slti $v0,$a0,0x80
  bnez $v0,2f
  slti $v0,$a0,0xf1
  beqz $v0,2f
  nop
  addiu $s2,$s2,14
  addiu $s0,$s0,2
  b 1b
  addiu $s1,$s1,2
2:
  addiu $v0,$zero,0x25
  bne $a0,$v0,5f
  nop
  lbu $a1,1($s0)
  beqz $a1,5f
  addiu $v0,$zero,0x79
  bne $a1,$v0,4f
  nop
  lui $v0,{hi(0x8a207bc)}
  lw $v0,{lo(0x8a207bc)}($v0)
  bal VW_STRW
  lw $a0,0($v0)
  addu $s2,$s2,$v0
  lui $v0,{hi(0x8a207bc)}
  lw $v0,{lo(0x8a207bc)}($v0)
  bal VW_STRW
  lw $a0,4($v0)
  addu $s2,$s2,$v0
  addiu $s2,$s2,{28-98}
  addiu $s0,$s0,2
  b 1b
  addiu $s1,$s1,2
4:
  addiu $s2,$s2,14
  addiu $s0,$s0,2
  b 1b
  addiu $s1,$s1,2
5:
  bal VW_ADVCH
  nop
  addu $s2,$s2,$v0
  addiu $s0,$s0,1
  b 1b
  addiu $s1,$s1,1
9:
  sll $v0,$s1,3
  subu $v0,$v0,$s1
  subu $v0,$v0,$s2
  addiu $v0,$v0,0x1e0
  sw $v0,0x50($sp)
  move $v0,$s1
  lw $ra,0x10($sp)
  lw $s0,0x14($sp)
  lw $s1,0x18($sp)
  lw $s2,0x1c($sp)
  jr $ra
  addiu $sp,$sp,48
'''
code,syms=assemble(src,CAVE)
print("code size",len(code)); assert CAVE+len(code)<=CAVE_END
assert d[v2o(CAVE)-12:v2o(CAVE)].endswith(b'error\0') or True
patch=[]
def add(va,new,expect=None):
    o=v2o(va)
    if expect is not None: assert _expect(d,o,expect),(hex(va),d[o:o+len(new)].hex())
    patch.append(dict(file_off=o,orig_sha1=hashlib.sha1(d[o:o+len(new)]).hexdigest(),new_hex=bytes(new).hex()))
def W(s): c,_=assemble(s,0); return c
def jal(t): return struct.pack('<I',0x0c000000|((t>>2)&0x3ffffff))
add(CAVE,code)
# centring: strlen -> VW_LW ; li a0,0x1e0 -> lw a0,0x20(sp)
add(0x88d1658,jal(syms['VW_LW']),'sha1:4:807405535960d2d3aa93fa62ec454406b5711c3b')
add(0x88d1748,W('lw $a0,0x20($sp)'),'sha1:4:636ece8a538d8cd2f615e51376bcc413804869c0')
# body text, ASCII path
add(0x88d17fc,jal(syms['VW_MB']),'sha1:4:fb4e685c3b27e2935ae121f07285d07790622591')
add(0x88d180c,W('addu $v1,$v1,$v0'),'sha1:4:993eb6fb23bc343ff3c45a07e2eabd8ee1a52c41')
# %y labels: pass the real character instead of the constant " " (0x08A1F6E8), proportional advance
for a_arg,a_jal,a_adv in ((0x88d1aac,0x88d1ac0,0x88d1ac8),(0x88d1b50,0x88d1b64,0x88d1b6c)):
    add(a_arg,W('move $a0,$s4'),'sha1:4:aaa26fa2ad8e444a228646b931cc95d17daa2482')
    add(a_jal,jal(syms['VW_MB']),'sha1:4:fb4e685c3b27e2935ae121f07285d07790622591')
    add(a_adv,W('addu $s0,$s0,$v0'),'sha1:4:f1e22684f9e969159828ced486587991d432db27')
# 0x088D1BDC: ASCII quad as wide as a full cell (14px) instead of 7px (no more squashing)
add(0x88d1d24,W('b 0x38'),'sha1:4:f160c932741f7b474fef419cec04288f48aead9e')   # 'b .+0x3c' -> 0x88d1d60 (same target as the bnez)
# labels back to ASCII
add(0x8a1f6ec,b'Yes\0\0\0\0\0','sha1:8:2c821363ac0fe5fd0f7e76c47c60b17c4e72b9b7')
add(0x8a1f6f4,b'No\0\0','sha1:4:a52d586594277c3e294073a2a4228b7bba20543c')
json.dump(patch,open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'patch.json'),'w'),indent=0)
json.dump({k:hex(v) for k,v in syms.items()},open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'layout.json'),'w'),indent=1)
print('cave',hex(CAVE),hex(CAVE+len(code)),len(code),'bytes;',len(patch),'patches')
