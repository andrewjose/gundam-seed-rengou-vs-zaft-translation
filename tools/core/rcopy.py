import os,sys,time
src,dst=sys.argv[1],sys.argv[2]; t=time.time()
n=os.path.getsize(src); have=os.path.getsize(dst) if os.path.exists(dst) else 0
with open(src,'rb') as a, open(dst,'ab') as b:
    a.seek(have)
    while have<n and time.time()-t<165:
        c=a.read(8<<20); b.write(c); have+=len(c)
print(have,n,'DONE' if have==n else 'PARTIAL')
