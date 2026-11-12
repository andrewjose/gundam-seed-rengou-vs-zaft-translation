import struct
def objects(d):
    n,=struct.unpack_from('<I',d,4)
    offs=list(struct.unpack_from('<%dI'%n,d,0x20))
    return offs
def parse_obj(d,o,end=None):
    """returns dict with name, header floats, cmd list start, vtype, prims, vertices (list of (u,v,x,y,z)) and vertex file offset"""
    name=d[o+0x60:o+0x70].split(b'\0')[0].decode()
    hdr=struct.unpack_from('<24f',d,o)
    c=o+0x100
    base=c; vaddr=None; vtype=None; prims=[]; cmds=[]
    while True:
        w,=struct.unpack_from('<I',d,c); cmd=w>>24; p=w&0xffffff
        cmds.append((c,cmd,p))
        if cmd==0x01: vaddr=base+p
        elif cmd==0x12: vtype=p
        elif cmd==0x04: prims.append(((p>>16)&7,p&0xffff))
        elif cmd==0x0b: break
        c+=4
        if c-o>0x10000: raise Exception('runaway')
    nv=sum(n for t,n in prims)
    tc=vtype&3; col=(vtype>>2)&7; nrm=(vtype>>5)&3; pos=(vtype>>7)&3
    assert tc==2 and pos==2 and nrm==0 and (vtype>>9)==0, hex(vtype)
    csz={0:0,4:2,5:2,6:2,7:4}[col]
    vs=4+csz+6
    verts=[]
    for i in range(nv):
        b=vaddr+vs*i
        u,v=struct.unpack_from('<HH',d,b); x,y,z=struct.unpack_from('<hhh',d,b+4+csz)
        verts.append((u,v,x,y,z))
    return dict(vsize=vs if True else 0,name=name,off=o,hdr=hdr,vaddr=vaddr,vtype=vtype,prims=prims,verts=verts,cmds=cmds,cmdend=c)

def build_obj(hdr_bytes, prims, sx, sy, sz=1.0):
    """hdr_bytes: original 0x100 header. prims: list of vertex lists [(u,v,x,y,z),...] each drawn as a triangle strip.
    Returns object bytes (padded to 16) with bounding sphere recomputed (vtype 0x102)."""
    h=bytearray(hdr_bytes)
    allv=[v for p in prims for v in p]
    xs=[v[2]*sx/32768 for v in allv]; ys=[v[3]*sy/32768 for v in allv]; zs=[v[4]*sz/32768 for v in allv]
    cx=(min(xs)+max(xs))/2; cy=(min(ys)+max(ys))/2; cz=(min(zs)+max(zs))/2
    rad=((max(xs)-min(xs))**2+(max(ys)-min(ys))**2+(max(zs)-min(zs))**2)**.5/2
    struct.pack_into('<4f',h,0x40,cx,cy,cz,rad)
    n=len(prims)
    cmdlen=4*(5+n+2)
    cmds=[0x14<<24,0x10<<24,0x02<<24,(0x01<<24)|cmdlen,(0x12<<24)|0x102]
    cmds+=[(0x04<<24)|(4<<16)|len(p) for p in prims]
    cmds+=[0x13<<24,0x0b<<24]
    out=bytes(h)+struct.pack('<%dI'%len(cmds),*cmds)
    for p in prims:
        for v in p: out+=struct.pack('<HHhhh',*v)
    out+=b'\0'*((-len(out))%16)
    return out

def build_file(orig, objs):
    """orig: original PMF2 bytes (for header). objs: list of object bytes."""
    n=len(objs)
    head=bytearray(orig[:0x20])
    struct.pack_into('<I',head,4,n)
    tab=0x20+4*n; tab+= (-tab)%16
    out=bytearray(head)+b'\0'*(tab-0x20)
    offs=[]
    for ob in objs:
        offs.append(len(out)); out+=ob
    struct.pack_into('<%dI'%n,out,0x20,*offs)
    return bytes(out)
