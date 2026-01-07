"use client";

import { useEffect, useState } from "react";
import {
  getMerchantProfileByShop,
  getInitQuestions,
  saveInitAnswers,
} from "@/lib/exclusivityApi";
import { useSearchParams } from "next/navigation";

/* -----------------------------
   Canonical types
------------------------------ */

type MerchantProfile = {
  merchant_id: string;
  shop_domain?: string | null;
  created_at?: string | null;
};

type ResolveSuccess = {
  ok: true;
  merchant_id: string;
  created: boolean;
};

type ResolveFail = {
  ok: false;
  error: string;
};

type ResolveResult = ResolveSuccess | ResolveFail;

/* -----------------------------
   Component
------------------------------ */

export default function OnboardingClient() {
  const searchParams = useSearchParams();
  const shop = searchParams.get("shop");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [merchantId, setMerchantId] = useState<string | null>(null);
  const [step, setStep] = useState(1);

  /* -----------------------------
     Resolve merchant identity
  ------------------------------ */
  useEffect(() => {
    if (!shop) {
      setError("Missing shop parameter");
      return;
    }

    let cancelled = false;

    async function resolve(): Promise<ResolveResult> {
      const profile = await getMerchantProfileByShop(shop);

      if (!profile.ok) {
        return { ok: false, error: profile.error || "Profile lookup failed" };
      }

      const data = profile.data as MerchantProfile | null;

      if (!data?.merchant_id) {
        return { ok: false, error: "Unable to resolve merchant identity" };
      }

      return {
        ok: true,
        merchant_id: data.merchant_id,
        created: false,
      };
    }

    async function run() {
      setBusy(true);
      setError(null);

      const result = await resolve();

      if (cancelled) return;

      if (!result.ok) {
        setBusy(false);
        setError(result.error);
        return;
      }

      setMerchantId(result.merchant_id);
      setBusy(false);
      setStep(2);
    }

    run();

    return () => {
      cancelled = true;
    };
  }, [shop]);

  /* -----------------------------
     UI
  ------------------------------ */

  if (busy) {
    return <div className="p-6 text-sm text-gray-500">Initializing…</div>;
  }

  if (error) {
    return (
      <div className="p-6 space-y-2">
        <div className="text-lg font-semibold">Exclusivity — Onboarding</div>
        <div className="text-sm text-red-600">{error}</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-3">
      <div className="text-lg font-semibold">Exclusivity — Onboarding</div>
      <div className="text-sm text-gray-500">Step {step} of 5</div>

      {merchantId && (
        <div className="text-xs text-gray-400">
          merchant_id: {merchantId}
        </div>
      )}
    </div>
  );
}
