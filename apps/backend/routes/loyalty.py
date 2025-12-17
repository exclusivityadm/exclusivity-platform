from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from apps.backend.services.core_service import CoreError
from apps.backend.services.loyalty_service import (
    upsert_customer,
    append_ledger,
    get_balance_and_tier,
    set_tiers,
    list_tiers,
    health_loyalty,
)

router = APIRouter(tags=["Loyalty"])


@router.get("/health")
async def loyalty_health():
    res = health_loyalty()
    return JSONResponse(content=res, status_code=200 if res.get("ok") else 503)


@router.post("/customer/upsert")
async def loyalty_customer_upsert(request: Request):
    try:
        body = await request.json()
        email = body.get("email")
        name = body.get("name")
        if not email:
            return JSONResponse(status_code=400, content={"error": "email is required"})
        return upsert_customer(request, email=email, name=name)
    except CoreError as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.message})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/ledger/earn")
async def loyalty_earn(request: Request):
    try:
        body = await request.json()
        email = body.get("customer_email")
        points = body.get("points")
        reason = body.get("reason")
        ref = body.get("ref")
        if not email or not points:
            return JSONResponse(status_code=400, content={"error": "customer_email and points are required"})
        return append_ledger(request, customer_email=email, event_type="earn", points=int(points), reason=reason, ref=ref)
    except CoreError as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.message})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/ledger/redeem")
async def loyalty_redeem(request: Request):
    try:
        body = await request.json()
        email = body.get("customer_email")
        points = body.get("points")
        reason = body.get("reason")
        ref = body.get("ref")
        if not email or not points:
            return JSONResponse(status_code=400, content={"error": "customer_email and points are required"})
        return append_ledger(request, customer_email=email, event_type="redeem", points=int(points), reason=reason, ref=ref)
    except CoreError as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.message})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/balance")
async def loyalty_balance(request: Request, customer_email: str):
    try:
        return get_balance_and_tier(request, customer_email=customer_email)
    except CoreError as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.message})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/tiers/set")
async def loyalty_tiers_set(request: Request):
    try:
        body = await request.json()
        tiers = body.get("tiers")
        if not isinstance(tiers, list):
            return JSONResponse(status_code=400, content={"error": "tiers must be a list"})
        return set_tiers(request, tiers=tiers)
    except CoreError as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.message})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/tiers")
async def loyalty_tiers_list(request: Request):
    try:
        return list_tiers(request)
    except CoreError as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.message})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
