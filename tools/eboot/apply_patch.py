#!/usr/bin/env python3
"""Apply a hash-verified EBOOT patch (patches/eboot_v041.json or a stage patch list) to an ELF.
Accepted formats: {"runs":[...], "after_strings_sha1":..., "output_sha1":...} or a plain list of runs.
Each run = {file_off, orig_sha1, new_hex}; the bytes being replaced must hash to orig_sha1.
usage: apply_patch.py <in.elf> <out.elf> <patch.json> [<patch2.json> ...]"""
import os, sys, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from gseed.hashing import apply, sha1

def run(inp, out, patch_files):
    b = bytearray(open(inp, 'rb').read())
    for pf in patch_files:
        p = json.load(open(pf))
        runs = p['runs'] if isinstance(p, dict) else p
        if isinstance(p, dict) and p.get('after_strings_sha1') and sha1(b) != p['after_strings_sha1']:
            raise SystemExit('%s: input sha1 %s != expected %s (run insert_strings.py on the decrypted EBOOT first)'
                             % (pf, sha1(b), p['after_strings_sha1']))
        apply(b, runs, os.path.basename(pf))
        if isinstance(p, dict) and p.get('output_sha1'):
            assert sha1(b) == p['output_sha1'], 'output sha1 mismatch'
            print('%s: %d runs applied, output sha1 verified' % (pf, len(runs)))
        else:
            print('%s: %d runs applied' % (pf, len(runs)))
    open(out, 'wb').write(b)

if __name__ == '__main__':
    if len(sys.argv) < 4: raise SystemExit(__doc__)
    run(sys.argv[1], sys.argv[2], sys.argv[3:])
