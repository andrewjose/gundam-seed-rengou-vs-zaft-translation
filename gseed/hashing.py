"""Hash-verified byte patches. Patch JSON = list of {file_off, orig_sha1, new_hex[, stage, note]}.
orig_sha1 = sha1 of the ORIGINAL bytes at [file_off, file_off+len(new)) so the patch carries no game bytes."""
import hashlib, json

def sha1(b): return hashlib.sha1(bytes(b)).hexdigest()

def sjis_sha1(s):
    """Key for a game string we may not store: sha1 of its Shift-JIS (cp932) bytes."""
    return sha1(s.encode('cp932'))

def check(buf, p):
    o = p['file_off'] if isinstance(p['file_off'], int) else int(p['file_off'], 0)
    n = len(p['new_hex']) // 2
    return o, n, sha1(buf[o:o + n]) == p['orig_sha1']

def apply(buf, patches, label='patch', allow_applied=False):
    """Apply in order; every run must match its orig_sha1 (or, with allow_applied, already equal new bytes)."""
    for p in patches:
        o, n, ok = check(buf, p)
        nb = bytes.fromhex(p['new_hex'])
        if not ok:
            if allow_applied and bytes(buf[o:o + n]) == nb: continue
            raise ValueError('%s: original bytes at 0x%x (len %d) do not match orig_sha1 - wrong input file?' % (label, o, n))
        buf[o:o + n] = nb
    return buf

def load(path):
    with open(path) as f: return json.load(f)
