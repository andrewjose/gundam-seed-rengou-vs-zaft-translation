"""assemble MIPS (Allegrex subset) with llvm-mc at a fixed base address; asserts no relocations."""
import subprocess,tempfile,os,re,struct
def assemble(src, base):
    with tempfile.TemporaryDirectory() as t:
        s=os.path.join(t,'a.s'); o=os.path.join(t,'a.o')
        open(s,'w').write('.set noreorder\n.set noat\n.set nomacro\n.text\n'+src+'\n')
        r=subprocess.run(['llvm-mc','-triple=mipsel-unknown-linux','-mcpu=mips32r2','-filetype=obj',s,'-o',o],capture_output=True,text=True)
        if r.returncode: raise SystemExit(r.stderr)
        rel=subprocess.run(['llvm-objdump','-r',o],capture_output=True,text=True).stdout
        if 'R_MIPS' in rel: raise SystemExit('relocations present:\n'+rel)
        b=subprocess.run(['llvm-objcopy','-O','binary','--only-section=.text',o,os.path.join(t,'b')],capture_output=True,text=True)
        if b.returncode: raise SystemExit(b.stderr)
        code=open(os.path.join(t,'b'),'rb').read()
        sy=subprocess.run(['llvm-nm',o],capture_output=True,text=True).stdout
        syms={}
        for line in sy.splitlines():
            p=line.split()
            if len(p)==3: syms[p[2]]=base+int(p[0],16)
    return code,syms
def hi(v): return ((v+0x8000)>>16)&0xffff
def lo(v): return v&0xffff if (v&0xffff)<0x8000 else (v&0xffff)-0x10000
def J(target): return struct.pack('<I',(0x0c000000)|((target>>2)&0x3ffffff))
