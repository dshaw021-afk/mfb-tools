#!/usr/bin/env python3
import json,re,urllib.parse,urllib.request,time
from pathlib import Path
API="https://public.api.bsky.app/xrpc/"
def get(ep,params):
    u=API+ep+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(u,headers={"User-Agent":"MFB-Team-Verify/1.0"})
    try:
      with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
    except Exception as e:return {"_error":str(e)}
def links(o):
    s=json.dumps(o,ensure_ascii=False)
    return re.findall(r'https?://[^"\\s]+',s)
out=[]
for t in json.loads(Path("team_candidates.json").read_text()):
    arr=[]
    for h in t["candidates"]:
        p=get("app.bsky.actor.getProfile",{"actor":h})
        if "_error" in p:
            arr.append({"handle":h,"exists":False,"error":p["_error"]});continue
        f=get("app.bsky.feed.getAuthorFeed",{"actor":h,"limit":20,"filter":"posts_no_replies"})
        posts=[]
        if "_error" not in f:
            for item in f.get("feed",[]):
                post=item.get("post",{})
                rec=post.get("record",{})
                posts.append({"text":rec.get("text",""),"createdAt":rec.get("createdAt"),"links":links(post)})
        hay=(p.get("description") or "")+" "+json.dumps(posts)
        domain_hits=hay.lower().count(t["domain"].lower())
        arr.append({"handle":h,"exists":True,"displayName":p.get("displayName"),"description":p.get("description"),
                    "did":p.get("did"),"followersCount":p.get("followersCount"),"postsCount":p.get("postsCount"),
                    "domain_hits":domain_hits,"posts":posts[:8]})
        time.sleep(.08)
    out.append({**t,"results":arr})
Path("team_verify_results.json").write_text(json.dumps(out,indent=2,ensure_ascii=False))
for t in out:
    print("\nTEAM",t["code"],t["name"],t["domain"])
    for r in t["results"]:
        if not r.get("exists"): print(" MISS",r["handle"]);continue
        print(" CAND",r["handle"],"domain_hits=",r["domain_hits"],"posts=",r.get("postsCount"),"|",(r.get("description") or "")[:140].replace("\n"," "))
        for p in r["posts"][:3]:
            print("  POST",(p.get("text") or "")[:130].replace("\n"," ")," LINKS ",",".join(p.get("links") or [])[:180])
