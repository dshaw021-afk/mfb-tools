#!/usr/bin/env python3
import json,re,urllib.parse,urllib.request,time
from pathlib import Path
API="https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile"
def get(h):
  try:
    u=API+"?"+urllib.parse.urlencode({"actor":h})
    req=urllib.request.Request(u,headers={"User-Agent":"MFB-Handle-Probe/1.0"})
    with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
  except Exception:return None
def norm(s):return re.sub(r"[^a-z0-9]+"," ",(s or "").lower()).strip()
def compact(s):return re.sub(r"[^a-z0-9]","",(s or "").lower())
src=json.loads(Path("audit_sources.json").read_text())
out=[]
for i,s in enumerate(src,1):
  x=s["x_handle"].lstrip("@").lower()
  nw=[w for w in re.findall(r"[a-z0-9]+",s["name"].lower()) if w not in ("the","sports","nfl")]
  cand=[]
  def add(v):
    v=v.strip(".-")
    if v and len(v)<=63 and re.fullmatch(r"[a-z0-9-]+",v) and v not in cand:cand.append(v)
  if "_" not in x: add(x)
  add(x.replace("_",""))
  add(x.replace("_","-"))
  add("".join(nw))
  add("-".join(nw))
  found=[]
  for stem in cand[:5]:
    h=stem+".bsky.social"
    p=get(h)
    if p:
      dn=p.get("displayName") or ""
      desc=p.get("description") or ""
      score=0
      if norm(dn)==norm(s["name"]):score+=60
      xt=compact(s["x_handle"].lstrip("@"))
      if compact(stem)==xt:score+=35
      st=set(norm(s["name"]).split()); dt=set(norm(dn).split())
      if st: score+=round(25*len(st&dt)/len(st),1)
      if s["source_type"]=="Reporter" and any(k in desc.lower() for k in ["reporter","writer","editor","covers","covering","journalist","columnist","espn","athletic"]):score+=10
      found.append({"handle":h,"displayName":dn,"description":desc,"did":p.get("did"),"postsCount":p.get("postsCount"),"score":score})
    time.sleep(.03)
  found.sort(key=lambda z:z["score"],reverse=True)
  out.append({"source":s,"candidates":found[:5]})
  if i%40==0:print("probed",i,"/",len(src),flush=True)
Path("handle_probe_results.json").write_text(json.dumps(out,indent=2,ensure_ascii=False))
for r in out:
  if r["candidates"] and r["candidates"][0]["score"]>=70:
    c=r["candidates"][0]
    print("MATCH",r["source"]["index"],r["source"]["name"],"=>",c["handle"],c["score"],"|",(c.get("description") or "")[:150].replace("\n"," "))
