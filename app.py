from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pathlib import Path
import subprocess, tempfile, json, re, uuid

app=FastAPI(title="ClipForge AI")
ROOT=Path(__file__).parent
JOBS=ROOT/"jobs"; JOBS.mkdir(exist_ok=True)

def run(cmd):
    return subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=True)

def valid(url):
    return bool(re.match(r"^https?://(www\.)?(youtube\.com|youtu\.be)/",url.strip(),re.I))

def download(url,job):
    run(["yt-dlp","-f","bv*+ba/b","--merge-output-format","mp4","--no-playlist","-o",str(job/"source.%(ext)s"),url])
    p=job/"source.mp4"
    if p.exists(): return p
    xs=list(job.glob("source.*"))
    if not xs: raise RuntimeError("Video download failed.")
    return xs[0]

def transcribe(video):
    import whisper
    return whisper.load_model("base").transcribe(str(video),fp16=False)["segments"]

def score(s):
    t=re.sub(r"\s+"," ",s["text"]).strip().lower()
    score=45
    words=["why","how","secret","mistake","never","truth","crazy","imagine","problem","actually","nobody","best","worst","learned","realized","because","but","important"]
    score+=min(24,sum(2 for w in words if w in t))
    n=len(t.split())
    if 8<=n<=85: score+=10
    if "?" in t: score+=5
    if "!" in t: score+=4
    d=s["end"]-s["start"]
    if 18<=d<=55: score+=10
    return min(100,score)

def pick(segs,n):
    pool=[]
    for i,s in enumerate(segs):
        st=max(0,s["start"]-2); en=s["end"]+3; j=i+1
        while j<len(segs) and en-st<48 and segs[j]["start"]-en<1.5:
            en=segs[j]["end"]+1;j+=1
        en=min(en,st+58)
        s2={"start":st,"end":en,"text":" ".join(x["text"].strip() for x in segs[i:j])}
        pool.append((score(s2),s2))
    pool.sort(key=lambda x:x[0],reverse=True)
    out=[]
    for sc,s in pool:
        if any(max(0,min(s["end"],o["end"])-max(s["start"],o["start"])) / max(1,max(s["end"],o["end"])-min(s["start"],o["start"]))>.45 for _,o in out): continue
        out.append((sc,s))
        if len(out)>=n: break
    return out

def cut(video,st,en,out):
    vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    run(["ffmpeg","-y","-ss",str(st),"-i",str(video),"-t",str(en-st),"-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-movflags","+faststart",str(out)])

@app.get("/",response_class=HTMLResponse)
def home(): return (ROOT/"index.html").read_text()

@app.post("/api/analyze")
def analyze(url:str=Form(...),clips:int=Form(5)):
    if not valid(url): return JSONResponse({"error":"Paste a valid YouTube link."},400)
    job=JOBS/uuid.uuid4().hex;job.mkdir()
    try:
        video=download(url,job)
        segs=transcribe(video)
        picks=pick(segs,max(1,min(10,clips)))
        result=[]
        for i,(sc,s) in enumerate(picks,1):
            out=job/f"clip_{i:02d}.mp4";cut(video,s["start"],s["end"],out)
            result.append({"id":i,"score":sc,"start":round(s["start"],1),"end":round(s["end"],1),"text":s["text"],"download":f"/api/download/{job.name}/{out.name}"})
        return {"clips":result}
    except Exception as e:
        return JSONResponse({"error":str(e)[:500]},500)

@app.get("/api/download/{job}/{filename}")
def dl(job,filename):
    p=JOBS/job/filename
    if not p.exists() or p.suffix!=".mp4": return JSONResponse({"error":"Not found"},404)
    return FileResponse(p,media_type="video/mp4",filename=filename)
