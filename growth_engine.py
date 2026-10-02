"""Local growth engine: content -> leads -> orders -> revenue -> next actions.
No paid API and no invented metrics. Attribution is product-match based and clearly labeled.
"""
from collections import Counter

def _amount(value):
    try:
        return float(str(value or "").replace(" ","").replace(",", ".").replace("₽",""))
    except Exception:
        return 0.0

def _title(p):
    return f"{p.get('brand','')} {p.get('name','')}".strip()

def _match(text, product):
    hay=str(text or "").lower()
    pid=str(product.get("id") or product.get("article") or "").strip().lower()
    title=_title(product).lower()
    name=str(product.get("name","")).lower().strip()
    article=str(product.get("article","")).lower().strip()
    return bool((pid and pid in hay) or (article and article in hay) or (name and name in hay) or (title and title in hay))

def funnel(leads, orders, plan, products):
    published=sum(1 for x in plan if x.get("status")=="Опубликовано")
    completed=sum(1 for x in orders if x.get("status")=="Завершён")
    revenue=sum(_amount(x.get("amount")) for x in orders if x.get("status")!="Отменён")
    return {
        "content":len(plan),"published":published,"leads":len(leads),
        "orders":len(orders),"completed_orders":completed,"revenue":revenue,
        "lead_to_order":(len(orders)/len(leads)*100) if leads else 0.0,
        "published_to_lead":(len(leads)/published*100) if published else 0.0,
    }

def product_performance(products, leads, orders, plan):
    rows=[]
    for p in products:
        title=_title(p) or "Товар"
        matched_leads=[x for x in leads if _match(x.get("product") or x.get("message"),p)]
        matched_orders=[x for x in orders if _match(x.get("product"),p)]
        content=sum(1 for x in plan if _match(x.get("product"),p))
        revenue=sum(_amount(x.get("amount")) for x in matched_orders if x.get("status")!="Отменён")
        stock=p.get("stock_by_size") or {}
        try: stock_qty=sum(max(0,int(v or 0)) for v in stock.values())
        except Exception: stock_qty=int(p.get("total_stock") or 0)
        rows.append({"product":title,"content":content,"leads":len(matched_leads),"orders":len(matched_orders),"revenue":revenue,"stock":stock_qty})
    return sorted(rows,key=lambda x:(-x["orders"],-x["revenue"],-x["leads"],-x["content"],x["product"]))

def content_performance(plan):
    platform=Counter(); types=Counter(); statuses=Counter()
    for x in plan:
        statuses[x.get("status","Идея")]+=1
        if x.get("status")=="Опубликовано":
            platform[x.get("platform","Другое")]+=1
            types[x.get("type","Пост")]+=1
    return {"platforms":platform,"types":types,"statuses":statuses}

def recommendations(products, leads, orders, plan):
    f=funnel(leads,orders,plan,products)
    pp=product_performance(products,leads,orders,plan)
    cp=content_performance(plan)
    out=[]
    if not products:
        return ["Добавьте товары: AI не будет придумывать ассортимент."]
    if f["published"]==0:
        out.append("Опубликуйте первые материалы: после этого система сможет сравнивать контент по результатам.")
    elif f["leads"]==0:
        out.append("Контент уже есть, но заявок нет: усилить CTA и сделать отдельные материалы с конкретным товаром.")
    if f["leads"] and not orders:
        out.append("Есть заявки, но нет заказов: проверить скорость ответа, наличие, размеры и следующий шаг в CRM.")
    if f["lead_to_order"] and f["lead_to_order"]<10:
        out.append("Конверсия заявка → заказ пока низкая: протестировать более точный подбор товара и короткий CTA.")
    if pp:
        sold=[x for x in pp if x["orders"]>0]
        if sold:
            out.append(f"Усилить контент вокруг товара «{sold[0]['product']}»: он уже связан с заказами.")
        lead_only=[x for x in pp if x["leads"]>0 and x["orders"]==0]
        if lead_only:
            out.append(f"Дожать лиды по «{lead_only[0]['product']}»: добавить FAQ, размеры и следующий шаг.")
        low=[x for x in pp if 0<x["stock"]<=2]
        if low:
            out.append(f"Проверить остаток перед продвижением: «{low[0]['product']}» — {low[0]['stock']} шт.")
    if cp["platforms"]:
        best=cp["platforms"].most_common(1)[0]
        out.append(f"По опубликованным материалам чаще использовать {best[0]} и сравнить его с другими каналами.")
    if len(out)<4:
        out.append("Следующий цикл: товар → короткий Reels → пост с выгодой → CTA → фиксация лида → заказ.")
    return out[:6]

def next_content(products, leads, orders, plan, limit=7):
    pp=product_performance(products,leads,orders,plan)
    ranked=[x["product"] for x in pp if x["orders"] or x["leads"]]
    names=ranked+[x["product"] for x in pp if x["product"] not in ranked]
    used=Counter((x.get("product"),x.get("type")) for x in plan)
    result=[]
    types=["Reels","Пост","Stories","Карусель"]
    for name in names:
        if len(result)>=limit: break
        p=next((x for x in products if _title(x)==name),None)
        if not p: continue
        for t in types:
            if used[(name,t)]<2:
                result.append({"product":name,"type":t,"idea":f"{t}: показать {name} через пользу, детали и понятный CTA.","priority":"Высокий" if name in ranked else "Обычный"})
                break
    return result

def ai_summary(products, leads, orders, plan):
    return {"headline":"Контент → продажи","funnel":funnel(leads,orders,plan,products),"recommendations":recommendations(products,leads,orders,plan),"next_content":next_content(products,leads,orders,plan),"products":product_performance(products,leads,orders,plan),"content":content_performance(plan)}
