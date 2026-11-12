import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import json,struct,sys
NORMALIZE = {'\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"', '\u2026': '...', '\u2014': '-', '\u2013': '-',
             '\uff01': '!', '\uff1f': '?', '\u3000': ' ', '\u00e9': 'e'}   # curly quotes, ellipsis, dashes, full-width !?/space
def clean(s):
    t=''.join(NORMALIZE.get(c,c) for c in s)
    return ''.join(c if 32<=ord(c)<127 else '?' for c in t)
def load(elf_path=P.stage('eboot_v03d.elf')):
    """Dialogue + tutorial lines: English from translations/eboot_strings.json, current location (after the
    v0.3 atlas re-layout) found through the pointer words that referenced the original string in the EBOOT."""
    items=json.load(open(os.path.join(P.ROOT,'translations','eboot_strings.json')))['strings']
    tl={str(x['id']):x['en'] for x in items}
    o=open(P.eboot_dec(),'rb').read(); d=open(elf_path,'rb').read()
    W={}
    for k in range(0x1d0758,len(o)-3,4): W.setdefault(struct.unpack_from('<I',o,k)[0],[]).append(k)
    out={'dialogue':[],'tutorial':[]}
    for x in items:
        x=dict(x,off=x['file_off'])
        if x['region']=='battle_dialogue': sys_='dialogue'
        elif 0x2AD900<=x['off']<0x2AE400: sys_='tutorial'
        else: continue
        va=x['off']-0x54+0x8804000
        ps=W.get(va,[])
        cur=sorted(set(struct.unpack_from('<I',d,p)[0] for p in ps))
        assert len(cur)==1,(x['id'],cur)
        a=cur[0]; fo=a-0x8804000+0x54
        s=d[fo:d.index(b'\0',fo)]
        en=clean(tl.get(str(x['id']),'')) or ' '
        out[sys_].append(dict(id=x['id'],va=a,fo=fo,cur=s.decode('ascii'),en=en,ptrs=ps))
    return out
