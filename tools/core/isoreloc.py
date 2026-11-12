# Patch ISO9660 directory records in place: set extent/size of files in /PSP_GAME/USRDIR.
import struct,pycdlib
def find_records(iso_path, dirpath='/PSP_GAME/USRDIR'):
    iso=pycdlib.PyCdlib(); iso.open(iso_path)
    d=iso.get_record(iso_path=dirpath); ext=d.extent_location(); ln=d.get_data_length(); iso.close()
    f=open(iso_path,'rb'); f.seek(ext*2048); data=f.read(ln); f.close()
    recs={}; o=0
    while o<len(data):
        L=data[o]
        if L==0: o=(o//2048+1)*2048; continue
        nl=data[o+32]; name=data[o+33:o+33+nl].decode('ascii','replace').split(';')[0]
        recs[name]=(ext*2048+o, struct.unpack_from('<I',data,o+2)[0], struct.unpack_from('<I',data,o+10)[0])
        o+=L
    return recs
def set_record(iso_path, rec_off, extent, size):
    with open(iso_path,'r+b') as f:
        f.seek(rec_off+2); f.write(struct.pack('<I',extent)+struct.pack('>I',extent)+struct.pack('<I',size)+struct.pack('>I',size))
if __name__=='__main__':
    import sys
    for k,v in find_records(sys.argv[1]).items(): print(k,hex(v[0]),v[1],v[2])
