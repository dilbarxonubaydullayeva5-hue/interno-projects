# tools/vp_extract.py <file.html>
import json,sys
t=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
i=t.find('"analysis_score"'); start=t.rfind('{',0,i)
for _ in range(20):
    j=t.rfind('{',0,start)
    if 'values_u8' in t[j:i]: break
    start=j
d=0
for p in range(start,len(t)):
    if t[p]=='{': d+=1
    elif t[p]=='}':
        d-=1
        if d==0: o=json.loads(t[start:p+1]); break
print(o['scores'])
for r in o['regions']: print(r['id'],[round(x,2) for x in r['values_by_frame']],'peak',r['peak_second'])
