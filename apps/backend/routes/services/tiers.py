# FULL FILE — new
def resolve_tier(supa, merchant_id, points: int):
    rows = supa.table("loyalty_tier").select("*").eq("merchant_id", merchant_id).order("threshold_points").execute().data
    current = None
    for t in rows:
        if points >= int(t["threshold_points"]):
            current = t
        else:
            break
    return current
