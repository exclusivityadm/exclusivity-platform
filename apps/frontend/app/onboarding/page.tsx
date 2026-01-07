// apps/frontend/app/onboarding/page.tsx
// =====================================================
// Exclusivity — Onboarding (FINAL, TYPE-SAFE)
// Phase: UI-05 / UI-06
//
// Guarantees:
// - No unsafe union access
// - No TS narrowing failures
// - Deterministic merchant bootstrap
// - One-way flow into dashboard
// =====================================================

"use client";

import { useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  getBrandStatusByShop,
  getMerchantProfileByShop,
  apiPost,
} from "@/lib/exclusivityApi";

/* ---------- Types ---------- */

type ResolveSuccess = {
  ok: true;
  merchant_id: string;
  created?: boolean;
};

type ResolveFailure = {
  ok: false;
  error: string;
  details?: any;
};

type ResolveResult = ResolveSuccess | ResolveFailure;

/* ---------- Page ---------- */

export default function OnboardingPage() {
  const params = useSearchParams();
  const router = useRouter();
  const shop = params.get("shop");

  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /* ---------- Guard ---------- */

  if (!shop) {
    return (
      <div style={{ padding: 32 }}>
        <h1>Exclusivity — Onboarding</h1>
        <p>Step 1 of 5: Welcome</p>
        <p style={{ color: "crimson" }}>Missing shop parameter</p>
      </div>
    );
  }

  /* ---------- Resolver ---------- */

  async function resolveMerchant(): Promise<ResolveResult> {
    try {
      const status = await getBrandStatusByShop(shop);
      if (!status.ok) {
        return { ok: false, error: "Unable to check brand status", details: status };
      }

      const profile = await getMerchantProfileByShop(shop);
      if (profile.ok && profile.data?.merchant_id) {
        return { ok: true, merchant_id: profile.data.merchant_id };
      }

      const ingest = await apiPost<{ merchant_id: string; created?: boolean }>(
        "/brand/ingest",
        { shop_domain: shop }
      );

      if (!ingest.ok || !ingest.data?.merchant_id) {
        return { ok: false, error: "Merchant bootstrap failed", details: ingest };
      }

      return {
        ok: true,
        merchant_id: ingest.data.merchant_id,
        created: ingest.data.created,
      };
    } catch (e: any) {
      return { ok: false, error: e?.message || "Unexpected error" };
    }
  }

  /* ---------- Action ---------- */

  async function handleContinue() {
    setBusy(true);
    setError(null);

    const result = await resolveMerchant();

    if (result.ok === false) {
      // 🔒 Fully safe: error only read in failure branch
      setBusy(false);
      setError(result.error);
      return;
    }

    // ✅ Success path
    setBusy(false);
    setStep(2);

    router.replace(`/dashboard?merchant_id=${result.merchant_id}`);
  }

  /* ---------- Render ---------- */

  return (
    <div style={{ padding: 32, maxWidth: 640 }}>
      <h1>Exclusivity — Onboarding</h1>
      <p>Step {step} of 5: Welcome</p>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <button
        onClick={handleContinue}
        disabled={busy}
        style={{ padding: "10px 16px", marginTop: 16 }}
      >
        {busy ? "Initializing…" : "Continue"}
      </button>
    </div>
  );
}
