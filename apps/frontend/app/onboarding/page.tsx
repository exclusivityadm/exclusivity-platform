// apps/frontend/app/onboarding/page.tsx
// =====================================================
// Exclusivity — Onboarding (Canonical, Type-Safe)
// Phase: UI-05 / UI-06 Bridge
//
// Guarantees:
// - shop param required
// - merchant identity bootstrapped deterministically
// - no unsafe property access
// - no TypeScript narrowing failures
// =====================================================

"use client";

import { useEffect, useState } from "react";
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
  details?: any;
};

type ResolveResult = ResolveSuccess | ResolveFailure;

export default function OnboardingPage() {
  const params = useSearchParams();
  const router = useRouter();

  const shop = params.get("shop");

  const [step, setStep] = useState<number>(1);
  const [busy, setBusy] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [merchantId, setMerchantId] = useState<string | null>(null);

  // --------------------------------------------------
  // Guard: shop param
  // --------------------------------------------------
  if (!shop) {
    return (
      <div style={{ padding: 32 }}>
        <h1>Exclusivity — Onboarding</h1>
        <p>Step 1 of 5: Welcome</p>
        <p style={{ color: "crimson" }}>Missing shop parameter</p>
      </div>
    );
  }

  // --------------------------------------------------
  // Resolve / Bootstrap merchant
  // --------------------------------------------------
  async function resolveMerchant(): Promise<ResolveResult> {
    try {
      // 1) Check status
      const status = await getBrandStatusByShop(shop);
      if (!status.ok) {
        return { ok: false, error: "Unable to check brand status", details: status };
      }

      // 2) Attempt profile resolution
      const profile = await getMerchantProfileByShop(shop);
      if (profile.ok && profile.data?.merchant_id) {
        return { ok: true, merchant_id: profile.data.merchant_id };
      }

      // 3) Bootstrap merchant
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
        created: Boolean(ingest.data.created),
      };
    } catch (e: any) {
      return { ok: false, error: e?.message || "Unexpected error" };
    }
  }

  // --------------------------------------------------
  // Continue handler
  // --------------------------------------------------
  async function handleContinue() {
    setBusy(true);
    setError(null);

    const result = await resolveMerchant();

    if (!result.ok) {
      setBusy(false);
      setError(result.error);
      return;
    }

    // ✅ Fully type-safe here
    setMerchantId(result.merchant_id);
    setBusy(false);
    setStep(2);

    // Temporary redirect straight to dashboard
    router.replace(`/dashboard?merchant_id=${result.merchant_id}`);
  }

  // --------------------------------------------------
  // Render
  // --------------------------------------------------
  return (
    <div style={{ padding: 32, maxWidth: 640 }}>
      <h1>Exclusivity — Onboarding</h1>
      <p>Step {step} of 5: Welcome</p>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      {!merchantId && (
        <button
          onClick={handleContinue}
          disabled={busy}
          style={{ padding: "10px 16px", marginTop: 16 }}
        >
          {busy ? "Initializing…" : "Continue"}
        </button>
      )}

      {merchantId && (
        <p style={{ color: "green" }}>
          Merchant resolved: {merchantId}
        </p>
      )}
    </div>
  );
}
