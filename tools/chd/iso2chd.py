#!/usr/bin/env python3
"""iso2chd.py - convert a 2048-byte-sector ISO (PSP UMD, DVD) into a CHD v5 file.

Pure Python 3.10+ standard library (zlib, hashlib, struct, binascii, threading).
Output is equivalent to `chdman createdvd -hs 2048 -c zlib`:

  * CHD v5 header, compressors = [zlib, none, none, none]
  * hunkbytes = 2048 by default (--hunk N, any multiple of 2048), unitbytes = 2048
  * 'DVD ' metadata entry (1 byte, 0x00, checksummed) exactly like chdman
  * per-hunk type: zlib (raw deflate, level 9), uncompressed (when deflate does
    not shrink the hunk), or self-reference (duplicate of an earlier hunk)
  * compressed v5 map (huffman-coded types with RLE, lengths/offsets/crc16s),
    as decoded by MAME's chd_file::decompress_v5_map / libchdr
  * rawsha1 / sha1 computed the same way chdman does

File layout (same as chdman): header | metadata | hunk data | map.

Usage: python3 iso2chd.py input.iso output.chd [--hunk 2048] [--threads N]
"""
import argparse
import binascii
import hashlib
import os
import struct
import sys
import time
import zlib
from concurrent.futures import ThreadPoolExecutor

UNIT_BYTES = 2048
HEADER_SIZE = 124

# v5 map compression types (MAME chd.h / libchdr)
COMPRESSION_TYPE_0 = 0
COMPRESSION_NONE = 4
COMPRESSION_SELF = 5
COMPRESSION_PARENT = 6
COMPRESSION_RLE_SMALL = 7
COMPRESSION_RLE_LARGE = 8
COMPRESSION_SELF_0 = 9
COMPRESSION_SELF_1 = 10

CHD_MDFLAGS_CHECKSUM = 0x01
DVD_METADATA_TAG = b'DVD '

MAP_HUFF_CODES = 16
MAP_HUFF_MAXBITS = 8


def crc16(data):
    """CRC-16/CCITT-FALSE, as chd_crc16 (poly 0x1021, init 0xffff)."""
    return binascii.crc_hqx(data, 0xFFFF)


# --------------------------------------------------------------------------
# Bit writer (MSB-first, matching libchdr's bitstream reader)
# --------------------------------------------------------------------------
class BitWriter:
    def __init__(self):
        self.out = bytearray()
        self.acc = 0
        self.nbits = 0

    def write(self, value, numbits):
        if numbits == 0:
            return
        self.acc = (self.acc << numbits) | (value & ((1 << numbits) - 1))
        self.nbits += numbits
        while self.nbits >= 8:
            self.nbits -= 8
            self.out.append((self.acc >> self.nbits) & 0xFF)
        self.acc &= (1 << self.nbits) - 1

    def flush(self):
        if self.nbits:
            self.out.append((self.acc << (8 - self.nbits)) & 0xFF)
            self.acc = 0
            self.nbits = 0
        return bytes(self.out)


# --------------------------------------------------------------------------
# Huffman encoder side of libchdr's huffman_decoder (16 codes, 8 max bits)
# --------------------------------------------------------------------------
def _huffman_lengths(freqs):
    import heapq
    syms = [(f, i) for i, f in enumerate(freqs) if f > 0]
    lengths = [0] * len(freqs)
    if len(syms) == 1:
        lengths[syms[0][1]] = 1          # root-only tree: MAME gives it 1 bit
        return lengths
    heap = [(f, n, [i]) for n, (f, i) in enumerate(syms)]
    heapq.heapify(heap)
    counter = len(heap)
    while len(heap) > 1:
        f1, _, s1 = heapq.heappop(heap)
        f2, _, s2 = heapq.heappop(heap)
        for s in s1 + s2:
            lengths[s] += 1
        heapq.heappush(heap, (f1 + f2, counter, s1 + s2))
        counter += 1
    return lengths


def huffman_code_lengths(freqs, maxbits):
    total = sum(freqs)
    floor = 0
    while True:
        adj = [max(f, floor) if f > 0 else 0 for f in freqs]
        lengths = _huffman_lengths(adj)
        if max(lengths) <= maxbits:
            return lengths
        floor = max(1, floor * 2 if floor else total >> 10)


def canonical_codes(lengths):
    """Exactly huffman_assign_canonical_codes()."""
    bithisto = [0] * 33
    for l in lengths:
        bithisto[l] += 1
    curstart = 0
    for codelen in range(32, 0, -1):
        nextstart = (curstart + bithisto[codelen]) >> 1
        if codelen != 1 and nextstart * 2 != curstart + bithisto[codelen]:
            raise ValueError('huffman tree not complete')
        bithisto[codelen] = curstart
        curstart = nextstart
    codes = [0] * len(lengths)
    for i, l in enumerate(lengths):
        if l > 0:
            codes[i] = bithisto[l]
            bithisto[l] += 1
    return codes


def export_tree_rle(bw, lengths, maxbits):
    """Inverse of huffman_import_tree_rle()."""
    numbits = 5 if maxbits >= 16 else (4 if maxbits >= 8 else 3)
    i = 0
    n = len(lengths)
    while i < n:
        value = lengths[i]
        j = i
        while j < n and lengths[j] == value:
            j += 1
        count = j - i
        i = j
        while count > 0:
            if value == 1:                   # literal 1 is escaped as 1,1
                bw.write(1, numbits)
                bw.write(1, numbits)
                count -= 1
            elif count >= 3:
                rep = min(count, 3 + (1 << numbits) - 1)
                bw.write(1, numbits)
                bw.write(value, numbits)
                bw.write(rep - 3, numbits)
                count -= rep
            else:
                bw.write(value, numbits)
                count -= 1


# --------------------------------------------------------------------------
# Map compression (encoder for decompress_v5_map)
# --------------------------------------------------------------------------
def compress_v5_map(entries, hunkbytes, firstoffs):
    """entries: list of (type, length, offset, crc) with type in
    {TYPE_0, NONE, SELF}; offset = file offset (TYPE_0/NONE) or hunk index (SELF).
    Returns the complete map blob (16-byte header + bitstream)."""
    hunkcount = len(entries)

    # raw (decoded) map for the CRC, and promoted type symbols
    rawmap = bytearray(12 * hunkcount)
    symbols = []
    last_self = 0
    max_complen = 0
    max_self = 0
    for h, (t, length, offset, crc) in enumerate(entries):
        struct.pack_into('>B', rawmap, h * 12, t)
        rawmap[h * 12 + 1:h * 12 + 4] = length.to_bytes(3, 'big')
        rawmap[h * 12 + 4:h * 12 + 10] = offset.to_bytes(6, 'big')
        rawmap[h * 12 + 10:h * 12 + 12] = crc.to_bytes(2, 'big')
        if t == COMPRESSION_SELF:
            if offset == last_self:
                sym = COMPRESSION_SELF_0
            elif offset == last_self + 1:
                sym = COMPRESSION_SELF_1
            else:
                sym = COMPRESSION_SELF
                max_self = max(max_self, offset)
            last_self = offset
        else:
            sym = t
            if t == COMPRESSION_TYPE_0:
                max_complen = max(max_complen, length)
        symbols.append(sym)
    mapcrc = crc16(bytes(rawmap))

    # RLE-encode the type stream into huffman symbols
    stream = []
    i = 0
    lastcomp = 0
    while i < hunkcount:
        sym = symbols[i]
        j = i
        while j < hunkcount and symbols[j] == sym:
            j += 1
        run = j - i
        i = j
        if sym != lastcomp:
            stream.append(sym)
            lastcomp = sym
            run -= 1
        while run > 0:
            if run < 3:
                stream.append(sym)
                run -= 1
            elif run <= 3 + 15:
                stream.append(COMPRESSION_RLE_SMALL)
                stream.append(run - 3)
                run = 0
            else:
                this = min(run, 3 + 16 + 255)
                v = this - 3 - 16
                stream.append(COMPRESSION_RLE_LARGE)
                stream.append(v >> 4)
                stream.append(v & 15)
                run -= this

    freqs = [0] * MAP_HUFF_CODES
    for s in stream:
        freqs[s] += 1
    lengths = huffman_code_lengths(freqs, MAP_HUFF_MAXBITS)
    codes = canonical_codes(lengths)

    lengthbits = max_complen.bit_length()
    selfbits = max_self.bit_length()
    parentbits = 0

    bw = BitWriter()
    export_tree_rle(bw, lengths, MAP_HUFF_MAXBITS)
    for s in stream:
        bw.write(codes[s], lengths[s])
    for h, (t, length, offset, crc) in enumerate(entries):
        sym = symbols[h]
        if sym == COMPRESSION_TYPE_0:
            bw.write(length, lengthbits)
            bw.write(crc, 16)
        elif sym == COMPRESSION_NONE:
            bw.write(crc, 16)
        elif sym == COMPRESSION_SELF:
            bw.write(offset, selfbits)
        # SELF_0 / SELF_1 carry no extra bits
    blob = bw.flush()
    hdr = struct.pack('>I', len(blob)) + firstoffs.to_bytes(6, 'big') + \
        struct.pack('>HBBBB', mapcrc, lengthbits, selfbits, parentbits, 0)
    return hdr + blob


# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
def build_header(logicalbytes, mapoffset, metaoffset, hunkbytes, rawsha1, sha1):
    return (b'MComprHD' + struct.pack('>II', HEADER_SIZE, 5) +
            b'zlib' + b'\0' * 12 +
            struct.pack('>QQQII', logicalbytes, mapoffset, metaoffset,
                        hunkbytes, UNIT_BYTES) +
            rawsha1 + sha1 + b'\0' * 20)


def overall_sha1(rawsha1, metadata):
    """chd_file::compute_overall_sha1: SHA1(rawsha1 || sorted(tag || sha1(data)))."""
    hashes = sorted(tag + hashlib.sha1(data).digest()
                    for tag, flags, data in metadata if flags & CHD_MDFLAGS_CHECKSUM)
    return hashlib.sha1(rawsha1 + b''.join(hashes)).digest()


# --------------------------------------------------------------------------
# Worker: per-batch hunk processing (zlib releases the GIL)
# --------------------------------------------------------------------------
def process_batch(buf, hunkbytes):
    res = []
    mv = memoryview(buf)
    for pos in range(0, len(buf), hunkbytes):
        hunk = mv[pos:pos + hunkbytes]
        key = hashlib.sha1(hunk).digest()
        c = zlib.compressobj(9, zlib.DEFLATED, -15)
        comp = c.compress(hunk) + c.flush()
        if len(comp) >= hunkbytes:
            comp = None
        res.append((key, crc16(hunk), comp))
    return res


def convert(src, dst, hunkbytes=2048, threads=None, quiet=False):
    if hunkbytes <= 0 or hunkbytes % UNIT_BYTES or hunkbytes > (1 << 24) - 1:
        raise ValueError('hunk size must be a positive multiple of 2048 below 16 MiB')
    logicalbytes = os.path.getsize(src)
    if logicalbytes == 0:
        raise ValueError('input is empty')
    if logicalbytes % UNIT_BYTES and not quiet:
        print('warning: input size is not a multiple of 2048; last sector zero-padded',
              file=sys.stderr)
    hunkcount = (logicalbytes + hunkbytes - 1) // hunkbytes
    threads = threads or os.cpu_count() or 1
    batch_hunks = max(1, (1 << 20) // hunkbytes)     # ~1 MiB per task

    metadata = [(DVD_METADATA_TAG, CHD_MDFLAGS_CHECKSUM, b'\0')]
    metaoffset = HEADER_SIZE
    metablob = bytearray()
    off = metaoffset
    for n, (tag, flags, data) in enumerate(metadata):
        nxt = off + 16 + len(data) if n + 1 < len(metadata) else 0
        metablob += tag + bytes([flags]) + len(data).to_bytes(3, 'big') + \
            struct.pack('>Q', nxt) + data
        off += 16 + len(data)
    firstoffs = metaoffset + len(metablob)

    t0 = time.time()
    rawsha = hashlib.sha1()
    entries = []
    seen = {}
    stats = {'zlib': 0, 'none': 0, 'self': 0}
    curoffset = firstoffs
    done = 0
    last_pct = -1

    with open(src, 'rb') as fin, open(dst, 'wb') as fout, \
            ThreadPoolExecutor(max_workers=threads) as pool:
        fout.write(b'\0' * HEADER_SIZE)
        fout.write(metablob)
        pending = []
        eof = False

        def submit():
            nonlocal eof
            if eof:
                return False
            buf = fin.read(batch_hunks * hunkbytes)
            if not buf:
                eof = True
                return False
            rawsha.update(buf)
            if len(buf) % hunkbytes:
                buf += b'\0' * (hunkbytes - len(buf) % hunkbytes)
            pending.append((buf, pool.submit(process_batch, buf, hunkbytes)))
            return True

        for _ in range(threads * 3):
            if not submit():
                break
        while pending:
            buf, fut = pending.pop(0)
            submit()
            for i, (key, crc, comp) in enumerate(fut.result()):
                h = len(entries)
                ref = seen.get(key)
                if ref is not None:
                    entries.append((COMPRESSION_SELF, 0, ref, 0))
                    stats['self'] += 1
                    continue
                seen[key] = h
                if comp is not None:
                    fout.write(comp)
                    entries.append((COMPRESSION_TYPE_0, len(comp), curoffset, crc))
                    curoffset += len(comp)
                    stats['zlib'] += 1
                else:
                    fout.write(buf[i * hunkbytes:(i + 1) * hunkbytes])
                    entries.append((COMPRESSION_NONE, hunkbytes, curoffset, crc))
                    curoffset += hunkbytes
                    stats['none'] += 1
            done = len(entries)
            pct = done * 100 // hunkcount
            if not quiet and pct != last_pct and (pct % 2 == 0 or done == hunkcount):
                last_pct = pct
                el = time.time() - t0
                mbps = done * hunkbytes / 1048576 / el if el > 0 else 0
                ratio = curoffset * 100.0 / max(1, done * hunkbytes)
                print('\r  %3d%%  %d/%d hunks  %.1f MiB/s  ratio %.1f%%   ' %
                      (pct, done, hunkcount, mbps, ratio), end='', flush=True)
        if not quiet:
            print()
        assert len(entries) == hunkcount, (len(entries), hunkcount)

        mapoffset = curoffset
        mapblob = compress_v5_map(entries, hunkbytes, firstoffs)
        fout.write(mapblob)
        rawsha1 = rawsha.digest()
        sha1 = overall_sha1(rawsha1, metadata)
        fout.seek(0)
        fout.write(build_header(logicalbytes, mapoffset, metaoffset, hunkbytes,
                                rawsha1, sha1))
        total = mapoffset + len(mapblob)

    el = time.time() - t0
    if not quiet:
        print('hunks: %d (zlib %d, uncompressed %d, self-copy %d)' %
              (hunkcount, stats['zlib'], stats['none'], stats['self']))
        print('output: %d bytes (%.1f%% of %d)' % (total, total * 100.0 / logicalbytes,
                                                     logicalbytes))
        print('data SHA1: %s   CHD SHA1: %s' % (rawsha1.hex(), sha1.hex()))
        print('total time: %.1f s (%.1f MiB/s)' % (el, logicalbytes / 1048576 / max(el, 1e-9)))
    return rawsha1, sha1


def main():
    ap = argparse.ArgumentParser(description='Convert a 2048-byte-sector ISO to CHD v5 '
                                 '(like chdman createdvd -hs 2048 -c zlib).')
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('--hunk', type=int, default=2048,
                    help='hunk size in bytes, multiple of 2048 (default 2048; chdman '
                         'createdvd default is 4096)')
    ap.add_argument('--threads', type=int, default=0,
                    help='compression threads (default: CPU count)')
    ap.add_argument('-q', '--quiet', action='store_true')
    a = ap.parse_args()
    if os.path.abspath(a.input) == os.path.abspath(a.output):
        ap.error('input and output are the same file')
    try:
        convert(a.input, a.output, a.hunk, a.threads or None, a.quiet)
    except (ValueError, OSError) as e:
        print('error: %s' % e, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
