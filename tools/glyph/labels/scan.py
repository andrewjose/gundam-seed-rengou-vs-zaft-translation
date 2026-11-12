import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import capstone,struct,sys
d=open(P.stage('eboot_v02.elf'),'rb').read()
BASE=0x08804000; FO=0x54
md=capstone.Cs(capstone.CS_ARCH_MIPS,capstone.CS_MODE_MIPS32+capstone.CS_MODE_LITTLE_ENDIAN); md.detail=False
TEXT_END=0x89d4704
ins=[]
for i in range(0,TEXT_END-BASE,4):
    w,=struct.unpack_from('<I',d,FO+i); ins.append(w)
import pickle; pickle.dump(ins,open(P.work('glyph','ins.pkl'),'wb'))
