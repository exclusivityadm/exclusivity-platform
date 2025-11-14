# FULL FILE — new
def add_points(supa, merchant_id, customer_id, delta, reason, ref=None):
    supa.table("points_ledger").insert({
        "merchant_id": merchant_id,
        "customer_id": customer_id,
        "delta": int(delta),
        "reason": reason,
        "ref": ref or {}
    }).execute()

def total_points(supa, merchant_id, customer_id):
    try:
        res = supa.rpc("sum_points", {"m": merchant_id, "c": customer_id}).execute()
        if res and res.data:
            return int(res.data[0].get("sum") or 0)
    except Exception:
        pass
    rows = supa.table("points_ledger").select("delta").eq("merchant_id", merchant_id).eq("customer_id", customer_id).execute().data
    return sum(int(r["delta"]) for r in rows)
