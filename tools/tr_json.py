# tools/tr_json.py  — python tools/tr_json.py <audio.pcm> <words.json> <lang> [model]
import json,sys,numpy as np
from faster_whisper import WhisperModel
m=WhisperModel(sys.argv[4] if len(sys.argv)>4 else "small",device="cpu",compute_type="int8")
a=np.frombuffer(open(sys.argv[1],"rb").read(),dtype="int16").astype("float32")/32768
segs,_=m.transcribe(a,language=sys.argv[3],word_timestamps=True)
json.dump([{"w":w.word.strip(),"s":round(w.start,3),"e":round(w.end,3)} for s in segs for w in s.words],open(sys.argv[2],"w"),ensure_ascii=False)
