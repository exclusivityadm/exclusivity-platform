"use client";

import React, { useState } from "react";

const API = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");

export default function MerchantAdmin() {
  const [merchantId, setMerchantId] = useState("");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");

  const [tokenName, setTokenName] = useState("LUX");
  const [tierUnit, setTierUnit] = useState("points");
  const [domains, setDomains] = useState("exclusivity.vip");

  const [tiers, setTiers] = useState([
    { code: "SILVER", name: "Silver", min_points: 0, sort_order: 1 },
    { code: "GOLD", name: "Gold", min_points: 1000, sort_order: 2 },
    { code: "PLATINUM", name: "Platinum", min_points: 5000, sort_order: 3 },
  ]);

  async function saveProfile() {
    const res = await fetch(`${API}/merchant/profile`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ merchant_id: merchantId || undefined, email: email || undefined, name: name || undefined }),
    });
    const json = await res.json();
    if (!res.ok) return alert(JSON.stringify(json));
    setMerchantId(json.merchant.merchant_id);
    alert("Profile saved");
  }

  async function saveSettings() {
    if (!merchantId) return alert("Save profile first (merchant_id).");
    const res = await fetch(`${API}/merchant/settings`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({
        merchant_id: merchantId,
        token_name: tokenName,
        tier_unit: tierUnit,
        domain_allowlist: domains.split(",").map(s=>s.trim()).filter(Boolean),
        settings: {},
      }),
    });
    const json = await res.json();
    if (!res.ok) return alert(JSON.stringify(json));
    alert("Settings saved");
  }

  async function saveTiers() {
    if (!merchantId) return alert("Save profile first (merchant_id).");
    const res = await fetch(`${API}/merchant/tiers`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ merchant_id: merchantId, tiers }),
    });
    const json = await res.json();
    if (!res.ok) return alert(JSON.stringify(json));
    alert("Tiers saved");
  }

  return (
    <main className="min-h-dvh bg-white text-black">
      <div className="max-w-3xl mx-auto p-6 space-y-8">
        <h1 className="text-2xl font-semibold">Merchant Profile & Settings</h1>

        <section className="rounded border p-4 space-y-2">
          <p className="font-medium">Profile</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input className="border p-2" placeholder="merchant_id (auto)" value={merchantId} onChange={e=>setMerchantId(e.target.value)} />
            <input className="border p-2" placeholder="email" value={email} onChange={e=>setEmail(e.target.value)} />
            <input className="border p-2" placeholder="name" value={name} onChange={e=>setName(e.target.value)} />
          </div>
          <button className="px-3 py-2 rounded bg-black text-white" onClick={saveProfile}>Save Profile</button>
        </section>

        <section className="rounded border p-4 space-y-2">
          <p className="font-medium">Brand Settings</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input className="border p-2" placeholder="token name" value={tokenName} onChange={e=>setTokenName(e.target.value)} />
            <input className="border p-2" placeholder="tier unit" value={tierUnit} onChange={e=>setTierUnit(e.target.value)} />
            <input className="border p-2" placeholder="domain allowlist (comma separated)" value={domains} onChange={e=>setDomains(e.target.value)} />
          </div>
          <button className="px-3 py-2 rounded bg-black text-white" onClick={saveSettings}>Save Settings</button>
        </section>

        <section className="rounded border p-4 space-y-3">
          <p className="font-medium">Tiers</p>
          {tiers.map((t, i)=>(
            <div key={i} className="grid grid-cols-4 gap-2">
              <input className="border p-2" placeholder="code" value={t.code} onChange={e=>{
                const v=[...tiers]; v[i]={...v[i], code:e.target.value}; setTiers(v);
              }}/>
              <input className="border p-2" placeholder="name" value={t.name} onChange={e=>{
                const v=[...tiers]; v[i]={...v[i], name:e.target.value}; setTiers(v);
              }}/>
              <input className="border p-2" placeholder="min_points" type="number" value={t.min_points} onChange={e=>{
                const v=[...tiers]; v[i]={...v[i], min_points: Number(e.target.value)}; setTiers(v);
              }}/>
              <input className="border p-2" placeholder="sort_order" type="number" value={t.sort_order} onChange={e=>{
                const v=[...tiers]; v[i]={...v[i], sort_order: Number(e.target.value)}; setTiers(v);
              }}/>
            </div>
          ))}
          <button className="px-3 py-2 rounded bg-black text-white" onClick={saveTiers}>Save Tiers</button>
        </section>
      </div>
    </main>
  );
}
