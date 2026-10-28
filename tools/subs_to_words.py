# tools/subs_to_words.py <W> <texts.txt> [fps] — word timings from burned-in word-by-word subtitles
# needs $W/txt.txt (white-pixel YAVG per frame of subtitle strip) and $W/chunks.txt ("from to" per chunk)
import json,sys,statistics as st
W=sys.argv[1]; T=[l.strip() for l in open(sys.argv[2],encoding='utf-8') if l.strip()]
fps=float(sys.argv[3]) if len(sys.argv)>3 else 24
v=[float(l.split('=')[1]) for l in open(f'{W}/txt.txt') if 'YAVG' in l]
ch=[tuple(map(int,l.split())) for l in open(f'{W}/chunks.txt')]
assert len(ch)==len(T),(len(ch),len(T))
words=[];caps=[]
for (a,b),t in zip(ch,T):
    ws=t.split()
    m=[]
    for r in [a]+[i for i in range(a+1,b+1) if v[i]-v[i-1]>0.55]:
        if not m or r-m[-1]>2: m.append(r)
    fb=len(m)!=len(ws)
    if fb:
        tot=sum(len(w) for w in ws); dur=b-a+1; acc=0; m=[]
        for w in ws: m.append(a+round(acc/tot*dur*0.7)); acc+=len(w)
    for i,w in enumerate(ws):
        e=m[i+1] if i+1<len(m) else b+1
        words.append({"w":w.lower(),"from":m[i],"to":e,"approx":fb})
    caps.append({"text":t,"from":a,"to":b+1,"wordFrames":m,"approx":fb})
json.dump(words,open(f'{W}/words.json','w'),ensure_ascii=False)
json.dump(caps,open(f'{W}/captions.json','w'),ensure_ascii=False,indent=1)
n=len(words); dur=(ch[-1][1]-ch[0][0])/fps
print(n,'words',round(dur,1),'s',round(n/dur*60),'wpm; chunks',len(ch),'approx',sum(c['approx'] for c in caps))
cl=[(b-a+1)/fps for a,b in ch]; print('chunk sec median',round(st.median(cl),2),'max',round(max(cl),2))
gaps=[(ch[i+1][0]-ch[i][1]-1)/fps for i in range(len(ch)-1)]
print('silences>=0.25s:',sum(g>=0.25 for g in gaps),'mean',round(st.mean([g for g in gaps if g>=0.25]),2),'max',round(max(gaps),2))
print('words/s on screen median',round(st.median([len(t.split())/((b-a+1)/fps) for (a,b),t in zip(ch,T)]),2))
