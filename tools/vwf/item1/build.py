#!/usr/bin/env python3
"""Item 1: proportional advance for the pilot/unit-name glyph system (14px + 18px sheets).
Writes item1/patch.json ([{file_off, orig_sha1, new_hex}]) against <work>/stage/eboot_v03d.elf."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,struct,json,os
from masm import assemble,hi,lo
from measure_names import measure
BASE_ELF=P.stage('eboot_v03d.elf')
d=open(BASE_ELF,'rb').read()
def _expect(d,o,e):
    """e = 'sha1:<n>:<sha1 of the n original bytes at o>' (no original bytes stored) or '' (no check)."""
    if not e: return True
    _,n,h=e.split(':'); return hashlib.sha1(bytes(d[o:o+int(n)])).hexdigest()==h
def v2o(v): return v-0x8804000+0x54
CAVE=0x89D6BBC            # file 0x1d2c10: CRI ADXT "parameter error" message strings (debug only)
CAVE_END=0x89D6BBC+0x3F0  # item 1 uses at most 0x1d2c10..0x1d3000
assert hashlib.sha1(bytes(d[v2o(CAVE):v2o(CAVE)+9])).hexdigest()=='a337ae216af8e5e43e43f54190f3a11a2b613a23'  # CRI ADXT debug message text
# ---------- width tables ----------
GROUPS={'G1':[(2,14),(134,14)],'G2':[(124,14),(129,14)],'T18':[(11,18),(130,18),(135,18),(137,18),(138,18)]}
GAP={'G1':1.0,'G2':1.5,'T18':1.5}
SPACE={'G1':0.30,'G2':0.30,'T18':0.30}   # space ink width as fraction of the cell
KB=("ABCDEFGHIJ" "KLMNOPQRST" "UVWXYZabcd" "efghij*k*l" "mnopqrstuv" "wxyz.-'!?")
CELL={}
for i,ch in enumerate(KB):
    if ch!='*': CELL[ch]=(i//10)*15+i%10
for n in range(10): CELL[str(n)]=90+n
CELL[' ']=85
M=measure()
def table(g):
    P=GROUPS[g][0][1]
    gap=round(64*GAP[g]/P)
    U=32-gap//2
    t=bytearray([U]*100)
    widths={}
    for ch,c in CELL.items():
        if ch==' ': w=SPACE[g]*P
        else:
            ws=[M[ch][k][1]-M[ch][k][0] for k in GROUPS[g] if k in M.get(ch,{})]
            if not ws: continue
            w=int(max(ws))
        widths[ch]=w
        t[c]=max(1,min(40,round(32*w/P)))
    return bytes(t)+bytes([gap,U,0,0]),widths,P,gap
TABS={}; WID={}
blob=bytearray()
for g in ('G1','G2','T18'):
    t,w,P,gap=table(g); TABS[g]=CAVE+len(blob); WID[g]=(w,P,gap); blob+=t
CODE=CAVE+len(blob)
SITES={ # name: (X = addr of 'lui vX,A', A-reg, cell-load insn (delay slot), next source, table)
 'A':(0x89b5144,'$v1','lbu $a0,0x6c($sp)','sjis:$s0','T18'),
 'B':(0x89a03d8,'$v1','lbu $a0,0x6c($sp)','sjis:$s3','G2'),
 'C':(0x89ad124,'$v1','lbu $a0,0x6c($sp)','sjis:$s0','G1'),
 'D':(0x89b29ac,'$v0','lbu $a0,6($s1)','code:8($s1)','T18'),
 'E':(0x89b68bc,'$v1','lbu $a0,0x6c($sp)','sjis:$s0','T18'),
 'F':(0x89b6b10,'$v1','lbu $a0,0x6c($sp)','sjis:$s0','T18'),
}
src=f'''
# ---- VW_CORE: a0=cur cell, a1=next cell, at=table, f0=pen, f1=cell advance A
#      f0 = pen + A*(H[cur]+H[next]+gap)/64 ; clobbers a0,a1 ; keeps v0,v1,f2,f3
VW_CORE:
  addiu $sp,$sp,-16
  sw $v0,0($sp)
  sw $v1,4($sp)
  swc1 $f2,8($sp)
  swc1 $f3,12($sp)
  lbu $v0,100($at)
  andi $a0,$a0,0xff
  sltiu $v1,$a0,100
  bnez $v1,1f
  addu $v1,$at,$a0
  xori $v1,$a0,0xff
  beqz $v1,1f
  addiu $v1,$at,85
  addiu $v1,$at,101
1:
  lbu $v1,0($v1)
  addu $v0,$v0,$v1
  andi $a1,$a1,0xff
  sltiu $v1,$a1,100
  bnez $v1,2f
  addu $v1,$at,$a1
  xori $v1,$a1,0xff
  beqz $v1,2f
  addiu $v1,$at,85
  addiu $v1,$at,101
2:
  lbu $v1,0($v1)
  addu $v0,$v0,$v1
  mtc1 $v0,$f2
  cvt.s.w $f2,$f2
  lui $v0,0x3c80
  mtc1 $v0,$f3
  mul.s $f2,$f2,$f3
  mul.s $f2,$f2,$f1
  add.s $f0,$f0,$f2
  lw $v0,0($sp)
  lw $v1,4($sp)
  lwc1 $f2,8($sp)
  lwc1 $f3,12($sp)
  jr $ra
  addiu $sp,$sp,16

# ---- VW_SJ: a0=cur cell, a1=next SJIS char ptr, at=table, f0=pen, f1=A
#      converts the next char with the game's own converter 0x089BE1B4 (keeps a2,a3,t0-t4,v1,ra)
VW_SJ:
  addiu $sp,$sp,-48
  sw $ra,0($sp)
  sw $a2,4($sp)
  sw $a3,8($sp)
  sw $t0,12($sp)
  sw $t1,16($sp)
  sw $t2,20($sp)
  sw $t3,24($sp)
  sw $t4,28($sp)
  sw $v1,32($sp)
  sw $a0,36($sp)
  sw $at,40($sp)
  jal 0x89be1b4
  addiu $a0,$sp,44
  lbu $a1,44($sp)
  lw $a0,36($sp)
  bal VW_CORE
  lw $at,40($sp)
  lw $ra,0($sp)
  lw $a2,4($sp)
  lw $a3,8($sp)
  lw $t0,12($sp)
  lw $t1,16($sp)
  lw $t2,20($sp)
  lw $t3,24($sp)
  lw $t4,28($sp)
  lw $v1,32($sp)
  jr $ra
  addiu $sp,$sp,48

# ---- generic name drawer 0x089BE334 (14px sheet, AFS 2_2 / 134_1_5): f1=advance (obj+0x20), s3=code ptr
VW_G:
  lwc1 $f0,0x60($sp)
  lbu $a1,2($s3)
  lui $at,{hi(TABS['G1'])}
  b VW_CORE
  addiu $at,$at,{lo(TABS['G1'])}
'''
for n,(X,areg,cl,nxt,tab) in SITES.items():
    src+=f'VW_{n}:\n  mov.s $f0,$f1\n  mtc1 {areg},$f1\n'
    kind,arg=nxt.split(':')
    if kind=='sjis':
        src+=f'  addiu $a1,{arg},2\n  lui $at,{hi(TABS[tab])}\n  b VW_SJ\n  addiu $at,$at,{lo(TABS[tab])}\n'
    else:
        src+=f'  lbu $a1,{arg}\n  lui $at,{hi(TABS[tab])}\n  b VW_CORE\n  addiu $at,$at,{lo(TABS[tab])}\n'
code,syms=assemble(src,CODE)
blob+=code
assert CAVE+len(blob)<=CAVE_END, hex(CAVE+len(blob))
patch=[]
def add(va,new):
    o=v2o(va); patch.append(dict(file_off=o,orig_sha1=hashlib.sha1(d[o:o+len(new)]).hexdigest(),new_hex=bytes(new).hex()))
def jal(t): return struct.pack('<I',0x0c000000|((t>>2)&0x3ffffff))
add(CAVE,blob)
code2,_=assemble('lbu $a0,0($s3)\naddiu $s1,$s1,1\nswc1 $f0,0x60($sp)',0)
assert hashlib.sha1(bytes(d[v2o(0x89be440):v2o(0x89be450)])).hexdigest()=='2736b1976d2c888299e27bf0c4f6511957e545a8'
add(0x89be440, jal(syms['VW_G'])+code2)
for n,(X,areg,cl,nxt,tab) in SITES.items():
    o=v2o(X); w=struct.unpack_from('<3I',d,o)
    assert w[0]>>16==0x3c02|(0 if areg=='$v0' else 1)  # lui v0/v1
    assert w[2]==0x46000800, hex(w[2])                   # add.s f0,f1,f0
    c,_=assemble(cl,0)
    add(X+4, jal(syms['VW_'+n])+c)
json.dump(patch,open(os.path.join(os.path.dirname(__file__),'patch.json'),'w'),indent=0)
json.dump({'syms':{k:hex(v) for k,v in syms.items()},'tables':{k:hex(v) for k,v in TABS.items()},
           'widths':{g:dict(w=WID[g][0],P=WID[g][1],gap64=WID[g][2]) for g in WID},'cave_used':[hex(CAVE),hex(CAVE+len(blob))]},
          open(os.path.join(os.path.dirname(__file__),'layout.json'),'w'),indent=1)
print('cave',hex(CAVE),'..',hex(CAVE+len(blob)),len(blob),'bytes; patches',len(patch))
for k,v in syms.items(): print(k,hex(v))
