"use client";

import React, { useEffect, useState } from "react";
import { StepShell } from "@/components/onboarding/StepShell";
import { ProgressPills } from "@/components/onboarding/ProgressPills";
import { ButtonRow } from "@/components/onboarding/ButtonRow";
import {
  getBrandStatusByShop,
  getDebugRoutes,
  getInitQuestions,
  getMerchantProfileByShop,
  saveInitAnswers,
} from "@/lib/exclusivityApi";

const STEPS = ["Welcome", "Verify Engine", "Backfill", "Brand DNA", "Done"];

function param(name: string) {
  if (typeof window === "undefined") return "";
  return new URL(window.location.href).searchParams.get(name) || "";
}

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [shop] = useState(param("shop") || param("shop_domain"));
  const [merchantId, setMerchantId] = useState<string | undefined>();
  const [questions, setQuestions] = useState<string[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<any>(null);

  async function discoverMerchant() {
    if (!shop) return;
    const p = await getMerchantProfileByShop(shop);
    if (p.ok) {
      setMerchantId(p.data?.merchant_id || p.data?.id);
      setStatus(p.data);
      return;
    }
    const b = await getBrandStatusByShop(shop);
    if (b.ok) {
      setMerchantId(b.data?.merchant_id || b.data?.id);
      setStatus(b.data);
    }
  }

  useEffect(() => {
    discoverMerchant();
    getInitQuestions().then((r) => r.ok && setQuestions(r.data.questions));
  }, []);

  async function verifyEngine() {
    setBusy(true);
    setError(null);
    const r = await getDebugRoutes();
    setBusy(false);
    if (!r.ok) {
      setError("Backend unreachable. Check NEXT_PUBLIC_BACKEND_URL.");
      return false;
    }
    return true;
  }

  async function saveDNA() {
    if (!merchantId) {
      setError("Missing merchant_id.");
      return false;
    }
    setBusy(true);
    setError(null);
    const r = await saveInitAnswers(merchantId, answers);
    setBusy(false);
    if (!r.ok) {
      setError("Failed to save Brand DNA.");
      return false;
    }
    return true;
  }

  return (
    <StepShell
      title="Exclusivity — Merchant Onboarding"
      subtitle={shop ? `Shop: ${shop}` : "Provide ?shop=myshop.myshopify.com"}
    >
      <ProgressPills steps={STEPS} index={step} />

      {step === 0 && (
        <>
          <p className="text-sm text-neutral-300">
            This wizard initializes the Exclusivity engine. Customers never see
            loyalty mechanics unless you expose them.
          </p>
          <ButtonRow
            backLabel="Exit"
            onBack={() => (window.location.href = "/")}
            nextLabel="Verify Engine"
            onNext={async () => (await verifyEngine()) && setStep(1)}
            busy={busy}
          />
        </>
      )}

      {step === 1 && (
        <>
          <pre className="text-xs bg-neutral-950 p-3 rounded-xl border border-neutral-800">
            {JSON.stringify(status ?? { note: "No status yet" }, null, 2)}
          </pre>
          {error && <div className="text-sm text-red-400">{error}</div>}
          <ButtonRow onBack={() => setStep(0)} onNext={() => setStep(2)} />
        </>
      )}

      {step === 2 && (
        <>
          <p className="text-sm text-neutral-300">
            Backfill runs automatically after install. This screen reflects any
            available status.
          </p>
          <pre className="text-xs bg-neutral-950 p-3 rounded-xl border border-neutral-800">
            {JSON.stringify(status ?? {}, null, 2)}
          </pre>
          <ButtonRow onBack={() => setStep(1)} onNext={() => setStep(3)} />
        </>
      )}

      {step === 3 && (
        <>
          {questions.map((q) => (
            <div key={q} className="border border-neutral-800 rounded-xl p-3">
              <div className="text-sm">{q}</div>
              <textarea
                className="mt-2 w-full bg-neutral-900 border border-neutral-700 rounded-xl p-2 text-sm"
                rows={3}
                value={answers[q] || ""}
                onChange={(e) =>
                  setAnswers((a) => ({ ...a, [q]: e.target.value }))
                }
              />
            </div>
          ))}
          <ButtonRow
            onBack={() => setStep(2)}
            nextLabel="Finish"
            onNext={async () => (await saveDNA()) && setStep(4)}
            nextDisabled={!merchantId}
            busy={busy}
          />
        </>
      )}

      {step === 4 && (
        <>
          <p className="text-sm text-neutral-300">
            Setup complete. Orion/Lyric can now generate briefings and guide
            actions.
          </p>
          <ButtonRow
            backLabel="Back"
            nextLabel="Go to Dashboard"
            onBack={() => setStep(3)}
            onNext={() => (window.location.href = "/")}
          />
        </>
      )}
    </StepShell>
  );
}
