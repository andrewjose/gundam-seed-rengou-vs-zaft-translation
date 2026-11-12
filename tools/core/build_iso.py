# usage: build_iso.py <src_iso> <dst_iso> <xdata_file> <eboot_file>   (dst must already be a full copy of src)
import sys,os,struct
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import isoreloc
src,dst,xd,eb=sys.argv[1:5]
assert os.path.getsize(dst)==os.path.getsize(src),'dst must be a complete copy of src'
recs=isoreloc.find_records(src)
xr_off,x_ext,x_len=recs['X_DATA.BIN']; dr_off,d_ext,d_len=recs['DUMMY.BIN']; y_ext=recs['Y_DATA.BIN'][1]
xs=os.path.getsize(xd); slot=(y_ext-x_ext)*2048
with open(dst,'r+b') as o, open(xd,'rb') as i:
    if xs<=slot: ext=x_ext
    else:
        assert xs<=d_len,'X_DATA too big even for DUMMY region'
        ext=d_ext; isoreloc.set_record(dst,dr_off,x_ext,min(d_len,slot)); print('relocated X_DATA into DUMMY region')
    o.seek(ext*2048)
    while True:
        c=i.read(8<<20)
        if not c: break
        o.write(c)
isoreloc.set_record(dst,xr_off,ext,xs)
# EBOOT
import pycdlib
iso=pycdlib.PyCdlib(); iso.open(src)
try: r=iso.get_record(iso_path='/PSP_GAME/SYSDIR/EBOOT.BIN')
except Exception: r=iso.get_record(iso_path='/PSP_GAME/SYSDIR/EBOOT.BIN;1')   # ISOs written with version suffixes
eo=r.extent_location()*2048; el=r.get_data_length(); iso.close()
e=open(eb,'rb').read(); assert len(e)==el
with open(dst,'r+b') as o: o.seek(eo); o.write(e)
print('X_DATA',xs,'at sector',ext,'(slot',slot,') ; EBOOT written')
