"use client";
import React, { useState } from "react";
const API = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");

export default function LoyaltyTester() {
  const [merchantId, setMerchantId] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [delta, setDelta] = useState(100);
  const [balance, setBalance] = useState<number | null>(null);
  const [tier, setTier] = useState<any>(null);

  async function doAccrue() {
    const res = await fetch(`${API}/loyalty/accrue`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ merchant_id: merchantId, customer_id: customerId, delta, reason: "manual-test" }),
    });
    const json = await res.json();
    if (!res.ok) return alert(JSON.stringify(json));
    setBalance(json.balance.points);
  }

  async function getBalance() {
    const res = await fetch(`${API}/loyalty/balance?merchant_id=${merchantId}&customer_id=${customerId}`);
    const json = await res.json();
    if (!res.ok) return alert(JSON.stringify(json));
    setBalance(json.balance.points);
  }

  async function recalcTier() {
    const res = await fetch(`${API}/loyalty/tier-recalc?merchant_id=${merchantId}&customer_id=${customerId}`, { method: "POST" });
    const json = await res.json();
    if (!res.ok) return alert(JSON.stringify(json));
    setTier(json.tier);
  }

  return (
    <main className="min-h-dvh bg-white text-black">
      <div className="max-w-xl mx-auto p-6 space-y-6">
        <h1 className="text-2xl font-semibold">Loyalty Tester</h1>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input className="border p-2" placeholder="merchant_id" value={merchantId} onChange={e=>setMerchantId(e.target.value)} />
          <input className="border p-2" placeholder="customer_id" value={customerId} onChange={e=>setCustomerId(e.target.value)} />
        </div>

        <div className="flex gap-2 items-center">
          <input className="border p-2 w-32" type="number" value={delta} onChange={e=>setDelta(Number(e.target.value))} />
          <button className="px-3 py-2 rounded bg-black text-white" onClick={doAccrue}>Accrue</button>
          <button className="px-3 py-2 rounded bg-black text-white" onClick={getBalance}>Get Balance</button>
          <button className="px-3 py-2 rounded bg-black text-white" onClick={recalcTier}>Recalc Tier</button>
        </div>

        <div className="text-sm space-y-1">
          <div>Balance: <b>{balance ?? "-"}</b></div>
          <div>Tier: <code>{tier ? `${tier.code} (${tier.name}) @ ${tier.min_points}+` : "-"}</code></div>
        </div>
      </div>
    </main>
  );
}
