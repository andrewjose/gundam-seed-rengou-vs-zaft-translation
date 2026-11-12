import sys,re,os
# SJIS run: 2-byte sequences lead 81-9f/e0-ef, trail 40-7e/80-fc ; min 4 chars
pat=re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\x20-\x7e]){4,}')
def runs(d):
    out=[]
    for m in pat.finditer(d):
        s=m.group()
        try: t=s.decode('cp932')
        except: continue
        jp=sum(1 for c in t if ord(c)>0x3000)
        if jp>=3: out.append((m.start(),t))
    return out
if __name__=='__main__':
    for fn in sys.argv[1:]:
        d=open(fn,'rb').read(); r=runs(d)
        if r: print(len(r),sum(len(t) for _,t in r),os.path.basename(fn),'|',r[0][1][:40],'|',r[len(r)//2][1][:40])
