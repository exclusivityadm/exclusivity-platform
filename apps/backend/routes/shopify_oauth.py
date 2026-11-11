"""Shopify connector admission gate.

Shopify's former OAuth callback accepted merchant_id as a caller-supplied
state with no nonce, merchant-owner binding, expiration or one-time use.
That legacy onboarding also auto-started the unsafe history backfill.

Preserve the earlier implementation in Git history and fail closed until the
replacement signed/stateful OAuth flow, encrypted token storage, webhook
checks, and merchant authorization have been reviewed and tested.
"""

from fastapi import APIRouter, HTTPException


router = APIRouter(prefix="/shopify", tags=["shopify"])


@router.get("/oauth/callback")
async def oauth_callback():
    raise HTTPException(
        status_code=503,
        detail=(
            "Shopify installation is paused pending a security-verified "
            "OAuth state, merchant authorization, and safe loyalty import."
        ),
    )
