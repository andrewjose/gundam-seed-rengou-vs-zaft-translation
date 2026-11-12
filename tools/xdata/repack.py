#!/usr/bin/env python3
"""Rebuild pack containers (and optionally the AFS) for ULJM05238.

Library use:
    import repack
    new = repack.rebuild_pack(orig_pack_bytes, {sub_idx: new_decompressed_bytes, ...})
    # unchanged sub-files reuse their original on-disk bytes -> byte-identical if nothing changed
    # changed sub-files: recompressed with lz.compress if originally compressed (flag kept),
    #                    stored raw if originally stored. Sector counts are recomputed.
    repack.rebuild_afs(src_afs_path, {afs_idx: new_entry_bytes}, out_path)

CLI:
    repack.py pack <afs_idx> <out.bin> [sub_idx=file.bin ...]     (reads entry from X_DATA.BIN)
    repack.py afs <out_X_DATA.BIN> [afs_idx=file.bin ...]
    repack.py selftest       (rebuild every pack unchanged, check byte-identity; plus recompress test)
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lz, pack

SECTOR = 0x800
AFS_DEFAULT = P.xdata_orig()
# The loader decompresses from a fixed buffer at 0x08F31800+0x206000; keep an eye on
# decompressed sizes (game allocates by the u32 size word). Don't grow files wildly.

def pad(b, a=SECTOR):
    return b + b'\0' * ((-len(b)) % a)

def rebuild_pack(orig, replace=None, force_flags=None, compressor=None):
    """orig: original pack bytes. replace: {sub_idx: decompressed bytes or None(=make empty)}.
    force_flags: {sub_idx: 0|1} to override compression for a replaced sub-file."""
    replace = replace or {}; force_flags = force_flags or {}
    subs, hdr_tail = pack.parse(orig)
    N = len(subs)
    entries = []; body = bytearray()
    for i, s in enumerate(subs):
        if i in replace:
            data = replace[i]
            if data is None or len(data) == 0:
                entries.append(0); continue
            flags = force_flags.get(i, s['flags'] if s['sectors'] else 1)
            blob = (compressor or lz.compress)(data) if flags & 1 else data
            if flags & 1:
                assert lz.decompress(blob) == data, 'recompression self-check failed'
            raw = pad(blob)
        else:
            flags = s['flags']; raw = s['raw']
        sc = len(raw) // SECTOR
        entries.append(((flags & 3) << 30) | sc if sc else 0)
        body += raw
    hdr = struct.pack('<I%dI' % N, N, *entries)
    if 4 + 4 * N > SECTOR: raise ValueError('header overflow')
    # keep original header padding bytes when untouched (normally zero)
    hdr = hdr + hdr_tail if len(hdr) + len(hdr_tail) == SECTOR else pad(hdr)
    return bytes(hdr) + bytes(body)

def read_afs(path=AFS_DEFAULT):
    import afs
    f, ents, _ = afs.read(path)
    return f, ents

def rebuild_afs(src, replace, out):
    """Rewrite the AFS with replaced entries. Keeps the original header/table area size,
    entry order and 0x800 alignment. Unchanged entries copied verbatim; offsets shift as needed."""
    f, ents = read_afs(src)
    f.seek(0); head = f.read(ents[0][0])      # header + table + padding up to first entry
    N = len(ents)
    tail_ptr = struct.unpack_from('<II', head, 8 + 8 * N)  # name table ptr (0 in this game)
    newtab = []; pos = len(head)
    with open(out + '.tmp', 'wb') as o:
        o.write(head)
        for i, (off, size) in enumerate(ents):
            if i in replace: data = replace[i]
            else: f.seek(off); data = f.read(size)
            newtab.append((pos, len(data)))
            o.write(pad(data)); pos += len(pad(data))
        o.seek(8)
        for a, b in newtab: o.write(struct.pack('<II', a, b))
    os.replace(out + '.tmp', out)
    return newtab

def selftest():
    import random
    f, ents = read_afs()
    n = ok = 0
    for i, (off, size) in enumerate(ents):
        f.seek(off); d = f.read(size)
        if not pack.is_pack(d): continue
        n += 1
        if rebuild_pack(d) == d: ok += 1
        else: print('MISMATCH', i)
    print('unchanged packs rebuilt byte-identical: %d/%d' % (ok, n))
    # replace-with-same-content test: decompress + recompress every LZ sub-file of some packs
    random.seed(2); cnt = 0
    packs = [i for i, (off, size) in enumerate(ents) if size < 0x200000]
    for i in random.sample(packs, 60):
        off, size = ents[i]; f.seek(off); d = f.read(size)
        if not pack.is_pack(d): continue
        subs, _ = pack.parse(d)
        rep = {j: (lz.decompress(s['raw']) if s['flags'] & 1 else s['raw'])
               for j, s in enumerate(subs) if s['sectors']}
        new = rebuild_pack(d, rep)
        assert pack.is_pack(new)
        s2, _ = pack.parse(new)
        for j, s in enumerate(s2):
            if s['sectors']:
                got = lz.decompress(s['raw']) if s['flags'] & 1 else s['raw']
                assert got == rep[j], (i, j)
        cnt += 1
    print('recompressed packs verified (content round-trip): %d' % cnt)

if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] == 'selftest': selftest()
    elif a[0] == 'pack':
        f, ents = read_afs(); i = int(a[1]); off, size = ents[i]; f.seek(off); d = f.read(size)
        rep = {int(k): open(v, 'rb').read() for k, v in (x.split('=', 1) for x in a[3:])}
        open(a[2], 'wb').write(rebuild_pack(d, rep)); print('wrote', a[2])
    elif a[0] == 'afs':
        rep = {int(k): open(v, 'rb').read() for k, v in (x.split('=', 1) for x in a[2:])}
        rebuild_afs(AFS_DEFAULT, rep, a[1]); print('wrote', a[1])
