import hashlib
import struct,json,sys
from unicorn import *
from unicorn.mips_const import *
import unicorn.mips_const as MC
def apply(path_in,patches):
    d=bytearray(open(path_in,'rb').read())
    for pj in patches:
        for p in json.load(open(pj)):
            o=p['file_off']; nb=bytes.fromhex(p['new_hex'])
            assert hashlib.sha1(bytes(d[o:o+len(nb)])).hexdigest()==p['orig_sha1'],hex(o); d[o:o+len(nb)]=nb
    return d
class Emu:
    def __init__(self,elf):
        self.d=elf
        mu=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32+UC_MODE_LITTLE_ENDIAN)
        mu.mem_map(0x08800000,0x01800000)
        img=bytes(elf[0x54:0x54+0x31fe50])
        mu.mem_write(0x8804000,img)
        self.mu=mu
        self.hooks={}
        # enable FPU: unicorn mips CP0 status CU1
        try:
            st=mu.reg_read(UC_MIPS_REG_CP0_STATUS); mu.reg_write(UC_MIPS_REG_CP0_STATUS,st|0x20000000)
        except Exception as e: print('status',e)
        mu.hook_add(UC_HOOK_CODE,self._code)
        self.trace=[]
    def _code(self,mu,addr,size,ud):
        if addr in self.hooks:
            self.hooks[addr](self)
    def ret(self):
        self.mu.reg_write(UC_MIPS_REG_PC,self.mu.reg_read(UC_MIPS_REG_RA))
    def f(self,n):
        return struct.unpack('<f',struct.pack('<I',self.mu.reg_read(UC_MIPS_REG_F0+n)&0xffffffff))[0]
    def setf(self,n,v): self.mu.reg_write(UC_MIPS_REG_F0+n,struct.unpack('<I',struct.pack('<f',v))[0])
    def r(self,name): return self.mu.reg_read(getattr(MC,'UC_MIPS_REG_'+name.upper()))
    def w(self,name,v): self.mu.reg_write(getattr(MC,'UC_MIPS_REG_'+name.upper()),v&0xffffffff)
    def rd(self,a,n): return bytes(self.mu.mem_read(a,n))
    def wr(self,a,b): self.mu.mem_write(a,bytes(b))
    def rf(self,a): return struct.unpack('<f',self.rd(a,4))[0]
    def wf(self,a,v): self.wr(a,struct.pack('<f',v))
    def run(self,start,until,count=200000):
        self.mu.emu_start(start,until,count=count)
