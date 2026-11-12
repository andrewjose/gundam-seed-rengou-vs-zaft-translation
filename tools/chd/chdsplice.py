#!/usr/bin/env python3
"""Make a CHD for a new ISO from the CHD of an older ISO when only a few hunks changed.

Hunks whose data changed are recompressed. Everything else is copied as raw compressed
bytes, so this is much faster than a full encode. The map and the header SHA-1s are
rebuilt. Afterwards, check the result with chdverify.py --against new.iso.

usage: chdsplice.py old.chd new.iso out.chd --range START:LEN [--range ...] [--rawsha1 HEX]
"""
import argparse, hashlib, os, struct, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chdverify as cv
import iso2chd as ic


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('old_chd'); ap.add_argument('new_iso'); ap.add_argument('out')
    ap.add_argument('--rawsha1', help='SHA-1 of new_iso, if already known')
    ap.add_argument('--range', action='append', required=True, help='changed ISO bytes START:LEN (repeatable)')
    a = ap.parse_args()
    fo = open(a.old_chd, 'rb'); size = os.path.getsize(a.old_chd)
    hdr = cv.read_header(fo)
    hb = hdr['hunkbytes']
    if hdr['logicalbytes'] != os.path.getsize(a.new_iso):
        sys.exit('ISO size differs from the CHD logical size')
    meta = cv.read_metadata(fo, hdr['metaoffset'], size)
    entries, info = cv.decode_map(fo, hdr, size)
    if any(t not in (ic.COMPRESSION_TYPE_0, ic.COMPRESSION_NONE, ic.COMPRESSION_SELF)
           for t, *_ in entries):
        sys.exit('unsupported hunk types')

    def old_hunk(h):
        t, ln, off, crc = entries[h]
        if t == ic.COMPRESSION_SELF:
            return old_hunk(off)
        fo.seek(off); d = fo.read(ln)
        return d if t == ic.COMPRESSION_NONE else zlib.decompress(d, -15)

    # Changed hunks: the ones covering the byte ranges given with --range START:LEN.
    iso = open(a.new_iso, 'rb')
    changed = set()
    for r in a.range:
        s, n = (int(x, 0) for x in r.split(':'))
        changed.update(range(s // hb, (s + n - 1) // hb + 1))
    changed = sorted(changed)
    for h in changed:   # sanity: they really differ from the old CHD
        iso.seek(h * hb); d = iso.read(hb)
        print('hunk %d differs: %s' % (h, d != old_hunk(h)))
    print('changed hunks:', changed)
    chset = set(changed)

    # Build the new entry list; compressed data is contiguous in hunk order, so the output
    # is the old data region with the changed hunks' bytes swapped out (copied in big blocks).
    new_entries = []
    pieces = []          # ('old', start, end) or ('new', bytes)
    cur = info['firstoffs']
    run_start = None
    for h, (t, ln, off, crc) in enumerate(entries):
        if t == ic.COMPRESSION_SELF and off not in chset and h not in chset:
            new_entries.append((t, 0, off, 0)); continue
        if h in chset or (t == ic.COMPRESSION_SELF and off in chset):
            if run_start is not None:
                pieces.append(('old', run_start, run_end)); run_start = None
            iso.seek(h * hb); d = iso.read(hb); d += b'\0' * (hb - len(d))
            c = zlib.compressobj(9, zlib.DEFLATED, -15); comp = c.compress(d) + c.flush()
            if len(comp) >= hb:
                comp = d; new_entries.append((ic.COMPRESSION_NONE, hb, cur, ic.crc16(d)))
            else:
                new_entries.append((ic.COMPRESSION_TYPE_0, len(comp), cur, ic.crc16(d)))
            pieces.append(('new', comp)); cur += len(comp)
            continue
        if run_start is None:
            run_start = off
        elif off != run_end:
            pieces.append(('old', run_start, run_end)); run_start = off
        run_end = off + ln
        new_entries.append((t, ln, cur, crc)); cur += ln
    if run_start is not None:
        pieces.append(('old', run_start, run_end))
    print('pieces:', len(pieces))

    out = open(a.out + '.tmp', 'wb')
    out.write(b'\0' * ic.HEADER_SIZE)
    fo.seek(ic.HEADER_SIZE); out.write(fo.read(info['firstoffs'] - ic.HEADER_SIZE))
    for pc in pieces:
        if pc[0] == 'new':
            out.write(pc[1]); continue
        fo.seek(pc[1]); left = pc[2] - pc[1]
        while left:
            blk = fo.read(min(left, 16 << 20)); out.write(blk); left -= len(blk)
    # SELF entries must point at an earlier hunk that still holds the same data.
    for h, (t, ln, off, crc) in enumerate(new_entries):
        if t == ic.COMPRESSION_SELF:
            assert off < h and new_entries[off][0] != ic.COMPRESSION_SELF
    mapblob = ic.compress_v5_map(new_entries, hb, info['firstoffs'])
    out.write(mapblob)
    if a.rawsha1:
        rawsha1 = bytes.fromhex(a.rawsha1)
    else:
        s = hashlib.sha1(); iso.seek(0)
        for blk in iter(lambda: iso.read(8 << 20), b''):
            s.update(blk)
        rawsha1 = s.digest()
    sha1 = ic.overall_sha1(rawsha1, meta)
    out.seek(0)
    out.write(ic.build_header(hdr['logicalbytes'], cur, hdr['metaoffset'], hb, rawsha1, sha1))
    out.close(); os.replace(a.out + '.tmp', a.out)
    print('wrote %s: %d bytes, data SHA1 %s, CHD SHA1 %s' % (a.out, cur + len(mapblob), rawsha1.hex(), sha1.hex()))


if __name__ == '__main__':
    main()
