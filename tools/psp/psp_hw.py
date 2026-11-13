#!/usr/bin/env python3
"""Make a patched ISO run on real PSP / Vita (Adrenaline) and optionally package it as a PSN-style EBOOT.PBP.

Steps (all in place on a copy of the built ISO, no file moves):
  --title TEXT      rewrite TITLE in /PSP_GAME/PARAM.SFO (inside its fixed slot; size unchanged)
  --sign-np PATH    fake-sign the decrypted EBOOT.BIN with `sign_np -elf` (tag 0, 0xD91609F0) and write it into
                    the EBOOT.BIN extent; only the directory record's size changes. Must fit the original sector run.
  --pbp OUT         build OUT (e.g. .../PSP/GAME/ULJM05238/EBOOT.PBP) with `sign_np -pbp -c` from the signed ISO.

Prints the ISO byte ranges that changed, for tools/chd/chdsplice.py --range.
sign_np is not included: build it from https://github.com/swarzesherz/sign_np (plain `make`, needs zlib).

usage: psp_hw.py ISO [--title T] [--sign-np BIN] [--pbp OUT] [--content-id ID]
"""
import argparse, os, struct, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sfo_set_title import parse as sfo_parse  # noqa: E402

SECTOR = 2048


def dir_records(iso, dirpath):
    """Return {name: (record_offset, extent, size)} for one directory (walks the ISO9660 path from the PVD)."""
    with open(iso, 'rb') as f:
        f.seek(16 * SECTOR); pvd = f.read(SECTOR)
        assert pvd[1:6] == b'CD001', 'not an ISO9660 image'
        root = pvd[156:156 + 34]
        ext, ln = struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0]
        for part in [p for p in dirpath.strip('/').split('/') if p]:
            recs = _read_dir(f, ext, ln)
            if part not in recs:
                sys.exit(f'{part} not found in ISO')
            _, ext, ln = recs[part]
        return _read_dir(f, ext, ln)


def _read_dir(f, ext, ln):
    f.seek(ext * SECTOR); data = f.read(ln); recs = {}; o = 0
    while o < len(data):
        L = data[o]
        if L == 0:
            o = (o // SECTOR + 1) * SECTOR; continue
        nl = data[o + 32]; name = data[o + 33:o + 33 + nl].decode('ascii', 'replace').split(';')[0]
        recs[name] = (ext * SECTOR + o, struct.unpack_from('<I', data, o + 2)[0], struct.unpack_from('<I', data, o + 10)[0])
        o += L
    return recs


def set_size(iso, rec_off, size):
    with open(iso, 'r+b') as f:
        f.seek(rec_off + 10); f.write(struct.pack('<I', size) + struct.pack('>I', size))


def set_title(iso, title, changed):
    off, ext, ln = dir_records(iso, '/PSP_GAME')['PARAM.SFO']
    with open(iso, 'r+b') as f:
        f.seek(ext * SECTOR); buf = bytearray(f.read(ln))
        e = next((e for e in sfo_parse(buf) if e['key'] == 'TITLE'), None)
        assert e and e['fmt'] == 0x0204, 'TITLE missing or not UTF-8'
        data = title.encode('utf-8') + b'\0'
        assert len(data) <= e['max'], f'title is {len(data)} bytes, slot is {e["max"]}'
        buf[e['off']:e['off'] + e['max']] = data.ljust(e['max'], b'\0')
        struct.pack_into('<I', buf, 20 + 16 * e['i'] + 4, len(data))
        f.seek(ext * SECTOR); f.write(buf)
    changed.append((ext * SECTOR, ln)); print(f'TITLE -> {title!r} ({len(data)}/{e["max"]} bytes)')


def sign_eboot(iso, sign_np, changed):
    off, ext, ln = dir_records(iso, '/PSP_GAME/SYSDIR')['EBOOT.BIN']
    with open(iso, 'rb') as f:
        f.seek(ext * SECTOR); elf = f.read(ln)
    if elf[:4] == b'~PSP':
        print('EBOOT.BIN is already signed/encrypted; skipping'); return
    assert elf[:4] == b'\x7fELF', 'EBOOT.BIN is neither ELF nor ~PSP'
    with tempfile.TemporaryDirectory() as td:
        i, o = os.path.join(td, 'in.elf'), os.path.join(td, 'out.bin')
        open(i, 'wb').write(elf)
        subprocess.run([sign_np, '-elf', i, o, '0'], check=True, stdout=subprocess.DEVNULL)
        signed = open(o, 'rb').read()
    assert signed[:4] == b'~PSP' and struct.unpack_from('<I', signed, 0x28)[0] == len(elf), 'unexpected sign_np output'
    slot = -(-ln // SECTOR) * SECTOR
    assert len(signed) <= slot, f'signed EBOOT ({len(signed)}) does not fit its {slot}-byte extent'
    with open(iso, 'r+b') as f:
        f.seek(ext * SECTOR); f.write(signed.ljust(slot, b'\0'))
    set_size(iso, off, len(signed))
    changed += [(ext * SECTOR, slot), (off // SECTOR * SECTOR, SECTOR)]
    print(f'EBOOT.BIN signed: {ln} -> {len(signed)} bytes (slot {slot})')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('--title')
    ap.add_argument('--sign-np', dest='sign_np')
    ap.add_argument('--pbp')
    ap.add_argument('--content-id', default='JP0000-ULJM05238_00-0000000000000000')
    a = ap.parse_args()
    changed = []
    if a.title:
        set_title(a.iso, a.title, changed)
    if a.sign_np:
        sign_eboot(a.iso, a.sign_np, changed)
    if a.pbp:
        assert a.sign_np, '--pbp needs --sign-np (the PBP must contain a signed EBOOT)'
        os.makedirs(os.path.dirname(os.path.abspath(a.pbp)), exist_ok=True)
        subprocess.run([a.sign_np, '-pbp', '-c', a.iso, a.pbp, a.content_id, '0'], check=True, stdout=subprocess.DEVNULL)
        with open(a.pbp, 'rb') as f:
            h = f.read(40); assert h[:4] == b'\0PBP'
            f.seek(struct.unpack_from('<I', h, 36)[0]); assert f.read(8) == b'NPUMDIMG'
        print(f'PBP: {a.pbp} ({os.path.getsize(a.pbp)} bytes)')
    if changed:
        print('chdsplice ranges:', ' '.join(f'--range {s}:{n}' for s, n in sorted(set(changed))))


if __name__ == '__main__':
    main()
