import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import keystone,struct,sys,re
from common import *
ks=keystone.Ks(keystone.KS_ARCH_MIPS, keystone.KS_MODE_MIPS32+keystone.KS_MODE_LITTLE_ENDIAN)
BODY='''
beqz $v0, 0x88d2468
sw $v0, 0x7c($sp)
beqz $s2, 0x88d2468
lwc1 $f1, 0x98($sp)
cvt.s.w $f1, $f1
lui $v0, 0x44a0
mul.s $f1, $f1, $f21
mtc1 $v0, $f0
beqz $s1, 0x88d2438
div.s $f20, $f1, $f0
lwc1 $f0, 0x44($sp)
lui $v0, 0x3f80
mtc1 $v0, $f2
add.s $f0, $f2, $f0
lwc1 $f1, 0x40($sp)
lui $v0, 0x8000
sw $v0, 0x70($sp)
add.s $f1, $f2, $f1
addiu $a0, $sp, 0x50
add.s $f0, $f0, $f20
swc1 $f1, 0x20($sp)
swc1 $f0, 0x24($sp)
add.s $f1, $f1, $f22
add.s $f0, $f21, $f0
swc1 $f1, 0x30($sp)
jal 0x8902950
swc1 $f0, 0x34($sp)
lwc1 $f0, 0x44($sp)
lwc1 $f1, 0x40($sp)
addiu $a0, $sp, 0x50
add.s $f0, $f0, $f20
swc1 $f1, 0x20($sp)
sw $s2, 0x70($sp)
swc1 $f0, 0x24($sp)
add.s $f1, $f1, $f22
add.s $f0, $f21, $f0
swc1 $f1, 0x30($sp)
jal 0x8902950
swc1 $f0, 0x34($sp)
sltiu $v1, $s0, 0x80
lui $v0, 0x3f80
beqz $v1, 0x88d249c
mtc1 $v0, $f2
lw $v0, 0x90($sp)
lw $v1, 0x94($sp)
addu $v0, $v0, $v1
addiu $v0, $v0, 1
mtc1 $v0, $f2
cvt.s.w $f2, $f2
lui $v0, 0x41a0
mtc1 $v0, $f3
div.s $f2, $f2, $f3
lwc1 $f0, 0x40($sp)
mul.s $f2, $f2, $f22
add.s $f0, $f0, $f2
lw $v1, 0xac($sp)
lbu $v1, 0($v1)
bnez $v1, 0x88d23b0
swc1 $f0, 0x40($sp)
'''
lines=[l for l in BODY.strip().splitlines()]
words=[]
a=0x88d23cc
REG={'zero':0,'v0':2,'v1':3,'s0':16,'s1':17,'s2':18}
for l in lines:
    m=re.match(r'(beqz|bnez) \$(\w+), (0x[0-9a-f]+)',l)
    if m:
        op=4 if m.group(1)=='beqz' else 5
        off=((int(m.group(3),16)-(a+4))>>2)&0xffff
        w=(op<<26)|(REG[m.group(2)]<<21)|off
    elif l.startswith('jal '):
        w=(3<<26)|((int(l.split()[1],16)>>2)&0x3ffffff)
    else:
        enc,_=ks.asm(l,a); assert len(enc)==4,(l,enc)
        w=struct.unpack('<I',bytes(enc))[0]
    words.append(w); a+=4
assert a==0x88d24b8, hex(a)
orig=[w32(0x88d23cc+4*i) for i in range(len(words))]
print('N',len(words))
import json
json.dump({'start':0x88d23cc,'orig':orig,'new':words},open(P.work('propfont_words.json'),'w'))
for i,(o,n) in enumerate(zip(orig,words)):
    va=0x88d23cc+4*i
    oi=next(md.disasm(struct.pack('<I',o),va)); ni=next(md.disasm(struct.pack('<I',n),va))
    print('%08x %06x %08x %-34s -> %08x %s'%(va,va-BASE+OFF,o,oi.mnemonic+' '+oi.op_str,n,ni.mnemonic+' '+ni.op_str))
