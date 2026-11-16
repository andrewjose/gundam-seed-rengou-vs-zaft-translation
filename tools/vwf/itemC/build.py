#!/usr/bin/env python3
"""Item C (v0.4.4): byte-count width estimates -> proportional estimate.
Nine call sites measure text as strlen() x 7 px (the Japanese 2-byte / 14 px assumption) to centre it or to shrink
it to a box. They now call VW_BLEN, which returns round(units / 10), units = sum of the sceFont advances in 1/20-size
units exactly as the proportional renderer 0x088D2330 advances them (ASCII: bitmapWidth + bitmapLeft + 1 from the
glyph cache 0x08979F40, as item 2's VW_ADVCH calls it; space 11; double-byte 20). That is the byte count a Japanese
string of the same width would have, so Japanese text measures exactly as before. Entries +1 / +2 add back the
constant the caller subtracts afterwards (strlen-1, strlen-2).
Cave: file 0x1D3290-0x1D33A8 (CRI ADXT "parameter error" debug strings, after item B's run that ends at 0x1D3290).
Input: the tested v0.4.1 EBOOT (<work>/stage/eboot_v041.elf, MD5 1667c483ad06c3cfbe3455389aba9ce9).
usage: build.py [in.elf]   -> writes patch.json + layout.json next to this file (runs = file_off, orig_sha1, new_hex)"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P
import sys, os, json, struct, hashlib
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(H))
from masm import assemble
def v2o(v): return v - 0x8804000 + 0x54
def o2v(o): return o + 0x8804000 - 0x54
CAVE = 0x1d3290; CAVE_END = 0x1d33a8
BASE = o2v(CAVE)
SRC = '''
blen0: b common
 move $v1,$zero
blen1: b common
 addiu $v1,$zero,1
blen2: b common
 addiu $v1,$zero,2
common:
 addiu $sp,$sp,-0x50
 sw $ra,0x10($sp)
 sw $s0,0x40($sp)
 sw $s1,0x44($sp)
 sw $v1,0x48($sp)
 move $s0,$a0
 move $s1,$zero
loop:
 lbu $a0,0($s0)
 beqz $a0,done
 sltiu $v0,$a0,0x80
 bnez $v0,ascii
 addiu $v0,$zero,0x20
 addiu $s1,$s1,20
 b loop
 addiu $s0,$s0,2
ascii:
 bne $a0,$v0,glyph
 nop
 addiu $s1,$s1,11
 b loop
 addiu $s0,$s0,1
glyph:
 sb $a0,0x14($sp)
 sb $zero,0x15($sp)
 addiu $a0,$sp,0x14
 addiu $a1,$sp,0x28
 jal 0x08979F40
 addiu $a2,$sp,0x18
 beqz $v0,missing
 lw $v0,0x18($sp)
 lw $a0,0x1c($sp)
 addu $v0,$v0,$a0
 addiu $v0,$v0,1
 addu $s1,$s1,$v0
 b loop
 addiu $s0,$s0,1
missing:
 addiu $s1,$s1,10
 b loop
 addiu $s0,$s0,1
done:
 addiu $v0,$s1,5
 addiu $a0,$zero,10
 div $zero,$v0,$a0
 mflo $v0
 lw $v1,0x48($sp)
 addu $v0,$v0,$v1
 lw $ra,0x10($sp)
 lw $s0,0x40($sp)
 lw $s1,0x44($sp)
 jr $ra
 addiu $sp,$sp,0x50
'''
SITES = [  # (call-site VA, entry, what) # (call-site VA, entry, what)
 (0x0888AE54,'blen0','lobby: "1P is in control. Please wait." centred (480-n*7)/2'),
 (0x088715B0,'blen0','lobby: "Return to the menu/lobby?" (%s%s) centred'),
 (0x088717F4,'blen1','lobby: "1P is selecting from the menu..." centred (480-(n-1)*7)/2'),
 (0x089A19E8,'blen0','lobby: "1P is setting up. Please wait." blinking, centred'),
 (0x089C2F5C,'blen2','network messages centred (480-(n-2)*7)/2'),
 (0x089C305C,'blen0','network "Press a button." centred (448-n*7)/2+32'),
 (0x089AEEF0,'blen0','mission panel title lines: size=min(13|14, 196/(n/2)), centred in 196 px'),
 (0x089AF72C,'blen0','mission panel win conditions: size 13, or 182/(n/2) when n/2>=15'),
 (0x089AF800,'blen0','mission panel lose conditions: same fit rule'),
]
STRLEN = 0x0880D70C
def jal(t): return struct.pack('<I', 0x0c000000 | ((t >> 2) & 0x3ffffff))
def build(eb):
    code, syms = assemble(SRC, BASE)
    assert len(code) <= CAVE_END - CAVE, len(code)
    runs = [{'file_off': CAVE, 'orig_sha1': hashlib.sha1(eb[CAVE:CAVE + len(code)]).hexdigest(), 'new_hex': code.hex(),
             'note': 'VW_BLEN stub at 0x%08X' % BASE}]
    for va, e, what in SITES:
        o = v2o(va); assert eb[o:o + 4] == jal(STRLEN), 'site 0x%08X is not jal strlen' % va
        runs.append({'file_off': o, 'orig_sha1': hashlib.sha1(eb[o:o + 4]).hexdigest(), 'new_hex': jal(syms[e]).hex(), 'note': what})
    return runs, syms
if __name__ == '__main__':
    inp = sys.argv[1] if len(sys.argv) > 1 else P.stage('eboot_v041.elf')
    eb = open(inp, 'rb').read()
    assert hashlib.md5(eb).hexdigest() == '1667c483ad06c3cfbe3455389aba9ce9', 'expects the v0.4.1 EBOOT'
    runs, syms = build(eb)
    json.dump(runs, open(os.path.join(H, 'patch.json'), 'w'), indent=1)
    json.dump({k: '0x%08X' % v for k, v in syms.items()}, open(os.path.join(H, 'layout.json'), 'w'), indent=1)
    print('item C: %d runs, VW_BLEN %s' % (len(runs), ', '.join('%s=0x%08X' % (k, v) for k, v in sorted(syms.items()) if k.startswith('blen'))))
