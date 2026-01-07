"use client";

import { useEffect, useState } from "react";
import {
  getBrandStatusByShop,
  getDebugRoutes,
  getInitQuestions,
  getMerchantProfileByShop,
  saveInitAnswers,
  type MerchantProfile,
} from "@/lib";

const STEPS = ["Welcome", "Verify Engine", "Backfill", "Brand DNA", "Done"];

function getShopParam(): string {
  if (typeof window === "undefined") return "";
  return new URL(window.location.href).searchParams.get("shop") || "";
}

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const [merchantId, setMerchantId] = useState<string | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [questions, setQuestions] = useState<string[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      const shop = getShopParam();
      if (!shop) {
        setError("Missing shop parameter");
        return;
      }

      const p = await getMerchantProfileByShop(shop);

      // ✅ Explicit union narrowing (required for Next build)
      if (p.ok === true) {
        const data = p.data as MerchantProfile;

        const id = data.merchant_id || data.id;
        if (!id) {
          setError("Merchant profile missing ID");
          return;
        }

        setMerchantId(id);
        setStatus(data);
        return;
      }

      const b = await getBrandStatusByShop(shop);
      if (b.ok === true) {
        setStatus(b.data);
        return;
      }

      setError("Unable to resolve merchant identity");
    };

    run();
  }, []);

  useEffect(() => {
    if (!merchantId) return;
    getInitQuestions().then((q) => {
      if (q.ok) setQuestions(q.data.questions);
    });
  }, [merchantId]);

  async function submitAnswers() {
    if (!merchantId) return;
    await saveInitAnswers(merchantId, answers);
    setStep(STEPS.length - 1);
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-50 p-8">
      <div className="max-w-3xl mx-auto space-y-6">
        <h1 className="text-2xl font-semibold">
          Exclusivity — Onboarding
        </h1>

        <p className="text-sm text-neutral-400">
          Step {step + 1} of {STEPS.length}: {STEPS[step]}
        </p>

        {error && (
          <div className="rounded-md bg-red-950/50 border border-red-800 p-3 text-red-300">
            {error}
          </div>
        )}

        {questions.length > 0 && step < STEPS.length - 1 && (
          <div className="space-y-4">
            {questions.map((q) => (
              <div key={q}>
                <label className="block text-sm mb-1">{q}</label>
                <input
                  className="w-full rounded bg-neutral-900 border border-neutral-800 p-2"
                  value={answers[q] || ""}
                  onChange={(e) =>
                    setAnswers((a) => ({ ...a, [q]: e.target.value }))
                  }
                />
              </div>
            ))}
            <button
              onClick={submitAnswers}
              className="rounded bg-white text-black px-4 py-2"
            >
              Continue
            </button>
          </div>
        )}

        {step === STEPS.length - 1 && (
          <div className="text-emerald-400">
            Onboarding complete. Engine is active.
          </div>
        )}
      </div>
    </div>
  );
}
