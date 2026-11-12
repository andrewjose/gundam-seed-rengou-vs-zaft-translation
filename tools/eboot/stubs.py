from common import *
import struct
st=0x89d3a6c; names={}
for e in range(st,st+0x1f4,20):
    name,ver,attr,ln,nv,nids,stubs=struct.unpack('<IHHBBHII',rd(e,20))[:7] if False else (None,)*7
    raw=rd(e,20)
    namep,ver,attr,ln,nv,nf=struct.unpack('<IHHBBH',raw[:12]); nidp,stubp=struct.unpack('<II',raw[12:20])
    nm=cstr(namep) if namep else '?'
    for k in range(nf):
        nid=w32(nidp+4*k); s=stubp+8*k
        print('%08x %s %08x'%(s,nm,nid))
