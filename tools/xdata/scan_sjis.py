import os as _os, sys as _sys; _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))); from gseed import paths as P; import hashlib, os, sys
import os,glob,json,re,sys,collections
OUT=P.unpacked()
def is_lead(c): return 0x81<=c<=0x9f or 0xe0<=c<=0xfc
def runs(d,minchars=4):
    i=0;n=len(d);res=[]
    while i<n:
        j=i;chars=0;kana=0;kanji=0
        while j<n:
            c=d[j]
            if is_lead(c) and j+1<n and (0x40<=d[j+1]<=0xfc and d[j+1]!=0x7f):
                try: ch=d[j:j+2].decode('cp932')
                except: break
                o=ord(ch)
                if 0x3040<=o<=0x30ff: kana+=1
                elif 0x4e00<=o<=0x9fff: kanji+=1
                chars+=1;j+=2
            elif 0x20<=c<0x7f and chars>0: j+=1   # allow ascii inside
            else: break
        if chars>=minchars and (kana+kanji)>=chars*0.6 and kana>=2:
            res.append((i,d[i:j].decode('cp932','replace')))
            i=j
        else: i=max(j,i+1) if j>i else i+1
    return res
if __name__=='__main__':
    inv=[];per=collections.Counter()
    for fn in sorted(glob.glob(OUT+'/*.bin')):
        d=open(fn,'rb').read()
        for o,t in runs(d):
            inv.append({'file':os.path.basename(fn),'offset':o,'text':t}); per[os.path.basename(fn)]+=1
    json.dump(inv,open(P.work('text_inventory_raw.json'),'w'),ensure_ascii=False,indent=0)
    print(len(inv),len(per))
    for k,v in per.most_common(60): print(k,v)
