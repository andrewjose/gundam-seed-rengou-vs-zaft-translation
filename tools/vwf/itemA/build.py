#!/usr/bin/env python3
"""Item A: big pilot name on the SELECT A PILOT panel (0x0899BF6C, record+6 name, 18px sheet, x = index*17.5).
Requires item 1 (uses VW_SJ / T18 table in its cave). Patch against <work>/stage/eboot_v04.elf."""
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
L1=json.load(open(os.path.join(H,'..','item1','layout.json')))
VW_SJ=int(L1['syms']['VW_SJ'],16); T18=int(L1['tables']['T18'],16)
STUB=0x89d6eb0; END=0x89d6fac
stub,syms=assemble(f'''
VW_PS:
  bnez $s2,1f
  lui $at,0x418c
  jr $ra
  mtc1 $zero,$f0
1:
  mtc1 $at,$f1
  lui $at,{hi(T18)}
  j {VW_SJ}
  addiu $at,$at,{lo(T18)}
''',STUB)
assert STUB+len(stub)<=END
site,_=assemble(f'''
  nop
  lwc1 $f0,0x20($sp)
  lbu $a0,0x7c($sp)
  jal {STUB}
  move $a1,$s3
  sw $zero,0x24($sp)
  sw $zero,0x28($sp)
  move $a1,$s3
  sw $zero,0x2c($sp)
  addiu $a0,$sp,0x7c
  jal 0x89be1b4
  swc1 $f0,0x20($sp)
''',0x899c060)
assert len(site)==48
patch=[]
def add(va,new,exp):
    o=v2o(va); assert _expect(d,o,exp),(hex(va),d[o:o+len(new)].hex())
    patch.append(dict(file_off=o,orig_sha1=hashlib.sha1(d[o:o+len(new)]).hexdigest(),new_hex=bytes(new).hex()))
add(STUB,stub,'')
add(0x899c060,site,'sha1:4:ab3037b30ac2aff6d67911570b5fe2f34ae2ce3b')
json.dump(patch,open(os.path.join(H,'patch.json'),'w'),indent=0)
print('stub',hex(STUB),len(stub),'site 0x899c060',len(site))
