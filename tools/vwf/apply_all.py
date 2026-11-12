#!/usr/bin/env python3
"""Apply the chosen VWF items to eboot_v03d.elf -> eboot_v04.elf (asserting original bytes, no overlaps).
usage: apply_all.py [--items 1,2,3,3b] [in.elf] [out.elf]
  1  = name tags (pilot/unit-name glyph system)           item1/patch.json
  2  = message box: proportional ASCII + Yes/No           item2/patch.json
  3  = battle dialogue VWF  (+ AFS 1677: item3/afs_1677.bin)   item3/patch.json
  3b = tutorial captions VWF (+ AFS 10: item3/afs_10.bin)      item3/patch_tut.json
  A  = SELECT A PILOT big name (needs 1)                  itemA/patch.json
  B  = Yes/No labels centred in their boxes (needs 2)     itemB/patch.json
  A2 = SELECT A PILOT big name, draw callback 0x0899D314 (needs 1)  itemA2/patch.json
Input: <work>/stage/eboot_v03d.elf (build it with: apply_patch.py <after-strings.elf> <out> patches/stages/eboot_v03d.json).
The matching atlases (AFS 1677 / 10) are built by atlas_vwf.py."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys,json,os,argparse
H=os.path.dirname(os.path.abspath(__file__))
ITEMS={'1':['item1/patch.json'],'2':['item2/patch.json'],'3':['item3/patch.json'],'3b':['item3/patch_tut.json'],
       'A':['itemA/patch.json'],'B':['itemB/patch.json'],'A2':['itemA2/patch.json']}
DEPS={'A':['1'],'B':['2'],'A2':['1']}   # A/B were made against eboot_v04 (1,2,3,3b applied) and patch into the caves of 1/2
LAYERED={'A','B','A2'}
AFS={}   # atlases: see atlas_vwf.py
OFF_LIMITS=[(0xCE420,0xCE50C,'proportional-font patch 0x088D2330'),(0x1D25B4,0x1D25C0,'"AFS\\0" magic')]
ap=argparse.ArgumentParser(); ap.add_argument('--items',default='1,2,3,3b,A,B,A2')
ap.add_argument('inp',nargs='?',default=P.stage('eboot_v03d.elf'))
ap.add_argument('out',nargs='?',default=None)
a=ap.parse_args()
sel=a.items.split(',')
for it in sel:
    for dep in DEPS.get(it,[]): assert dep in sel and sel.index(dep)<sel.index(it),'item %s needs item %s first'%(it,dep)
if a.out is None: a.out=P.stage('eboot_v041.elf' if 'A2' in sel else 'eboot_v041a.elf' if LAYERED&set(sel) else 'eboot_v04.elf')
d=bytearray(open(a.inp,'rb').read()); n0=len(d)
used=[]
for it in a.items.split(','):
    for pj in ITEMS[it]:
        for p in json.load(open(os.path.join(H,pj))):
            o=p['file_off']; nb=bytes.fromhex(p['new_hex'])
            assert hashlib.sha1(bytes(d[o:o+len(nb)])).hexdigest()==p['orig_sha1'],'orig mismatch at 0x%x (%s)'%(o,pj)
            for s,e,why in OFF_LIMITS: assert not (o<e and o+len(nb)>s),'touches %s'%why
            if it not in LAYERED:
                for s,e,w in used: assert not (o<e and o+len(nb)>s),'overlap %s with %s at 0x%x'%(pj,w,o)
            used.append((o,o+len(nb),pj))
            d[o:o+len(nb)]=nb
assert len(d)==n0 and d[0x1D25B8:0x1D25BC]==b'AFS\0'
open(a.out,'wb').write(d)
print('items',a.items,'->',a.out,'(%d patch runs)'%len(used))
for it in a.items.split(','):
    for idx,p in AFS.get(it,{}).items(): print('  install AFS %d <- %s'%(idx,os.path.join(H,p)))
