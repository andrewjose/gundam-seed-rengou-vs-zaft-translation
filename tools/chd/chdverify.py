#!/usr/bin/env python3
"""chdverify.py - independent pure-Python CHD v5 reader/verifier (libchdr logic).

Checks: header, metadata chain, map decode (huffman + RLE) and map CRC16,
every hunk decompressed (zlib/raw-deflate, uncompressed, self, parent=error)
with its per-hunk CRC16, the data SHA1 against header rawsha1, the overall
SHA1 against header sha1, and optionally the bytes against a source ISO.

Usage: python3 chdverify.py file.chd [--against input.iso] [--extract out.iso]
"""
import argparse
import binascii
import hashlib
import struct
import sys
import time
import zlib

COMPRESSION_TYPE_0, COMPRESSION_TYPE_1, COMPRESSION_TYPE_2, COMPRESSION_TYPE_3 = 0, 1, 2, 3
COMPRESSION_NONE, COMPRESSION_SELF, COMPRESSION_PARENT = 4, 5, 6
COMPRESSION_RLE_SMALL, COMPRESSION_RLE_LARGE = 7, 8
COMPRESSION_SELF_0, COMPRESSION_SELF_1 = 9, 10
COMPRESSION_PARENT_SELF, COMPRESSION_PARENT_0, COMPRESSION_PARENT_1 = 11, 12, 13


class VerifyError(Exception):
    pass


def crc16(data):
    return binascii.crc_hqx(data, 0xFFFF)


class BitReader:
    """Mirror of libchdr bitstream: MSB-first, zero-fill past the end."""
    def __init__(self, data):
        self.data = data
        self.pos = 0          # bit position

    def read(self, n):
        if n == 0:
            return 0
        v = 0
        p = self.pos
        need = n
        while need:
            byte_i = p >> 3
            b = self.data[byte_i] if byte_i < len(self.data) else 0
            avail = 8 - (p & 7)
            take = min(avail, need)
            bits = (b >> (avail - take)) & ((1 << take) - 1)
            v = (v << take) | bits
            p += take
            need -= take
        self.pos = p
        return v

    def peek(self, n):
        p = self.pos
        v = self.read(n)
        self.pos = p
        return v

    def overflow(self):
        return self.pos > len(self.data) * 8


class HuffmanDecoder:
    def __init__(self, numcodes, maxbits):
        self.numcodes = numcodes
        self.maxbits = maxbits
        self.lengths = [0] * numcodes

    def import_tree_rle(self, br):
        numbits = 5 if self.maxbits >= 16 else (4 if self.maxbits >= 8 else 3)
        cur = 0
        while cur < self.numcodes:
            nb = br.read(numbits)
            if nb != 1:
                self.lengths[cur] = nb
                cur += 1
            else:
                nb = br.read(numbits)
                if nb == 1:
                    self.lengths[cur] = 1
                    cur += 1
                else:
                    rep = br.read(numbits) + 3
                    if rep + cur > self.numcodes:
                        raise VerifyError('huffman RLE tree overruns code table')
                    for _ in range(rep):
                        self.lengths[cur] = nb
                        cur += 1
        self._build()
        if br.overflow():
            raise VerifyError('huffman tree: input too small')

    def _build(self):
        bithisto = [0] * 33
        for l in self.lengths:
            if l > self.maxbits:
                raise VerifyError('huffman code length exceeds maxbits')
            bithisto[l] += 1
        curstart = 0
        for codelen in range(32, 0, -1):
            nextstart = (curstart + bithisto[codelen]) >> 1
            if codelen != 1 and nextstart * 2 != curstart + bithisto[codelen]:
                raise VerifyError('huffman tree inconsistent (Kraft)')
            bithisto[codelen] = curstart
            curstart = nextstart
        size = 1 << self.maxbits
        self.lookup = [None] * size
        for sym, l in enumerate(self.lengths):
            if l > 0:
                code = bithisto[l]
                bithisto[l] += 1
                shift = self.maxbits - l
                start = code << shift
                end = ((code + 1) << shift)
                if end > size:
                    raise VerifyError('huffman lookup overflow')
                for k in range(start, end):
                    self.lookup[k] = (sym, l)

    def decode_one(self, br):
        ent = self.lookup[br.peek(self.maxbits)]
        if ent is None:
            raise VerifyError('invalid huffman code in map')
        br.pos += ent[1]
        return ent[0]


def read_header(f):
    f.seek(0)
    h = f.read(124)
    if len(h) < 16 or h[:8] != b'MComprHD':
        raise VerifyError('not a CHD file (bad magic)')
    length, version = struct.unpack('>II', h[8:16])
    if version != 5 or length != 124:
        raise VerifyError('only CHD v5 supported (version %d, header length %d)' % (version, length))
    comps = [h[16 + 4 * i:20 + 4 * i] for i in range(4)]
    logicalbytes, mapoffset, metaoffset, hunkbytes, unitbytes = struct.unpack('>QQQII', h[32:64])
    return {
        'compressors': comps, 'logicalbytes': logicalbytes, 'mapoffset': mapoffset,
        'metaoffset': metaoffset, 'hunkbytes': hunkbytes, 'unitbytes': unitbytes,
        'rawsha1': h[64:84], 'sha1': h[84:104], 'parentsha1': h[104:124],
    }


def read_metadata(f, offset, filesize):
    out = []
    seen = set()
    while offset:
        if offset in seen or offset + 16 > filesize:
            raise VerifyError('bad metadata chain at %d' % offset)
        seen.add(offset)
        f.seek(offset)
        raw = f.read(16)
        tag = raw[:4]
        flags = raw[4]
        length = int.from_bytes(raw[5:8], 'big')
        nxt = struct.unpack('>Q', raw[8:16])[0]
        data = f.read(length)
        if len(data) != length:
            raise VerifyError('truncated metadata')
        out.append((tag, flags, data))
        offset = nxt
    return out


def decode_map(f, hdr, filesize):
    hunkbytes, unitbytes = hdr['hunkbytes'], hdr['unitbytes']
    hunkcount = (hdr['logicalbytes'] + hunkbytes - 1) // hunkbytes
    f.seek(hdr['mapoffset'])
    raw = f.read(16)
    mapbytes = struct.unpack('>I', raw[0:4])[0]
    firstoffs = int.from_bytes(raw[4:10], 'big')
    mapcrc = struct.unpack('>H', raw[10:12])[0]
    lengthbits, selfbits, parentbits = raw[12], raw[13], raw[14]
    if max(lengthbits, selfbits, parentbits) > 32:
        raise VerifyError('map field widths > 32')
    if hdr['mapoffset'] + mapbytes >= filesize:
        raise VerifyError('map extends past end of file (libchdr check)')
    br = BitReader(f.read(mapbytes))
    dec = HuffmanDecoder(16, 8)
    dec.import_tree_rle(br)

    types = bytearray(hunkcount)
    repcount = 0
    lastcomp = 0
    for h in range(hunkcount):
        if repcount > 0:
            types[h] = lastcomp
            repcount -= 1
        else:
            if br.overflow():
                raise VerifyError('map type stream overflow')
            val = dec.decode_one(br)
            if val == COMPRESSION_RLE_SMALL:
                types[h] = lastcomp
                repcount = 2 + dec.decode_one(br)
            elif val == COMPRESSION_RLE_LARGE:
                types[h] = lastcomp
                repcount = 2 + 16 + (dec.decode_one(br) << 4)
                repcount += dec.decode_one(br)
            else:
                types[h] = lastcomp = val

    entries = []
    rawmap = bytearray()
    curoffset = firstoffs
    last_self = 0
    last_parent = 0
    for h in range(hunkcount):
        t = types[h]
        offset = curoffset
        length = 0
        crc = 0
        if t <= COMPRESSION_TYPE_3:
            length = br.read(lengthbits)
            curoffset += length
            crc = br.read(16)
        elif t == COMPRESSION_NONE:
            length = hunkbytes
            curoffset += length
            crc = br.read(16)
        elif t == COMPRESSION_SELF:
            last_self = offset = br.read(selfbits)
        elif t == COMPRESSION_PARENT:
            last_parent = offset = br.read(parentbits)
        elif t in (COMPRESSION_SELF_0, COMPRESSION_SELF_1):
            if t == COMPRESSION_SELF_1:
                last_self += 1
            t = COMPRESSION_SELF
            offset = last_self
        elif t == COMPRESSION_PARENT_SELF:
            t = COMPRESSION_PARENT
            last_parent = offset = h * hunkbytes // unitbytes
        elif t in (COMPRESSION_PARENT_0, COMPRESSION_PARENT_1):
            if t == COMPRESSION_PARENT_1:
                last_parent += hunkbytes // unitbytes
            t = COMPRESSION_PARENT
            offset = last_parent
        else:
            raise VerifyError('invalid map type %d at hunk %d' % (t, h))
        entries.append((t, length, offset, crc))
        rawmap += bytes([t]) + length.to_bytes(3, 'big') + offset.to_bytes(6, 'big') + \
            crc.to_bytes(2, 'big')
    if br.overflow():
        raise VerifyError('map bitstream overflow')
    if crc16(bytes(rawmap)) != mapcrc:
        raise VerifyError('map CRC16 mismatch (stored %04x, computed %04x)' %
                          (mapcrc, crc16(bytes(rawmap))))
    info = {'mapbytes': mapbytes, 'firstoffs': firstoffs, 'lengthbits': lengthbits,
            'selfbits': selfbits, 'parentbits': parentbits, 'mapcrc': mapcrc,
            'consumed_bits': br.pos}
    return entries, info


def verify(path, against=None, extract=None, quiet=False):
    t0 = time.time()
    with open(path, 'rb') as f:
        f.seek(0, 2)
        filesize = f.tell()
        hdr = read_header(f)
        hb, ub = hdr['hunkbytes'], hdr['unitbytes']
        if hb == 0 or ub == 0 or hb % ub:
            raise VerifyError('bad hunk/unit sizes %d/%d' % (hb, ub))
        if hdr['parentsha1'] != b'\0' * 20:
            raise VerifyError('CHD has a parent; not supported')
        comps = hdr['compressors']
        if comps[0] == b'\0\0\0\0':
            raise VerifyError('uncompressed CHD (raw map) not handled by this verifier')
        meta = read_metadata(f, hdr['metaoffset'], filesize)
        entries, minfo = decode_map(f, hdr, filesize)
        hunkcount = len(entries)
        if not quiet:
            print('CHD v5: logical %d bytes, hunk %d, unit %d, %d hunks, compressors %s' %
                  (hdr['logicalbytes'], hb, ub, hunkcount,
                   [c.decode('latin-1') for c in comps if c != b'\0\0\0\0']))
            for tag, flags, data in meta:
                print('metadata: tag %r flags %02x len %d data %r' %
                      (tag.decode('latin-1'), flags, len(data), data[:64]))
            print('map: %d bytes, firstoffs %d, lengthbits %d selfbits %d parentbits %d, '
                  'crc %04x OK' % (minfo['mapbytes'], minfo['firstoffs'], minfo['lengthbits'],
                                    minfo['selfbits'], minfo['parentbits'], minfo['mapcrc']))

        cache = {}       # hunk index -> data, only for hunks referenced by SELF
        needed = set(e[2] for e in entries if e[0] == COMPRESSION_SELF)
        counts = {}
        sha = hashlib.sha1()
        remaining = hdr['logicalbytes']
        src = open(against, 'rb') if against else None
        out = open(extract, 'wb') if extract else None
        try:
            for h, (t, length, offset, crc) in enumerate(entries):
                if t <= COMPRESSION_TYPE_3:
                    codec = comps[t]
                    if offset + length > filesize:
                        raise VerifyError('hunk %d data past EOF' % h)
                    f.seek(offset)
                    cdata = f.read(length)
                    if codec == b'zlib':
                        d = zlib.decompressobj(-15)
                        data = d.decompress(cdata, hb)
                        if len(data) != hb:
                            raise VerifyError('hunk %d: zlib produced %d bytes' % (h, len(data)))
                    else:
                        raise VerifyError('hunk %d: codec %r not supported by this verifier'
                                          % (h, codec))
                    if crc16(data) != crc:
                        raise VerifyError('hunk %d: CRC16 mismatch' % h)
                    name = codec.decode('latin-1')
                elif t == COMPRESSION_NONE:
                    f.seek(offset)
                    data = f.read(hb)
                    if len(data) != hb:
                        raise VerifyError('hunk %d: uncompressed data past EOF' % h)
                    if crc16(data) != crc:
                        raise VerifyError('hunk %d: CRC16 mismatch' % h)
                    name = 'none'
                elif t == COMPRESSION_SELF:
                    if offset >= h:
                        raise VerifyError('hunk %d: self reference to later hunk %d' % (h, offset))
                    data = cache.get(offset)
                    if data is None:
                        raise VerifyError('hunk %d: self reference to %d unavailable' % (h, offset))
                    name = 'self'
                else:
                    raise VerifyError('hunk %d: parent reference without parent' % h)
                counts[name] = counts.get(name, 0) + 1
                if h in needed:
                    cache[h] = data
                piece = data[:min(hb, remaining)]
                remaining -= len(piece)
                sha.update(piece)
                if src is not None:
                    ref = src.read(len(piece))
                    if ref != piece:
                        raise VerifyError('hunk %d differs from %s' % (h, against))
                if out is not None:
                    out.write(piece)
                if not quiet and (h % 8192 == 0 or h == hunkcount - 1):
                    print('\r  verifying %d/%d' % (h + 1, hunkcount), end='', flush=True)
            if src is not None and src.read(1):
                raise VerifyError('%s is longer than the CHD logical size' % against)
        finally:
            if src:
                src.close()
            if out:
                out.close()
        if not quiet:
            print()
        rawsha1 = sha.digest()
        if rawsha1 != hdr['rawsha1']:
            raise VerifyError('data SHA1 mismatch: header %s, computed %s' %
                              (hdr['rawsha1'].hex(), rawsha1.hex()))
        hashes = sorted(tag + hashlib.sha1(data).digest() for tag, flags, data in meta
                        if flags & 1)
        overall = hashlib.sha1(rawsha1 + b''.join(hashes)).digest()
        if overall != hdr['sha1']:
            raise VerifyError('overall SHA1 mismatch: header %s, computed %s' %
                              (hdr['sha1'].hex(), overall.hex()))
    if not quiet:
        print('hunk types: %s' % ', '.join('%s %d' % kv for kv in sorted(counts.items())))
        print('data SHA1 %s OK, overall SHA1 %s OK%s' %
              (rawsha1.hex(), overall.hex(),
               ', byte-identical to %s' % against if against else ''))
        print('verify time: %.1f s' % (time.time() - t0))
    return True


def main():
    ap = argparse.ArgumentParser(description='Verify a CHD v5 file (pure Python).')
    ap.add_argument('chd')
    ap.add_argument('--against', help='source ISO to compare byte-for-byte')
    ap.add_argument('--extract', help='write the decompressed image to this file')
    ap.add_argument('-q', '--quiet', action='store_true')
    a = ap.parse_args()
    try:
        verify(a.chd, a.against, a.extract, a.quiet)
    except (VerifyError, OSError, zlib.error) as e:
        print('\nFAILED: %s' % e, file=sys.stderr)
        sys.exit(1)
    print('OK')


if __name__ == '__main__':
    main()
