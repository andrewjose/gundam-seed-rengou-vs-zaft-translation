#!/usr/bin/env python3
"""Set string keys (e.g. TITLE) in a PSP PARAM.SFO in place.

Usage: sfo_set_title.py PARAM.SFO "New Title" [--key TITLE] [-o out.sfo]

PSF layout: header (magic \\0PSF, version, key_table_off, data_table_off, count),
then `count` 16-byte index entries:
  u16 key_off, u16 fmt, u32 len, u32 max_len, u32 data_off
fmt 0x0204 = null-terminated UTF-8. We rewrite inside max_len, so no
offsets move and the file size is unchanged.
"""
import argparse, struct, sys


def parse(buf):
    magic, ver, koff, doff, n = struct.unpack_from("<4sIIII", buf, 0)
    if magic != b"\0PSF":
        sys.exit("not a PSF/SFO file")
    entries = []
    for i in range(n):
        ko, fmt, ln, mx, do = struct.unpack_from("<HHIII", buf, 20 + 16 * i)
        end = buf.index(b"\0", koff + ko)
        key = buf[koff + ko:end].decode("ascii")
        entries.append(dict(i=i, key=key, fmt=fmt, len=ln, max=mx, off=doff + do))
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sfo")
    ap.add_argument("value")
    ap.add_argument("--key", default="TITLE")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    buf = bytearray(open(a.sfo, "rb").read())
    for e in parse(buf):
        if e["key"] != a.key:
            continue
        if e["fmt"] != 0x0204:
            sys.exit(f"{a.key} is not a UTF-8 string (fmt {e['fmt']:#x})")
        data = a.value.encode("utf-8") + b"\0"
        if len(data) > e["max"]:
            sys.exit(f"value is {len(data)} bytes, max is {e['max']}")
        buf[e["off"]:e["off"] + e["max"]] = data.ljust(e["max"], b"\0")
        struct.pack_into("<I", buf, 20 + 16 * e["i"] + 4, len(data))
        open(a.out or a.sfo, "wb").write(buf)
        print(f"{a.key}: {a.value!r} ({len(data)}/{e['max']} bytes)")
        return
    sys.exit(f"key {a.key} not found")


if __name__ == "__main__":
    main()
