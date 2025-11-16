"use client";
import React, { useState } from "react";
const API = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");

export default function ShopifyInstallPage() {
  const [shop, setShop] = useState("");
  const [merchantId, setMerchantId] = useState("");

  function install() {
    if (!shop) return alert("Enter your shop domain (e.g., mybrand)");
    const shopParam = shop.endsWith(".myshopify.com") ? shop : `${shop}.myshopify.com`;
    const url = `${API}/shopify/install?shop=${encodeURIComponent(shopParam)}${
      merchantId ? `&merchant_id=${encodeURIComponent(merchantId)}` : ""
    }`;
    window.location.href = url;
  }

  return (
    <main className="min-h-dvh bg-white text-black">
      <div className="max-w-xl mx-auto p-6 space-y-6">
        <h1 className="text-2xl font-semibold">Shopify Install</h1>
        <div className="space-y-2">
          <input className="border p-2 w-full" placeholder="shop domain (e.g., mybrand or mybrand.myshopify.com)"
                 value={shop} onChange={e=>setShop(e.target.value)} />
          <input className="border p-2 w-full" placeholder="(optional) merchant_id to link"
                 value={merchantId} onChange={e=>setMerchantId(e.target.value)} />
        </div>
        <button className="px-3 py-2 rounded bg-black text-white" onClick={install}>Install App</button>
        <p className="text-sm text-gray-600">
          This launches the Shopify OAuth flow and returns to the backend callback, storing the shop access token in Supabase.
        </p>
      </div>
    </main>
  );
}
