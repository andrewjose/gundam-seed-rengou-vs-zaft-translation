import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,struct,json
from names_fw import *
SRC=P.stage('eboot_v03.elf')
d=bytearray(open(SRC,'rb').read()); orig=bytes(d)
def v2o(v): return v-0x8804000+0x54
def o2v(o): return o-0x54+0x8804000
FW={' ':'\u3000','.':'\uff0e','-':'\uff0d',"'":'\u2019','!':'\uff01','?':'\uff1f'}  # full-width punctuation
def fw(s):
    out=b''; i=0
    while i<len(s):
        c=s[i]
        if c=='#': out+=s[i:i+2].encode('ascii'); i+=2; continue
        if 'A'<=c<='Z' or 'a'<=c<='z' or '0'<=c<='9': out+=chr(ord(c)+0xfee0).encode('cp932')
        else: out+=FW[c].encode('cp932')
        i+=1
    return out
def nchars(s): return len(s)-s.count('#')
# ---- 1. glyph lookup tables ----
KB=("ABCDEFGHIJ" "KLMNOPQRST" "UVWXYZabcd" "efghij*k*l" "mnopqrstuv" "wxyz.-'!?")
assert len(KB)==59
PAGE0=0x2ad2e8
for k,ch in enumerate(KB):
    if ch=='*': continue
    idx=(k//10)*15+k%10
    struct.pack_into('2s',d,PAGE0+2*idx,fw(ch))
for n in range(10): struct.pack_into('2s',d,PAGE0+2*(90+n),fw(str(n)))
d[PAGE0+2*29:PAGE0+2*29+2]=b'\x81\x96'   # full-width '*'; the old full-width 'V' in col 14 would shadow the new V
KBT=0x2a6b90
for k,ch in enumerate(KB):
    if ch=='*': assert d[KBT+2*k:KBT+2*k+2]==b'\x81\x96'; continue
    d[KBT+2*k:KBT+2*k+2]=fw(ch)
assert hashlib.sha1(bytes(d[KBT+2*59:KBT+2*60])).hexdigest()=='9b02ed3420f3103b43d3e74f4d9b17cb83acb21c'  # end-of-table kana sentinel
# ---- 2. ranking default names ----
o=0x2a6398
for i in range(30):
    f=bytes(d[o:o+16]); key=hashlib.sha1(f.split(b'\0')[0]).hexdigest()
    en=fw(RANKING[key]); assert len(en)<=14
    d[o:o+16]=en.ljust(16,b'\0'); o+=0x20
# ---- 3. full-width name strings into CRI ADXF error-message text (NOT the "AFS" magic at 0x1D25B8) ----
SEGS=[[0x1d2104,0x1d25b4],[0x1d25c0,0x1d2868]]   # keep 0x1d25b4..0x1d25c0 ("AFS\0" at 0x1d25b8) untouched
assert bytes(d[0x1d25b8:0x1d25bc])==b'AFS\0'
uniq=[]
for tab,names in TABLES:
    for s in names:
        if s not in uniq: uniq.append(s)
enc={s:fw(s) for s in uniq}
# suffix sharing: a string whose encoding is a suffix of a longer one points into it
order=sorted(uniq,key=lambda s:-len(enc[s]))
cache={}; placed=[]
for s in order:
    b=enc[s]
    host=next((h for h in placed if enc[h].endswith(b)),None)
    if host is not None:
        cache[s]=cache[host]+len(enc[host])-len(b); continue
    need=len(b)+1
    for seg in SEGS:
        st=(seg[0]+3)&~3
        if st+need<=seg[1]:
            d[st:st+need]=b+b'\0'; cache[s]=o2v(st); seg[0]=st+need; break
    else: raise SystemExit('pool full at '+s)
    placed.append(s)
for tab,names in TABLES:
    n=len(names)
    for i in range(n):
        p,=struct.unpack_from('<I',d,v2o(tab)+4*i); assert 0x8a1d000<=p<0x8a1e000,(hex(tab),i)
    p,=struct.unpack_from('<I',d,v2o(tab)+4*n); assert not (0x8a1d000<=p<0x8a1e000),(hex(tab),'longer table')
    for i,s in enumerate(names):
        assert nchars(s)<=(9 if tab==0x8a1da80 else 8),s
        assert cache[s]%2==0
        struct.pack_into('<I',d,v2o(tab)+4*i,cache[s])
assert bytes(d[0x1d25b4:0x1d25c0])==orig[0x1d25b4:0x1d25c0]
print('segments left',[(hex(a),b-a) for a,b in SEGS],'strings placed',len(placed),'shared',len(uniq)-len(placed))
# clear the remainder of the used pool tail? keep remaining ADX text as is (still NUL-terminated strings)
# ---- emit patch list ----
patch=[]; i=0; n=len(d)
while i<n:
    if d[i]!=orig[i]:
        j=i
        while j<n and (d[j]!=orig[j] or (j+1<n and d[j+1]!=orig[j+1])): j+=1
        patch.append(dict(file_off=i,orig_sha1=hashlib.sha1(orig[i:j]).hexdigest(),new_hex=bytes(d[i:j]).hex())); i=j
    else: i+=1
for p in patch:
    a=p['file_off']; b=a+len(p['new_hex'])//2
    # forbidden regions from the first task
    assert not (a<0x088D24B8-0x8804000+0x54 and b>0x088D23CC-0x8804000+0x54)
json.dump(patch,open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'eboot_patch.json'),'w'),indent=0)
open(P.stage('eboot_v03_names.elf'),'wb').write(d)
print(len(patch),'patch runs', sum(len(p['new_hex'])//2 for p in patch),'bytes')
