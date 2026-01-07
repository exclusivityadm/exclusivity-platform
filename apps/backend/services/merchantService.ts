// apps/backend/services/merchantService.ts
import { ApiResult, err, ok, fromException } from "../shared/apiResult";

// NOTE: Replace these imports with your actual DB layer.
// The only requirement: you can look up a merchant by shop_domain and create one.
import { db } from "../db"; // <-- adjust to your project

export type MerchantRecord = {
  id: string;
  shop_domain: string;
  created_at?: string;
};

function normalizeShop(shop: string): string {
  const s = (shop || "").trim().toLowerCase();
  // Basic safety: remove protocol and trailing slash if user pastes full URL.
  return s.replace(/^https?:\/\//, "").replace(/\/+$/, "");
}

export async function getMerchantByShop(
  shop_domain: string
): Promise<ApiResult<{ merchant_id: string; shop_domain: string }>> {
  try {
    const shop = normalizeShop(shop_domain);
    if (!shop) return err("Missing shop parameter");

    const row: MerchantRecord | null = await db.merchants.findByShopDomain(shop);
    if (!row) return err("Merchant not found");

    return ok({ merchant_id: row.id, shop_domain: row.shop_domain });
  } catch (e) {
    return fromException("Merchant lookup failed", e);
  }
}

export async function ensureMerchantByShop(
  shop_domain: string
): Promise<ApiResult<{ merchant_id: string; shop_domain: string; created: boolean }>> {
  try {
    const shop = normalizeShop(shop_domain);
    if (!shop) return err("Missing shop parameter");

    const existing: MerchantRecord | null = await db.merchants.findByShopDomain(shop);
    if (existing) {
      return ok({ merchant_id: existing.id, shop_domain: existing.shop_domain, created: false });
    }

    const created: MerchantRecord = await db.merchants.createForShopDomain(shop);
    return ok({ merchant_id: created.id, shop_domain: created.shop_domain, created: true });
  } catch (e) {
    return fromException("Merchant resolve failed", e);
  }
}
