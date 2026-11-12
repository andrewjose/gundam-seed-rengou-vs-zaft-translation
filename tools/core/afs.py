import struct,sys,os,collections
def read(path):
    f=open(path,'rb'); d=f.read(8); n=struct.unpack('<I',d[4:8])[0]
    tab=struct.unpack('<%dI'%(2*n+2),f.read(8*n+8))
    ents=[(tab[2*i],tab[2*i+1]) for i in range(n)]
    nameoff,namelen=tab[2*n],tab[2*n+1]
    names=None
    if nameoff and namelen:
        f.seek(nameoff); nd=f.read(namelen); names=[]
        for i in range(n):
            r=nd[i*48:i*48+48]; names.append(r[:32].split(b'\0')[0].decode('ascii','replace'))
    return f,ents,names
if __name__=='__main__':
    path,out=sys.argv[1],sys.argv[2]
    f,ents,names=read(path); os.makedirs(out,exist_ok=True)
    mag=collections.Counter()
    with open(out+'/_index.tsv','w') as idx:
        for i,(o,s) in enumerate(ents):
            f.seek(o); d=f.read(s)
            nm=names[i] if names else ''
            m=d[:4]
            key=m.hex() if not all(32<=c<127 for c in m) else m.decode()
            mag[key]+=1
            fn='%04d_%s'%(i,nm or 'f')+'.bin'
            if sys.argv[3:]==['x']: open(out+'/'+fn,'wb').write(d)
            idx.write('%d\t%s\t%d\t%d\t%s\n'%(i,nm,o,s,key))
    print('names' if names else 'nonames',len(ents)); print(mag.most_common(40))
