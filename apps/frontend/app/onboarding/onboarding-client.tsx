// apps/frontend/app/onboarding/onboarding-client.tsx
// =====================================================
// Exclusivity — Onboarding Client Logic
// Client-only, dynamic-safe
// =====================================================

"use client";

import { useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  getBrandStatusByShop,
  getMerchantProfileByShop,
  apiPost,
} from "@/lib/exclusivityApi";

type ResolveSuccess = {
  ok: true;
  merchant_id: string;
  created?: boolean;
};

type ResolveFailure = {
  ok: false;
  error: string;
};

type ResolveResult = ResolveSuccess | ResolveFailure;

export default function OnboardingClient() {
  const params = useSearchParams();
  const router = useRouter();
  const shop = params.get("shop");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!shop) {
    return (
      <div style={{ padding: 32 }}>
        <h1>Exclusivity — Onboarding</h1>
        <p style={{ color: "crimson" }}>Missing shop parameter</p>
      </div>
    );
  }

  async function resolveMerchant(): Promise<ResolveResult> {
    const status = await getBrandStatusByShop(shop);
    if (!status.ok) return { ok: false, error: "Brand status check failed" };

    const profile = await getMerchantProfileByShop(shop);
    if (profile.ok && profile.data?.merchant_id) {
      return { ok: true, merchant_id: profile.data.merchant_id };
    }

    const ingest = await apiPost<{ merchant_id: string }>(
      "/brand/ingest",
      { shop_domain: shop }
    );

    if (!ingest.ok || !ingest.data?.merchant_id) {
      return { ok: false, error: "Merchant bootstrap failed" };
    }

    return { ok: true, merchant_id: ingest.data.merchant_id };
  }

  async function handleContinue() {
    setBusy(true);
    setError(null);

    const result = await resolveMerchant();

    if (!result.ok) {
      setBusy(false);
      setError(result.error);
      return;
    }

    router.replace(`/dashboard?merchant_id=${result.merchant_id}`);
  }

  return (
    <div style={{ padding: 32 }}>
      <h1>Exclusivity — Onboarding</h1>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <button onClick={handleContinue} disabled={busy}>
        {busy ? "Initializing…" : "Continue"}
      </button>
    </div>
  );
}
