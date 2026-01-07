"use client";

import React, { useEffect, useMemo, useState } from "react";

type ResolveResult =
  | { ok: true; merchant_id: string; shop_domain: string; created?: boolean }
  | { ok: false; error: string; details?: any };

type BackfillResult =
  | { ok: true; merchant_id: string; shop_domain: string; started: boolean; result?: any }
  | { ok: false; error: string; details?: any };

const STEPS = ["Welcome", "Verify Engine", "Resolve Merchant", "Backfill", "Done"];

function getParam(name: string): string | null {
  if (typeof window === "undefined") return null;
  const u = new URL(window.location.href);
  return u.searchParams.get(name);
}

export default function OnboardingPage() {
  const shop = useMemo(() => getParam("shop"), []);
  const [step, setStep] = useState(0);

  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const [merchantId, setMerchantId] = useState<string | null>(null);
  const [engineOk, setEngineOk] = useState<boolean | null>(null);
  const [created, setCreated] = useState<boolean>(false);

  useEffect(() => {
    if (!shop) {
      setMsg("Missing shop parameter");
      setStep(0);
      return;
    }
    setMsg(null);
    setStep(0);
  }, [shop]);

  async function verifyEngine() {
    setBusy(true);
    setMsg(null);
    setEngineOk(null);

    try {
      const r = await fetch("/api/engine-check", { cache: "no-store" });
      const j = await r.json().catch(() => null);
      if (!r.ok) {
        setEngineOk(false);
        setMsg(j?.error || "Engine check failed");
        setBusy(false);
        return;
      }
      setEngineOk(true);
      setBusy(false);
      setStep(2);
    } catch (e: any) {
      setEngineOk(false);
      setMsg(e?.message || "Engine check error");
      setBusy(false);
    }
  }

  async function resolveMerchant() {
    if (!shop) return;

    setBusy(true);
    setMsg(null);
    setMerchantId(null);
    setCreated(false);

    try {
      const r = await fetch("/api/resolve-merchant", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ shop_domain: shop }),
        cache: "no-store",
      });

      const j = (await r.json().catch(() => null)) as ResolveResult | null;

      if (!r.ok || !j || (j as any).ok !== true) {
        setMsg((j as any)?.error || "Unable to resolve merchant identity");
        setBusy(false);
        return;
      }

      setMerchantId(j.merchant_id);
      setCreated(Boolean(j.created));
      setBusy(false);
      setStep(3);
    } catch (e: any) {
      setMsg(e?.message || "Unable to resolve merchant identity");
      setBusy(false);
    }
  }

  async function runBackfill() {
    if (!shop || !merchantId) return;

    setBusy(true);
    setMsg(null);

    try {
      const r = await fetch("/api/run-backfill", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ shop_domain: shop, merchant_id: merchantId, points_per_dollar: 1.0 }),
        cache: "no-store",
      });

      const j = (await r.json().catch(() => null)) as BackfillResult | null;

      if (!r.ok || !j || (j as any).ok !== true) {
        setMsg((j as any)?.error || "Backfill failed to start");
        setBusy(false);
        return;
      }

      setBusy(false);
      setStep(4);

      // UI-05 handoff: redirect to dashboard with canonical UUID
      window.location.href = `/dashboard?merchant_id=${encodeURIComponent(merchantId)}`;
    } catch (e: any) {
      setMsg(e?.message || "Backfill failed to start");
      setBusy(false);
    }
  }

  // Auto-advance path for install-like behavior:
  // Welcome -> Verify -> Resolve -> Backfill (auto-run)
  useEffect(() => {
    if (!shop) return;
    // step 1: user clicks continue; we do not auto-run without an explicit click
  }, [shop]);

  const stepLabel = STEPS[Math.min(step, STEPS.length - 1)];

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-6">
      <div className="w-full max-w-2xl rounded-2xl border border-neutral-800 bg-neutral-950/40 p-6 shadow">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xl font-semibold">Exclusivity — Onboarding</div>
            <div className="mt-1 text-sm text-neutral-400">
              Step {step + 1} of {STEPS.length}: {stepLabel}
            </div>
          </div>
          {shop ? (
            <div className="text-xs text-neutral-400">
              Shop: <span className="text-neutral-200">{shop}</span>
            </div>
          ) : null}
        </div>

        <div className="mt-6 space-y-4">
          {msg ? (
            <div className="rounded-xl border border-red-900/40 bg-red-950/20 p-3 text-sm text-red-200">
              {msg}
            </div>
          ) : null}

          {step === 0 ? (
            <div className="space-y-3">
              <div className="text-sm text-neutral-300">
                Exclusivity installs as an engine-first merchant intelligence system. We verify the engine,
                resolve your canonical merchant UUID, then run the historical backfill before any AI onboarding.
              </div>

              {!shop ? (
                <div className="text-sm text-neutral-400">
                  This page must be launched with a Shopify-style shop parameter:
                  <div className="mt-2 rounded-lg border border-neutral-800 bg-neutral-950 p-3 font-mono text-xs">
                    /onboarding?shop=your-store.myshopify.com
                  </div>
                </div>
              ) : (
                <button
                  className="w-full rounded-xl bg-white text-black py-2 text-sm font-medium disabled:opacity-60"
                  disabled={busy}
                  onClick={() => {
                    setStep(1);
                    verifyEngine();
                  }}
                >
                  Continue
                </button>
              )}
            </div>
          ) : null}

          {step === 1 ? (
            <div className="space-y-3">
              <div className="text-sm text-neutral-300">Verifying engine connectivity…</div>

              <div className="rounded-xl border border-neutral-800 bg-neutral-950 p-3 text-sm text-neutral-300">
                Engine status:{" "}
                {engineOk === null ? (
                  <span className="text-neutral-400">checking…</span>
                ) : engineOk ? (
                  <span className="text-emerald-300">ok</span>
                ) : (
                  <span className="text-red-300">failed</span>
                )}
              </div>

              <button
                className="w-full rounded-xl bg-white text-black py-2 text-sm font-medium disabled:opacity-60"
                disabled={busy || engineOk !== true}
                onClick={() => {
                  setStep(2);
                }}
              >
                Next
              </button>
            </div>
          ) : null}

          {step === 2 ? (
            <div className="space-y-3">
              <div className="text-sm text-neutral-300">
                Resolving canonical merchant identity (UUID-first). Shopify IDs are metadata only.
              </div>

              <button
                className="w-full rounded-xl bg-white text-black py-2 text-sm font-medium disabled:opacity-60"
                disabled={busy || !shop}
                onClick={resolveMerchant}
              >
                Resolve Merchant
              </button>

              {merchantId ? (
                <div className="rounded-xl border border-neutral-800 bg-neutral-950 p-3 text-xs text-neutral-300">
                  merchant_id: <span className="font-mono text-neutral-100">{merchantId}</span>
                  {created ? <div className="mt-1 text-neutral-400">(created)</div> : null}
                </div>
              ) : null}
            </div>
          ) : null}

          {step === 3 ? (
            <div className="space-y-3">
              <div className="text-sm text-neutral-300">
                Running Shopify historical backfill. This must happen before AI onboarding.
              </div>

              <div className="rounded-xl border border-neutral-800 bg-neutral-950 p-3 text-xs text-neutral-300">
                merchant_id: <span className="font-mono text-neutral-100">{merchantId || "—"}</span>
                <div className="mt-1 text-neutral-400">
                  Backfill is executed server-side using secure env tokens (not exposed to the browser).
                </div>
              </div>

              <button
                className="w-full rounded-xl bg-white text-black py-2 text-sm font-medium disabled:opacity-60"
                disabled={busy || !merchantId || !shop}
                onClick={runBackfill}
              >
                Run Backfill Now
              </button>
            </div>
          ) : null}

          {step >= 4 ? (
            <div className="space-y-3">
              <div className="text-sm text-neutral-300">Backfill started. Redirecting to dashboard…</div>
              <div className="text-xs text-neutral-500">
                If you are not redirected automatically, open:
                <div className="mt-2 rounded-lg border border-neutral-800 bg-neutral-950 p-3 font-mono text-xs">
                  /dashboard?merchant_id={merchantId || "<merchant_id>"}
                </div>
              </div>
            </div>
          ) : null}
        </div>

        <div className="mt-6 text-xs text-neutral-500">
          UI-05 implements install → merchant resolution → backfill handoff. AI onboarding is deferred until the
          engine is complete.
        </div>
      </div>
    </div>
  );
}
