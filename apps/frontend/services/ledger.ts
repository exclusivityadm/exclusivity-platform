import { apiGet } from "@/lib/exclusivityApi";
import type { BalanceResponse } from "@/types/ledger";

export async function getLedgerSummary(
  merchantId: string
) {
  return apiGet<BalanceResponse>(
    `/ledger/summary?merchant_id=${encodeURIComponent(merchantId)}`
  );
}
