# tools/build_report.py <W> <thumb frames...> — fills report.tpl.html: {{img:x}}, {{passport}}, {{captions}}, {{thumbs}}
import sys,re,json,base64
W=sys.argv[1]; th=sys.argv[2:]
b64=lambda p:'data:image/jpeg;base64,'+base64.b64encode(open(p,'rb').read()).decode()
t=open(f'{W}/report.tpl.html',encoding='utf-8').read()
t=re.sub(r'\{\{img:([^}]+)\}\}',lambda m:b64(f'{W}/rep/{m.group(1)}'),t)
t=t.replace('{{passport}}',open(f'{W}/passport.json',encoding='utf-8').read())
t=t.replace('{{captions}}',json.dumps(json.load(open(f'{W}/captions.json',encoding='utf-8')),ensure_ascii=False))
t=t.replace('{{thumbs}}',json.dumps([b64(f'{W}/rep/s_{f}.jpg') for f in th]))
open(f'{W}/report.html','w',encoding='utf-8').write(t); print(len(t)//1024,'KB')
