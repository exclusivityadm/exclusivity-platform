// FULL FILE — new
"use client";
import { useState } from "react";

export default function ShopifySettings(){
  const [shop,setShop]=useState("");
  const [busy,setBusy]=useState(false);

  return (
    <main className="p-6 space-y-3">
      <h1 className="text-xl font-semibold">Shopify</h1>
      <div className="flex gap-2 max-w-xl">
        <input className="border p-2 flex-1" placeholder="myshop.myshopify.com" value={shop} onChange={e=>setShop(e.target.value)} />
        <button disabled={busy || !shop} className="bg-black text-white px-3 py-2 rounded"
          onClick={async()=>{
            setBusy(true);
            try{
              const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/shopify/oauth/start?shop=${encodeURIComponent(shop)}`, { cache:"no-store" });
              const j = await r.json();
              window.location.href = j.auth_url;
            } finally { setBusy(false); }
          }}>
          {busy ? "Connecting..." : "Connect"}
        </button>
      </div>
    </main>
  );
}
