#!/usr/bin/env python3
"""Stage 1 of the EBOOT build: write translations/eboot_strings.json into a copy of the decrypted EBOOT.
Each string is written in place at its file offset and zero-padded to its byte budget (the original slot
length); the original bytes are verified by sha1 first, so a wrong/modified input is rejected.
usage: insert_strings.py <decrypted_EBOOT> <out.elf> [--strings translations/eboot_strings.json]"""
import os, sys, json, argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from gseed import paths as P
from gseed.hashing import sha1

def insert(buf, strings):
    bad = []
    for x in strings:
        o, n = x['file_off'], x['budget']
        if sha1(buf[o:o + n]) != x['orig_sha1']: bad.append(x['id']); continue
        e = x['en'].encode('ascii')
        if len(e) > n: raise ValueError('string %d longer than its budget (%d > %d)' % (x['id'], len(e), n))
        buf[o:o + n] = e + b'\0' * (n - len(e))
    if bad: raise ValueError('%d strings did not match their original bytes (first ids %s) - is this the decrypted ULJM05238 EBOOT?' % (len(bad), bad[:5]))
    return buf

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('inp'); ap.add_argument('out')
    ap.add_argument('--strings', default=os.path.join(P.ROOT, 'translations', 'eboot_strings.json'))
    a = ap.parse_args()
    s = json.load(open(a.strings))['strings']
    b = insert(bytearray(open(a.inp, 'rb').read()), s)
    open(a.out, 'wb').write(b); print('inserted %d strings -> %s' % (len(s), a.out))
