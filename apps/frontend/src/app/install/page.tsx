"use client";

import { useMemo, useState } from "react";

function pickBackendUrl() {
  const env = process.env.NEXT_PUBLIC_BACKEND_URL || "";
  return (env || "https://exclusivity-backend.onrender.com").replace(/\/+$/, "");
}

export default function InstallPage() {
  const BACKEND = useMemo(() => pickBackendUrl(), []);
  const [shop, setShop] = useState("");

  function go() {
    if (!shop || !shop.includes(".myshopify.com")) {
      alert("Enter your shop domain like: your-store.myshopify.com");
      return;
    }
    window.location.href = `${BACKEND}/shopify/install?shop=${encodeURIComponent(shop)}`;
  }

  return (
    <main style={{ minHeight: "100vh", background: "#0d0f14", color: "#f3f4f6", padding: 40 }}>
      <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 10 }}>Install Exclusivity</h1>
      <p style={{ opacity: 0.8, marginBottom: 18 }}>
        Enter your Shopify store domain to begin OAuth install.
      </p>

      <input
        value={shop}
        onChange={(e) => setShop(e.target.value.trim())}
        placeholder="exclusivity-dev.myshopify.com"
        style={{
          width: "min(520px, 100%)",
          padding: "12px 14px",
          borderRadius: 10,
          border: "1px solid #2a2f3e",
          background: "#111318",
          color: "#f3f4f6"
        }}
      />

      <div style={{ marginTop: 14 }}>
        <button
          onClick={go}
          style={{
            padding: "12px 16px",
            borderRadius: 10,
            border: "1px solid #1d4ed8",
            background: "#2563eb",
            color: "white",
            fontWeight: 800
          }}
        >
          Start Install
        </button>
      </div>

      <div style={{ marginTop: 30, fontSize: 12, opacity: 0.7 }}>
        Backend: <code>{BACKEND}</code>
      </div>
    </main>
  );
}
