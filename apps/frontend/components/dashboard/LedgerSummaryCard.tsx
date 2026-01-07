"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/exclusivityApi";

type BalanceResponse = {
  ok?: boolean;
  merchant_id?: string;
  email?: string;
  balance?: number;
  points?: number;
  [k: string]: any;
};

export default function LedgerSummaryCard({ merchantId }: { merchantId: string }) {
  const [balance, setBalance] = useState<BalanceResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setErr(null);

      // Backend shape may vary; this is a safe call that won't crash if 4xx/5xx.
      // If your backend expects different query params, we’ll align it in backend phase.
      const r = await apiGet<BalanceResponse>(`/loyalty/balance?merchant_id=${encodeURIComponent(merchantId)}`);
      if (!cancelled) {
        if (r.ok) setBalance(r.data);
        else setErr(r.error || "Ledger summary unavailable");
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, [merchantId]);

  return (
    <section className="border rounded p-4 space-y-2">
      <div className="font-medium">Ledger Snapshot</div>
      {err && <div className="text-sm text-red-600">{err}</div>}

      {!err && !balance && (
        <div className="text-sm text-gray-500">No data yet.</div>
      )}

      {balance && (
        <div className="text-sm space-y-1">
          <div className="text-gray-500 text-xs">Raw response (stable)</div>
          <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">
{JSON.stringify(balance, null, 2)}
          </pre>
        </div>
      )}
    </section>
  );
}
