"""Pack container used inside X_DATA.BIN (ULJM05238).
Layout:
  sector 0 (0x800 bytes): u32 N, then N u32 entries, rest zero-padded.
     entry = (flags << 30) | sector_count ; flags bit0 (0x40000000) = LZ-compressed
     entry == 0 -> empty slot (no data)
  sub-file data follows from 0x800, each occupying sector_count*0x800 bytes,
  in entry order; compressed blobs are zero-padded to the sector boundary.
  Header must fit in one sector (N <= 511); total size = (1+sum(sectors))*0x800.
"""
import struct
SECTOR = 0x800
FLAG_LZ = 0x40000000

def is_pack(d):
    if len(d) < 8 or len(d) % SECTOR: return False
    N = struct.unpack_from('<I', d, 0)[0]
    if N == 0 or 4 + 4*N > SECTOR: return False
    ent = struct.unpack_from('<%dI' % N, d, 4)
    if any(x >> 30 > 1 for x in ent): return False
    return (1 + sum(x & 0x3FFFFFFF for x in ent)) * SECTOR == len(d)

def parse(d):
    """returns list of dicts: {flags, sectors, offset, raw(bytes on disk incl. padding)}"""
    N = struct.unpack_from('<I', d, 0)[0]
    ent = struct.unpack_from('<%dI' % N, d, 4)
    pos = SECTOR; subs = []
    for x in ent:
        sc = x & 0x3FFFFFFF
        subs.append({'entry': x, 'flags': x >> 30, 'sectors': sc, 'offset': pos,
                     'raw': d[pos:pos + sc*SECTOR]})
        pos += sc * SECTOR
    return subs, d[4+4*N:SECTOR]
