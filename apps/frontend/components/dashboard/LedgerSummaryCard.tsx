"use client";

import { useEffect, useState } from "react";
import { getLedgerSummary } from "@/services/ledger";
import type { BalanceResponse } from "@/types/ledger";

export default function LedgerSummaryCard({
  merchantId,
}: {
  merchantId: string;
}) {
  const [balance, setBalance] = useState<BalanceResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const r = await getLedgerSummary(merchantId);
      if (cancelled) return;

      if (!r.ok) {
        setErr("Ledger summary unavailable");
        return;
      }

      setBalance(r.data);
    }

    if (merchantId) load();
    return () => {
      cancelled = true;
    };
  }, [merchantId]);

  if (err) {
    return (
      <div className="p-4 border rounded">
        <div className="text-sm text-red-600">{err}</div>
      </div>
    );
  }

  if (!balance) {
    return (
      <div className="p-4 border rounded text-sm text-muted-foreground">
        Loading ledger…
      </div>
    );
  }

  return (
    <div className="p-4 border rounded space-y-1">
      <div className="text-sm text-muted-foreground">Ledger Balance</div>
      <div className="text-2xl font-semibold">
        {balance.total.toLocaleString()}
      </div>
    </div>
  );
}
