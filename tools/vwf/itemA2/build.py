#!/usr/bin/env python3
"""Item A2: SELECT A PILOT big name = object draw callback 0x0899D314 (codes at obj+0x170 filled by 0x0899D1F8
from record(+6), 8 slots, x = slot*17.75 on the 18px sheet). f20 (x offset) becomes the proportional pen
summed over the previous slots. Needs item 1 (VW_CORE + T18). Patch against <work>/stage/eboot_v041a.elf (items 1,2,3,3b,A,B applied)."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,os,json
H=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.dirname(H))
from masm import assemble,hi,lo
d=open(P.stage('eboot_v041a.elf'),'rb').read()
def _expect(d,o,e):
    """e = 'sha1:<n>:<sha1 of the n original bytes at o>' (no original bytes stored) or '' (no check)."""
    if not e: return True
    _,n,h=e.split(':'); return hashlib.sha1(bytes(d[o:o+int(n)])).hexdigest()==h
def v2o(v): return v-0x8804000+0x54
L1=json.load(open(os.path.join(H,'..','item1','layout.json')))
CORE=int(L1['syms']['VW_CORE'],16); T18=int(L1['tables']['T18'],16)
STUB=0x89d6ed0; END=0x89d6fac
stub,syms=assemble(f'''
VW_PN:
  addiu $sp,$sp,-32
  sw $ra,0x10($sp)
  sw $t0,0x14($sp)
  sw $t1,0x18($sp)
  mtc1 $zero,$f0
  lui $at,0x418e
  ori $at,$at,0x8106
  mtc1 $at,$f1
  sll $t0,$s2,1
  subu $t0,$s3,$t0
  move $t1,$zero
1:
  slt $at,$t1,$s2
  beqz $at,2f
  nop
  lbu $a0,0($t0)
  lbu $a1,2($t0)
  lui $at,{hi(T18)}
  jal {CORE}
  addiu $at,$at,{lo(T18)}
  addiu $t0,$t0,2
  b 1b
  addiu $t1,$t1,1
2:
  mov.s $f20,$f0
  lw $ra,0x10($sp)
  lw $t0,0x14($sp)
  lw $t1,0x18($sp)
  jr $ra
  addiu $sp,$sp,32
''',STUB)
assert STUB+len(stub)<=END
site,_=assemble(f'''
  jal {STUB}
  nop
  lui $s0,0x8ab
  move $s1,$zero
  addiu $s0,$s0,-0x36b0
  nop
  nop
  nop
  nop
''',0x899d36c)
patch=[]
def add(va,new,exp):
    o=v2o(va); assert _expect(d,o,exp),(hex(va),d[o:o+len(new)].hex())
    patch.append(dict(file_off=o,orig_sha1=hashlib.sha1(d[o:o+len(new)]).hexdigest(),new_hex=bytes(new).hex()))
add(STUB,stub,'')
add(0x899d36c,site,'sha1:12:b0c1c447667c6c0544f57503d49869520413f52a')
json.dump(patch,open(os.path.join(H,'patch.json'),'w'),indent=0)
print('stub',hex(STUB),len(stub))
