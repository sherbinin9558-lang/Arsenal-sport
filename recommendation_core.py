import re

def recommend(products, query, limit=6):
    q=(query or "").lower()
    tokens=set(re.findall(r"[\wа-яё]+",q))
    scored=[]
    for p in products:
        text=" ".join(str(p.get(k,"")) for k in ["name","brand","sport","category","purpose","surface","color","material","season","level","description","specs","sizes"]).lower()
        score=sum(1 for t in tokens if len(t)>1 and t in text)
        if p.get("active",True) is False: continue
        if p.get("stock_by_size"):
            available=sum(int(v or 0) for v in p["stock_by_size"].values())
            if available<=0: continue
            score+=2
        elif p.get("stock",0):
            score+=1
        if any(w in q for w in ["футбол","бутс","football"]) and "фут" in text: score+=3
        if any(w in q for w in ["искусствен","ag","ис"] ) and "искус" in text: score+=3
        scored.append((score,p))
    scored.sort(key=lambda x:x[0],reverse=True)
    return [p for s,p in scored[:limit] if s>0] or [p for _,p in scored[:limit]]
