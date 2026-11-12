"""LZ codec used by Gundam SEED Rengou vs ZAFT Portable (ULJM05238) pack sub-files.

Format (all little-endian):
  u32  decompressed size
  then groups: u16 control word, followed by 16 items (bits consumed MSB first).
    bit 0 -> literal: copy next 2 bytes (one 16-bit word) to output
    bit 1 -> match token v = u16:
               L = v >> 11       (length in 16-bit words, 1..31)
               D = v & 0x7FF     (distance in 16-bit words, 1..2047)
               if L == 0: an extra u16 follows (no control bit) giving L (words)
             copy L*2 bytes from out[-D*2] (overlapping allowed, byte-wise)
               if D == 0 and L > 0: write L*2 zero bytes (zero fill)
               if D == 0 and L == 0 (i.e. words 0x0000 0x0000): END of stream
  The game's decoder (0x088D24E4) ignores the size word and stops only at the
  END token; the size word is used by the loader for buffer sizing.
  Word copies are 16-bit (lhu/sh), equivalent to byte-wise overlapping copy.
"""
import struct

def decompress(b, return_consumed=False, strict=True):
    """Faithful port of the game's routine at 0x088D24E4 (called with src+4).
    Stops at the end token (match, L field 0, extended L 0, D 0)."""
    size = struct.unpack_from('<I', b, 0)[0]
    p = 4
    out = bytearray()
    while True:
        ctl = b[p] | (b[p+1] << 8); p += 2
        done = False
        for bit in range(15, -1, -1):
            v = b[p] | (b[p+1] << 8); p += 2
            if (ctl >> bit) & 1:
                L = v >> 11; D = (v & 0x7FF) * 2
                if L == 0:
                    L = b[p] | (b[p+1] << 8); p += 2
                L *= 2
                if D == 0:
                    if L == 0:
                        done = True; break
                    out += bytes(L)          # zero fill
                    continue
                if D > len(out):
                    raise ValueError('bad distance %d at out=%d in=%d' % (D, len(out), p))
                s = len(out) - D
                if D >= L:
                    out += out[s:s+L]
                else:
                    for k in range(L):
                        out.append(out[s+k])
            else:
                out.append(v & 0xFF); out.append(v >> 8)
        if done: break
    if len(out) == size + 1 and size & 1:
        del out[size:]
    if strict and len(out) != size:
        raise ValueError('size mismatch: header %d, decoded %d' % (size, len(out)))
    if return_consumed:
        return bytes(out), p
    return bytes(out)


def compress(data, level=1):
    """Greedy LZ encoder producing a stream the game decoder accepts.
    level=0: literal-only. level=1: greedy hash-chain matching on 16-bit words."""
    size = len(data)
    src = data + (b'\0' if size & 1 else b'')
    nw = len(src) // 2
    words = [src[2*i] | (src[2*i+1] << 8) for i in range(nw)]
    out = bytearray(struct.pack('<I', size))
    items = []  # list of (flag, [u16 words])
    i = 0
    MAXD = 0x7FF; MAXL = 0xFFFF
    head = {}
    prev = [-1] * nw
    def insert(k):
        if k + 1 < nw:
            key = (words[k], words[k+1])
            prev[k] = head.get(key, -1)
            head[key] = k
    while i < nw:
        bestL = 0; bestD = 0
        if level and i + 1 < nw:
            key = (words[i], words[i+1])
            c = head.get(key, -1); tries = 0
            while c >= 0 and i - c <= MAXD and tries < 64:
                L = 2
                lim = min(MAXL, nw - i)
                while L < lim and words[c+L] == words[i+L]:
                    L += 1
                if L > bestL:
                    bestL, bestD = L, i - c
                    if L == lim: break
                c = prev[c]; tries += 1
        if level:
            z = 0
            while i + z < nw and z < MAXL and words[i+z] == 0:
                z += 1
            if z >= 2 and z > bestL:
                bestL, bestD = z, 0
        if bestL >= 2:
            if bestL <= 31:
                items.append((1, [(bestL << 11) | bestD]))
            else:
                items.append((1, [bestD, bestL]))
            for k in range(i, i + bestL):
                insert(k)
            i += bestL
        else:
            items.append((0, [words[i]]))
            insert(i)
            i += 1
    items.append((1, [0, 0]))   # END token
    for g in range(0, len(items), 16):
        grp = items[g:g+16]
        ctl = 0
        for j, (f, _) in enumerate(grp):
            if f: ctl |= 1 << (15 - j)
        out += struct.pack('<H', ctl)
        for f, ws in grp:
            for w in ws: out += struct.pack('<H', w)
    return bytes(out)


def compress_opt(data, tries=64):
    """Optimal-parse encoder (minimises output size). Same stream format as compress()."""
    size = len(data)
    src = data + (b'\0' if size & 1 else b'')
    nw = len(src) // 2
    words = [src[2*i] | (src[2*i+1] << 8) for i in range(nw)]
    MAXD = 0x7FF; MAXL = 0xFFFF
    head = {}; prev = [-1] * nw
    Lm = [0] * nw; Dm = [0] * nw
    # zero runs (computed backward)
    zr = [0] * (nw + 1)
    for i in range(nw - 1, -1, -1):
        zr[i] = zr[i+1] + 1 if words[i] == 0 else 0
    pL = 0; pD = 0
    for i in range(nw):
        bestL = 0; bestD = 0
        if pL > 2 and pD > 0:            # continuation of previous match
            bestL = pL - 1; bestD = pD
        if i + 1 < nw:
            key = (words[i], words[i+1])
            c = head.get(key, -1); t = 0
            lim = min(MAXL, nw - i)
            while c >= 0 and i - c <= MAXD and t < tries:
                if bestL >= lim: break
                if bestL < 2 or words[c + bestL] == words[i + bestL]:
                    L = 2
                    while L < lim and words[c+L] == words[i+L]:
                        L += 1
                    if L > bestL:
                        bestL, bestD = L, i - c
                c = prev[c]; t += 1
            prev[i] = head.get(key, -1); head[key] = i
        z = zr[i]
        if z > MAXL: z = MAXL
        if z >= 2 and z > bestL:
            bestL, bestD = z, 0
        Lm[i] = bestL; Dm[i] = bestD
        pL, pD = (bestL, bestD) if bestD else (0, 0)
    INF = 1 << 60
    cost = [0] * (nw + 1); choice = [0] * nw
    for i in range(nw - 1, -1, -1):
        best = 17 + cost[i+1]; ch = 1
        L = Lm[i]
        if L >= 2:
            m = min(L, 31)
            seg = cost[i+2:i+m+1]
            v = min(seg)
            if 17 + v < best:
                best = 17 + v; ch = seg.index(v) + 2
            if L >= 32:
                seg = cost[i+32:i+L+1]
                v = min(seg)
                if 33 + v < best:
                    best = 33 + v; ch = seg.index(v) + 32
        cost[i] = best; choice[i] = ch
    items = []
    i = 0
    while i < nw:
        ch = choice[i]
        if ch == 1:
            items.append((0, [words[i]])); i += 1
        else:
            D = Dm[i]
            if ch <= 31: items.append((1, [(ch << 11) | D]))
            else: items.append((1, [D, ch]))
            i += ch
    items.append((1, [0, 0]))
    out = bytearray(struct.pack('<I', size))
    for g in range(0, len(items), 16):
        grp = items[g:g+16]
        ctl = 0
        for j, (f, _) in enumerate(grp):
            if f: ctl |= 1 << (15 - j)
        out += struct.pack('<H', ctl)
        for f, ws in grp:
            for w in ws: out += struct.pack('<H', w)
    return bytes(out)
