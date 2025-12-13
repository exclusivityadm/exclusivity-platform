"use client";

import { useEffect, useMemo, useState } from "react";

function pickBackendUrl() {
  const env = process.env.NEXT_PUBLIC_BACKEND_URL || "";
  return (env || "https://exclusivity-backend.onrender.com").replace(/\/+$/, "");
}

export default function OnboardingPage() {
  const BACKEND = useMemo(() => pickBackendUrl(), []);
  const [merchantId, setMerchantId] = useState<string>("");
  const [shop, setShop] = useState<string>("");
  const [status, setStatus] = useState<string>("loading");
  const [msg, setMsg] = useState<string>("");

  useEffect(() => {
    const url = new URL(window.location.href);
    const m = url.searchParams.get("merchant_id") || "";
    const s = url.searchParams.get("shop") || "";
    setMerchantId(m);
    setShop(s);

    const run = async () => {
      if (!m) {
        setStatus("missing_merchant_id");
        return;
      }
      try {
        const r = await fetch(`${BACKEND}/onboarding/status?merchant_id=${encodeURIComponent(m)}`);
        const j = await r.json();
        setStatus(j.status || "installed");
      } catch {
        setStatus("error");
      }
    };

    run();
  }, [BACKEND]);

  async function confirmProfile() {
    setMsg("Confirming profile…");
    const r = await fetch(`${BACKEND}/onboarding/confirm-profile?merchant_id=${encodeURIComponent(merchantId)}`, {
      method: "POST"
    });
    if (!r.ok) {
      setMsg("❌ Failed to confirm profile");
      return;
    }
    setMsg("✅ Profile confirmed");
    const j = await (await fetch(`${BACKEND}/onboarding/status?merchant_id=${encodeURIComponent(merchantId)}`)).json();
    setStatus(j.status || status);
  }

  async function bootstrapLoyalty() {
    setMsg("Bootstrapping loyalty baseline…");
    const r = await fetch(`${BACKEND}/loyalty/bootstrap?merchant_id=${encodeURIComponent(merchantId)}`, {
      method: "POST"
    });
    const t = await r.text();
    if (!r.ok) {
      setMsg(`❌ Loyalty bootstrap failed: ${t}`);
      return;
    }
    setMsg("✅ Loyalty baseline created");
    // We’ll mark ready and then send you to dashboard.
    await fetch(`${BACKEND}/onboarding/mark-ready?merchant_id=${encodeURIComponent(merchantId)}`, { method: "POST" });
    window.location.href = "/dashboard";
  }

  return (
    <main style={{ minHeight: "100vh", background: "#0d0f14", color: "#f3f4f6", padding: 40 }}>
      <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 10 }}>Exclusivity Onboarding</h1>
      <div style={{ opacity: 0.8, marginBottom: 18 }}>
        <div><b>Shop:</b> {shop || "—"}</div>
        <div><b>Merchant ID:</b> {merchantId || "—"}</div>
        <div><b>Status:</b> {status}</div>
      </div>

      {!merchantId && (
        <div style={{ padding: 14, borderRadius: 10, background: "#1a1f2a", border: "1px solid #2a2f3e" }}>
          Missing <code>merchant_id</code> in URL. Install via Shopify to enter onboarding.
        </div>
      )}

      {merchantId && (
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
          <button
            onClick={confirmProfile}
            style={{ padding: "12px 16px", borderRadius: 10, border: "1px solid #1f2430", background: "#111318", color: "#f3f4f6", fontWeight: 700 }}
          >
            Confirm Profile
          </button>

          <button
            onClick={bootstrapLoyalty}
            style={{ padding: "12px 16px", borderRadius: 10, border: "1px solid #059669", background: "#10b981", color: "#04120c", fontWeight: 800 }}
          >
            Create Loyalty Baseline
          </button>
        </div>
      )}

      {msg && (
        <div style={{ marginTop: 18, padding: 12, borderRadius: 10, background: "#1a1f2a", border: "1px solid #2a2f3e" }}>
          {msg}
        </div>
      )}

      <div style={{ marginTop: 30, fontSize: 12, opacity: 0.7 }}>
        Backend: <code>{BACKEND}</code>
      </div>
    </main>
  );
}
