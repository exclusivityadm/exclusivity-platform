// apps/backend/routes/onboarding.ts
import { Router } from "express";
import { ApiResult, err, ok, fromException } from "../shared/apiResult";
import { ensureMerchantByShop } from "../services/merchantService";

const router = Router();

type ResolveOnboardingResult = {
  merchant_id: string;
  created: boolean;
  shop_domain: string;
};

router.post("/resolve", async (req, res) => {
  try {
    const shop = (req.body?.shop || req.query?.shop || "").toString();

    const r = await ensureMerchantByShop(shop);
    if (!r.ok) return res.status(400).json(r);

    const payload: ResolveOnboardingResult = {
      merchant_id: r.data.merchant_id,
      created: r.data.created,
      shop_domain: r.data.shop_domain,
    };

    return res.json(ok(payload));
  } catch (e) {
    return res.status(500).json(fromException("Resolve failed", e));
  }
});

export default router;
