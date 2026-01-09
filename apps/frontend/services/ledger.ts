import { apiGet } from "@/lib/api";
import type { BalanceResponse } from "@/types/ledger";
import type { ApiResult } from "@/types/api";

export async function getLedgerSummary(
  merchantId: string
): Promise<ApiResult<BalanceResponse>> {
  return apiGet<BalanceResponse>(
    `/ledger/summary?merchant_id=${encodeURIComponent(merchantId)}`
  );
}
