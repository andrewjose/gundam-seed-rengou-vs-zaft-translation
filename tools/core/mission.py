import struct,sys,os,json
def parse(d):
    h=struct.unpack('<5I',d[:20])
    t=h[3]; ptrs=[]
    o=t
    while o+4<=len(d):
        p=struct.unpack('<I',d[o:o+4])[0]
        if p==0 or p>=t: break
        ptrs.append(p); o+=4
    strs=[]
    for p in ptrs:
        e=d.index(b'\0',p); strs.append(d[p:e].decode('cp932'))
    return h,ptrs,strs
if __name__=='__main__':
    ok=bad=0; res={}
    for line in open('scan_text.txt'):
        fn=line.split()[2]
        if fn in('0172_f.bin','0173_f.bin','EBOOT.BIN'): continue
        d=open('x_data/'+fn,'rb').read()
        try:
            h,p,s=parse(d)
            assert len(p)>=3 and p[0]>=0x14
            res[fn]=s; ok+=1
        except Exception as e: bad+=1; print('BAD',fn,h if 'h' in dir() else '',e)
    print(ok,bad); json.dump(res,open('missions_raw.json','w'),ensure_ascii=False,indent=0)
    from collections import Counter
    print(Counter(len(v) for v in res.values()))
