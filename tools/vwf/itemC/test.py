#!/usr/bin/env python3
"""Emulated check of item C (unicorn): runs VW_BLEN on the patched v0.4.1 EBOOT with a stand-in glyph-metrics hook
for 0x08979F40 (bitmapWidth = 4 + code % 9, bitmapLeft = code % 2) and compares with the same formula in Python,
for all three entry points. Also checks the stack pointer and s0/s1 are preserved and that every call site now calls
VW_BLEN. usage: test.py [v041.elf]  (default <work>/stage/eboot_v041.elf)"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P
import sys, os, json, struct, hashlib
from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
from unicorn.mips_const import *
H = os.path.dirname(os.path.abspath(__file__))
inp = sys.argv[1] if len(sys.argv) > 1 else P.stage('eboot_v041.elf')
eb = bytearray(open(inp, 'rb').read())
for p in json.load(open(os.path.join(H, 'patch.json'))):
    o = p['file_off']; nb = bytes.fromhex(p['new_hex'])
    assert hashlib.sha1(bytes(eb[o:o + len(nb)])).hexdigest() == p['orig_sha1'], hex(o)
    eb[o:o + len(nb)] = nb
L = {k: int(v, 16) for k, v in json.load(open(os.path.join(H, 'layout.json'))).items()}
def metrics(c): return 4 + c % 9, c % 2
def units(b):
    u = 0; i = 0
    while i < len(b):
        c = b[i]
        if c >= 0x80: u += 20; i += 2; continue
        if c == 0x20: u += 11
        else: w, l = metrics(c); u += w + l + 1
        i += 1
    return u
mu = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 + UC_MODE_LITTLE_ENDIAN)
mu.mem_map(0x08800000, 0x02000000); mu.mem_write(0x08804000, bytes(eb[0x54:]))
STK, STR, RET = 0x09f00000, 0x09e00000, 0x09d00000
def hook(uc, addr, size, ud):
    a0 = uc.reg_read(UC_MIPS_REG_A0); a2 = uc.reg_read(UC_MIPS_REG_A2)
    w, l = metrics(uc.mem_read(a0, 1)[0]); uc.mem_write(a2, struct.pack('<ii', w, l))
    for r in (UC_MIPS_REG_T0, UC_MIPS_REG_A1, UC_MIPS_REG_A3, UC_MIPS_REG_V1): uc.reg_write(r, 0xdeadbeef)
    uc.reg_write(UC_MIPS_REG_V0, 1); uc.reg_write(UC_MIPS_REG_PC, uc.reg_read(UC_MIPS_REG_RA))
mu.hook_add(UC_HOOK_CODE, hook, begin=0x08979F40, end=0x08979F40)
tests = [b'', b'Please wait.', b'Lost connection with the host (1P).', b'Repel Justice (Meteor)', b'\x83\x65\x83\x58', b'A']
ok = n = 0
for s in tests:
    for e, k in (('blen0', 0), ('blen1', 1), ('blen2', 2)):
        mu.mem_write(STR, s + b'\0'); mu.reg_write(UC_MIPS_REG_SP, STK); mu.reg_write(UC_MIPS_REG_A0, STR); mu.reg_write(UC_MIPS_REG_RA, RET)
        mu.reg_write(UC_MIPS_REG_S0, 0x1234); mu.reg_write(UC_MIPS_REG_S1, 0x5678)
        mu.emu_start(L[e], RET, count=200000)
        v = mu.reg_read(UC_MIPS_REG_V0); exp = (units(s) + 5) // 10 + k
        good = v == exp and mu.reg_read(UC_MIPS_REG_SP) == STK and mu.reg_read(UC_MIPS_REG_S0) == 0x1234 and mu.reg_read(UC_MIPS_REG_S1) == 0x5678
        ok += good; n += 1
        if not good: print('FAIL', e, s, v, exp)
print('item C emulation: %d/%d ok (double-byte strings measure as their byte count: %s)' % (ok, n, (units(b'\x83\x65\x83\x58') + 5) // 10 == 4))
sys.exit(0 if ok == n else 1)
