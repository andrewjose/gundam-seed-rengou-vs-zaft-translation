import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import capstone,struct,sys
d=open(P.eboot_dec(),'rb').read()
BASE=0x08804000; FO=0x54
def v2o(v): return v-BASE+FO
md=capstone.Cs(capstone.CS_ARCH_MIPS,capstone.CS_MODE_MIPS32+capstone.CS_MODE_LITTLE_ENDIAN); md.skipdata=True
def dis(va,n):
    o=v2o(va)
    for i in md.disasm(d[o:o+4*n],va): print('%08x: %-8s %s'%(i.address,i.mnemonic,i.op_str))
if __name__=='__main__': dis(int(sys.argv[1],16),int(sys.argv[2]))
