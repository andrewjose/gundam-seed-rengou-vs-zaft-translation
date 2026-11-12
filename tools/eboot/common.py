import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import struct, capstone
D=open(P.eboot_dec(),'rb').read()
BASE=0x08804000; OFF=0x54
def rd(va,n): return D[va-BASE+OFF:va-BASE+OFF+n]
def w32(va): return struct.unpack('<I',rd(va,4))[0]
md=capstone.Cs(capstone.CS_ARCH_MIPS,capstone.CS_MODE_MIPS32+capstone.CS_MODE_LITTLE_ENDIAN)
def dis(va,n):
    for i in md.disasm(rd(va,n*4),va):
        print('%08x: %08x  %s %s'%(i.address,struct.unpack('<I',i.bytes)[0],i.mnemonic,i.op_str))
def cstr(va):
    b=rd(va,256); return b[:b.index(0)].decode('latin1')
