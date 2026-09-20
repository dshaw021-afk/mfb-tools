#!/usr/bin/env python3
import json, urllib.parse, urllib.request, time, math, re, sys
from pathlib import Path

API="https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors"
BAD_OFFICIAL=("unofficial","fan account","fan page","parody","not official","not the official","unaffiliated","not affiliated")

def norm(s):
    return re.sub(r"[^a-z0-9]+"," ",(s or "").lower()).strip()

def compact(s):
    return re.sub(r"[^a-z0-9]","",(s or "").lower())

def tokens(s):
    stop={"the","and","of","sports","nfl","football","official","news"}
    return {x for x in norm(s).split() if len(x)>2 and x not in stop}

def fetch(q,tries=4):
    url=API+"?"+urllib.parse.urlencode({"q":q,"limit":10})
    last=None
    for i in range(tries):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"MFB-Bluesky-Audit/1.0"})
            with urllib.request.urlopen(req,timeout=20) as r:
                return json.load(r).get("actors",[])
        except Exception as e:
            last=e; time.sleep(1.5*(i+1))
    raise last

def candidate_score(src,a):
    name=src["name"]; typ=src["source_type"]
    disp=a.get("displayName") or ""
    handle=a.get("handle") or ""
    desc=a.get("description") or ""
    nd, nn = norm(disp), norm(name)
    score=0
    reasons=[]
    if nd==nn:
        score+=55; reasons.append("exact display name")
    st, dt=tokens(name),tokens(disp)
    if st:
        overlap=len(st & dt)/max(1,len(st))
        score+=round(30*overlap,1)
        if overlap>=0.7: reasons.append("strong name-token match")
    xstem=compact(src["x_handle"].lstrip("@"))
    hc=compact(handle)
    if xstem and (xstem in hc or hc.startswith(xstem)):
        score+=22; reasons.append("X-handle match")
    nslug=compact(name)
    if nslug and (nslug in hc or hc in nslug) and len(hc)>=5:
        score+=15; reasons.append("handle/name match")
    dlow=(desc+" "+disp).lower()
    if typ=="Official" and any(b in dlow for b in BAD_OFFICIAL):
        score-=120; reasons.append("reject: unofficial/fan/parody")
    if typ=="Reporter":
        if any(k in dlow for k in ("reporter","writer","journalist","covers","covering","insider","editor","columnist")):
            score+=8; reasons.append("journalist bio")
        if "nfl" in dlow or src["coverage"].lower() in dlow:
            score+=5
    if typ=="Outlet":
        if any(k in dlow for k in ("news","sports","newspaper","media","coverage")):
            score+=5
    fc=a.get("followersCount") or 0
    if fc:
        score+=min(8, max(0, math.log10(max(fc,1))*1.5))
    return round(score,1), reasons

sources=json.loads(Path("audit_sources.json").read_text())
results=[]
for n,src in enumerate(sources,1):
    qs=[src["name"]]
    xq=src["x_handle"].lstrip("@")
    if xq and compact(xq)!=compact(src["name"]): qs.append(xq)
    found={}
    errs=[]
    for q in qs:
        try:
            for a in fetch(q):
                h=a.get("handle")
                if h: found[h]=a
        except Exception as e:
            errs.append(str(e))
        time.sleep(.12)
    ranked=[]
    for a in found.values():
        sc,why=candidate_score(src,a)
        ranked.append({
            "handle":a.get("handle"),"displayName":a.get("displayName"),"description":a.get("description"),
            "did":a.get("did"),"followersCount":a.get("followersCount"),"score":sc,"reasons":why
        })
    ranked.sort(key=lambda x:x["score"],reverse=True)
    top=ranked[:5]
    decision="none"
    if top:
        if top[0]["score"]>=75 and (len(top)==1 or top[0]["score"]-top[1]["score"]>=8):
            decision="high"
        elif top[0]["score"]>=55:
            decision="review"
    results.append({"source":src,"decision":decision,"candidates":top,"errors":errs})
    if n%20==0: print(f"audited {n}/{len(sources)}",flush=True)

Path("audit_results.json").write_text(json.dumps(results,indent=2,ensure_ascii=False))
high=[r for r in results if r["decision"]=="high"]
review=[r for r in results if r["decision"]=="review"]
none=[r for r in results if r["decision"]=="none"]
print("MFB_AUDIT_SUMMARY",json.dumps({"sources":len(results),"high":len(high),"review":len(review),"none":len(none)}))
for r in high:
    c=r["candidates"][0]
    print("HIGH",r["source"]["destination"],r["source"]["name"],"=>",c["handle"],c["score"],"|",c.get("description","")[:160].replace("\n"," "))
print("REVIEW_COUNT",len(review))
for r in review[:80]:
    c=r["candidates"][0]
    print("REVIEW",r["source"]["name"],"=>",c["handle"],c["score"],"|",c.get("description","")[:120].replace("\n"," "))
