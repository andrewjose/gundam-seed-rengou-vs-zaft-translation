import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import capstone,struct,sys,re
d=open(P.stage('eboot_v03d.elf'),'rb').read()
md=capstone.Cs(capstone.CS_ARCH_MIPS,capstone.CS_MODE_MIPS32+capstone.CS_MODE_LITTLE_ENDIAN); md.detail=True
def ins(a):
    o=a-0x8804000+0x54
    l=list(md.disasm(d[o:o+4],a))
    return l[0] if l else None
BR={'beq','bne','beql','bnel','bgez','bgtz','blez','bltz','bltzl','bgezl','blezl','bgtzl','bc1t','bc1f','bc1tl','bc1fl','beqz','bnez','beqzl','bnezl','b'}
def rw(i):
    m=i.mnemonic; regs=re.findall(r'\$(\w+)',i.op_str)
    if m in ('sb','sh','sw','swc1','swl','swr','sdc1') or m in BR or m.startswith('c.') or m in('mult','multu','div','divu','madd','maddu','msub','msubu','jr','jalr','teq','tne','mthi','mtlo','sync','nop','syscall','break','cache'):
        r=set(regs); w=set()
        if m in('jalr',): w={'ra'}
        if m[:4] in('mult','madd','msub') or m[:3]=='div': w|={'hi','lo'}
        return r,w
    if m=='mtc1': return {regs[0]},{regs[1]}
    if m=='jal': return set(),{'ra'}
    if m in('mfhi','mflo'): return {m[2:]},{regs[0]}
    if not regs: return set(),set()
    return set(regs[1:]),{regs[0]}
def live(start,regs,limit=200):
    """is any reg in regs read before written starting at start (following both branch paths)? returns list of (reg, addr) reads"""
    res=[]; seen=set()
    stack=[(start,frozenset(regs),0)]
    while stack:
        a,rs,n=stack.pop()
        if not rs or n>limit or (a,rs) in seen: continue
        seen.add((a,rs))
        i=ins(a)
        if i is None: res.append(('?',hex(a))); continue
        r,w=rw(i)
        m=i.mnemonic
        for x in rs&r: res.append((x,hex(a),m+' '+i.op_str))
        rs=rs-r  # read reported; stop tracking
        if m in('jr',) : 
            if 'ra' in i.op_str: continue
        if m in('jal','jalr'):
            # delay slot then callee clobbers caller-saved: treat a0-a3,v0,v1,t*,at,f0-f19 as written after delay slot
            di=ins(a+4); dr,dw=rw(di)
            for x in rs&dr: res.append((x,hex(a+4),'delay '+di.mnemonic+' '+di.op_str))
            rs=rs-dr-dw
            # argument regs could be read by callee! treat a0-a3 as read if live
            for x in rs&{'a0','a1','a2','a3'}: res.append((x,hex(a),'arg to call?'))
            rs=frozenset(x for x in rs if x not in('a0','a1','a2','a3','v0','v1','at','t0','t1','t2','t3','t4','t5','t6','t7','t8','t9') and not (x.startswith('f') and int(x[1:])<20))
            stack.append((a+8,rs,n+2)); continue
        rs=rs-w
        if m in BR:
            di=ins(a+4); dr,dw=rw(di)
            tgt=int(i.op_str.split(',')[-1].strip(),16)
            for x in rs&dr: res.append((x,hex(a+4),'delay'))
            likely=m.endswith('l') and m not in('bnel_',)
            rs2=rs-dw
            stack.append((tgt,rs2,n+2))
            if m!='b': stack.append((a+8, rs if likely else rs2, n+2))
            continue
        if m=='j':
            stack.append((int(i.op_str,16),rs,n+1)); continue
        rs=frozenset(rs)
        stack.append((a+4,rs,n+1))
    return res
if __name__=='__main__':
    a=int(sys.argv[1],16); regs=sys.argv[2].split(',')
    for x in live(a,set(regs)): print(x)
