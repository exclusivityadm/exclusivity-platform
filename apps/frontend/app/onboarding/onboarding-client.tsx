"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getMerchantProfileByShop } from "@/lib/exclusivityApi";

/* ---------------------------------
   Canonical local types
---------------------------------- */

type MerchantProfile = {
  merchant_id: string;
};

type ResolveSuccess = {
  ok: true;
  merchant_id: string;
};

type ResolveFail = {
  ok: false;
  message: string;
};

type ResolveResult = ResolveSuccess | ResolveFail;

/* ---------------------------------
   Component
---------------------------------- */

export default function OnboardingClient() {
  const searchParams = useSearchParams();
  const shop = searchParams.get("shop");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [merchantId, setMerchantId] = useState<string | null>(null);
  const [step, setStep] = useState(1);

  useEffect(() => {
    if (!shop) {
      setError("Missing shop parameter");
      return;
    }

    let cancelled = false;

    async function resolveMerchant(): Promise<ResolveResult> {
      const res = await getMerchantProfileByShop(shop);

      if (!res.ok) {
        return { ok: false, message: "Profile lookup failed" };
      }

      const data = res.data as MerchantProfile | null;

      if (!data?.merchant_id) {
        return { ok: false, message: "Unable to resolve merchant identity" };
      }

      return { ok: true, merchant_id: data.merchant_id };
    }

    async function run() {
      setBusy(true);
      setError(null);

      const result = await resolveMerchant();

      if (cancelled) return;

      if (result.ok === false) {
        const { message } = result; // ✅ explicit branch extraction
        setBusy(false);
        setError(message);
        return;
      }

      const { merchant_id } = result; // ✅ explicit success branch
      setMerchantId(merchant_id);
      setStep(2);
      setBusy(false);
    }

    run();

    return () => {
      cancelled = true;
    };
  }, [shop]);

  /* ---------------------------------
     UI
  ---------------------------------- */

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
