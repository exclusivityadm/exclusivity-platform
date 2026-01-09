'use client'

import { useEffect, useState } from 'react'
import { getLedgerSummary } from '@/services/ledger'
import type { BalanceResponse } from '@/types/ledger'

export default function LedgerSummaryCard() {
  const [balance, setBalance] = useState<BalanceResponse | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      const r = await getLedgerSummary()
      if (cancelled) return

      if (r.ok) {
        setBalance(r.data)
        setErr(null)
      } else {
        setErr(r.message || 'Ledger summary unavailable')
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  if (err) {
    return <div className="text-red-500 text-sm">{err}</div>
  }

  if (!balance) {
    return <div className="text-sm text-muted-foreground">Loading…</div>
  }

  return (
    <div className="rounded-lg border p-4">
      <div className="text-sm text-muted-foreground">Ledger Balance</div>
      <div className="text-2xl font-semibold">
        {balance.total.toLocaleString()}
      </div>
    </div>
  )
}
