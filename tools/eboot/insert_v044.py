#!/usr/bin/env python3
"""Stage 3 of the EBOOT build (v0.4.4+): on top of the tested v0.4.1 EBOOT (insert_strings.py + apply_patch.py
patches/eboot_v041.json, MD5 1667c483ad06c3cfbe3455389aba9ce9) write translations/eboot_strings_v044.json
(leftover Japanese, prompts, tutorial punctuation, the ad hoc "%s%s" composition and its two pointers) and the
item C code patch (tools/vwf/itemC/patch.json: proportional width estimate for 9 call sites).
Every write is checked against the sha1 of the bytes it replaces.
usage: insert_v044.py <v041.elf> <out.elf> [--no-itemC]"""
import os, sys, json, struct, argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from gseed import paths as P
from gseed.hashing import sha1, apply

def runs_from_text(doc):
    runs = []
    for s in doc['strings']:
        e = s['en'].encode('ascii')
        if len(e) + 1 > s['n']: raise ValueError('0x%x: %r needs %d bytes, slot has %d' % (s['file_off'], s['en'], len(e) + 1, s['n']))
        runs.append({'file_off': s['file_off'], 'orig_sha1': s['orig_sha1'], 'new_hex': (e + b'\0' * (s['n'] - len(e))).hex()})
    for b in doc['blobs']:
        buf = bytearray(b['n'])
        for off, t in b['parts']:
            e = t.encode('ascii'); assert off + len(e) < b['n']; buf[off:off + len(e)] = e
        runs.append({'file_off': b['file_off'], 'orig_sha1': b['orig_sha1'], 'new_hex': bytes(buf).hex()})
    for p in doc['pointers']:
        runs.append({'file_off': p['file_off'], 'orig_sha1': p['orig_sha1'], 'new_hex': struct.pack('<I', int(p['new_va'], 16)).hex()})
    return runs

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('inp'); ap.add_argument('out')
    ap.add_argument('--strings', default=os.path.join(P.ROOT, 'translations', 'eboot_strings_v044.json'))
    ap.add_argument('--no-itemC', action='store_true', help='leave out item C (for bisecting)')
    a = ap.parse_args()
    b = bytearray(open(a.inp, 'rb').read()); n0 = len(b)
    runs = runs_from_text(json.load(open(a.strings)))
    apply(b, runs, 'eboot_strings_v044.json')
    nc = 0
    if not a.no_itemC:
        c = json.load(open(os.path.join(P.TOOLS, 'vwf', 'itemC', 'patch.json')))
        apply(b, c, 'itemC/patch.json'); nc = len(c)
    assert len(b) == n0 and b[0x1D25B8:0x1D25BC] == b'AFS\0'
    open(a.out, 'wb').write(b)
    print('v0.4.4+ text: %d runs, item C: %d runs -> %s (sha1 %s)' % (len(runs), nc, a.out, sha1(b)))
