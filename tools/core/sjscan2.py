import sys,os,re
sys.path.insert(0,os.path.dirname(__file__))
from sjscan import runs
def good(t):
    k=sum(1 for c in t if '\u3040'<=c<='\u30ff' or c in '\u3001\u3002\uff01\uff1f\u300c\u300d\u30fc\u2026\u30fb\u3000')
    return len(t)>=5 and k/len(t)>=0.35
for fn in sys.argv[1:]:
    d=open(fn,'rb').read(); r=[(o,t) for o,t in runs(d) if good(t)]
    if len(r)>=3: print(len(r),sum(len(t) for _,t in r),os.path.basename(fn),len(d),d[:4].hex(),'|',r[0][1][:30],'|',r[-1][1][:30])
