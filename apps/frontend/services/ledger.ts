import { apiGet } from '@/services/http'
import type { BalanceResponse } from '@/types/ledger'
import type { ApiResult } from '@/types/api'

export async function getLedgerSummary(): Promise<ApiResult<BalanceResponse>> {
  return apiGet<BalanceResponse>('/ledger/summary')
}
