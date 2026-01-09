"use client";

import { useEffect, useState } from "react";

/**
 * Frontend-local merchant shape.
 * The frontend must be independently deployable (no shared backend imports).
 */
type MerchantProfile = {
  merchant_id: string;
  shop_domain: string;
  store_name?: string;
  plan_name?: string;
  sniff_state?: "not_started" | "queued" | "running" | "completed" | "failed";
};

type ApiOk<T> = { ok: true; data: T };
type ApiErr = { ok: false; error?: string };
type ApiResult<T> = ApiOk<T> | ApiErr;

function getErrorMessage<T>(r: ApiResult<T>): string {
  // Explicit narrowing that TypeScript always accepts.
  if (!r.ok && "error" in r && typeof r.error === "string" && r.error.trim()) {
    return r.error;
  }
  return "Unable to load merchant profile";
}

export default function DashboardRoot() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [merchant, setMerchant] = useState<MerchantProfile | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadMerchant() {
      setLoading(true);
      setError(null);

      let result: ApiResult<MerchantProfile>;

      try {
        const base = process.env.NEXT_PUBLIC_BACKEND_URL || "";
        const url = `${base}/api/merchant/profile`;

        const res = await fetch(url, { credentials: "include" });

        if (!res.ok) {
          result = { ok: false, error: "Backend request failed" };
        } else {
          result = (await res.json()) as ApiResult<MerchantProfile>;
        }
      } catch {
        result = { ok: false, error: "Network error contacting backend" };
      }

      if (!result.ok) {
        if (!cancelled) {
          setError(getErrorMessage(result));
          setLoading(false);
        }
        return;
      }

      if (!cancelled) {
        setMerchant(result.data);
        setLoading(false);
      }
    }

    loadMerchant();

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex h-full w-full items-center justify-center text-sm text-muted-foreground">
        Loading dashboard…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full w-full items-center justify-center text-sm text-red-600">
        {error}
      </div>
    );
  }

  if (!merchant) {
    return (
      <div className="flex h-full w-full items-center justify-center text-sm text-muted-foreground">
        No merchant context available.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <header>
        <h1 className="text-xl font-semibold">
          {merchant.store_name || merchant.shop_domain}
        </h1>
        <p className="text-sm text-muted-foreground">
          Plan: {merchant.plan_name || "Unknown"}
        </p>
      </header>

      <section className="rounded-md border p-4">
        <p className="text-sm">
          Store status:{" "}
          <span className="font-medium">
            {merchant.sniff_state === "completed"
              ? "Store detected"
              : merchant.sniff_state === "failed"
              ? "Detection needs attention"
              : "Detecting store…"}
          </span>
        </p>
      </section>
    </div>
  );
}
