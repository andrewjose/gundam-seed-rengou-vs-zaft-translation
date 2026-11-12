#!/usr/bin/env python3
"""Build the translated text entries of X_DATA.BIN (missions AFS 174-473, unit descriptions AFS 172/173).

Inputs : your original X_DATA.BIN, translations/missions.json, translations/units.json (English only).
Output : <out_dir>/afs_<i>.bin for every changed entry (install them with tools/xdata/repack.py afs ...).

missions.json is keyed by AFS index + string slot (0..9). Mission files are re-packed: the strings are written
back-to-back in slot order inside the original string area and the 10-entry pointer table is rewritten.
units.json is keyed by sha1(Shift-JIS bytes of the original string): the u32 pointer table must keep every
original offset (moving strings crashes Arcade mode), so each English string is written over its original slot
and truncated to fit.

usage: insert_text.py [--xdata X_DATA.BIN] [--out DIR] [--check]
"""
import os, sys, json, struct, argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from gseed import paths as P
from gseed.hashing import sha1
from mission import parse
from afs import read as afsread

TL = os.path.join(P.ROOT, 'translations')

def build_mission(d, row, report):
    h, ptrs, strs = parse(d); start = ptrs[0]; end = h[3]
    assert len(strs) == len(row) == 10, ('unexpected slot count', len(strs))
    buf = bytearray(); newp = []
    for i, (s, en) in enumerate(zip(strs, row)):
        if bool(s) != bool(en): raise ValueError('slot %d: empty/non-empty mismatch' % i)
        newp.append(start + len(buf)); buf += en.encode('ascii') + b'\0'
    if len(buf) > end - start:
        report.append('overflow by %d bytes -> entry left untranslated' % (len(buf) - (end - start)))
        return None
    out = bytearray(d)
    out[start:end] = bytes(buf) + b'\0' * (end - start - len(buf))
    struct.pack_into('<%dI' % len(newp), out, h[3], *newp)
    return bytes(out)

def build_units(d, tl, report):
    n = struct.unpack('<I', d[:4])[0] // 4; ptrs = struct.unpack('<%dI' % n, d[:4 * n])
    out = bytearray(d); starts = sorted(set(ptrs)); miss = 0
    for k, p in enumerate(starts):
        nxt = starts[k + 1] if k + 1 < len(starts) else len(d)
        e = d.index(b'\0', p); s = d[p:e]
        if not s: continue
        key = sha1(s)
        if key not in tl:
            miss += 1; continue           # junk / control entries are not in the table: leave untouched
        b = tl[key].encode('ascii'); room = nxt - p - 1
        if len(b) > room:
            report.append('truncated %r to %d bytes' % (tl[key], room)); b = b[:room]
        out[p:nxt] = b + b'\0' * (nxt - p - len(b))
    return bytes(out), miss

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xdata', default=P.xdata_orig())
    ap.add_argument('--out', default=P.afs_new())
    a = ap.parse_args()
    missions = json.load(open(os.path.join(TL, 'missions.json')))['entries']
    units = json.load(open(os.path.join(TL, 'units.json')))['entries']
    f, ents, _ = afsread(a.xdata); os.makedirs(a.out, exist_ok=True)
    def entry(i): f.seek(ents[i][0]); return f.read(ents[i][1])
    nm = 0; rep = []
    for k, row in sorted(missions.items(), key=lambda kv: int(kv[0])):
        i = int(k); r = []
        b = build_mission(entry(i), row, r)
        if b is None: rep += ['AFS %d: %s' % (i, x) for x in r]; continue
        open(os.path.join(a.out, 'afs_%d.bin' % i), 'wb').write(b); nm += 1
    for k, tl in units.items():
        i = int(k); r = []
        b, miss = build_units(entry(i), tl, r)
        open(os.path.join(a.out, 'afs_%d.bin' % i), 'wb').write(b)
        rep += ['AFS %d: %s' % (i, x) for x in r]
        print('units AFS %d: %d strings translated, %d untouched entries' % (i, len(tl), miss))
    print('missions: %d entries written' % nm)
    for x in rep: print('  ' + x)

if __name__ == '__main__':
    main()
