"use client";

import { useEffect, useState } from "react";

/**
 * IMPORTANT:
 * This project is a monorepo. In production (Vercel + Turbopack),
 * the `@/` alias resolves relative to `apps/frontend`, not repo root.
 *
 * Therefore ALL frontend imports must be relative unless the alias
 * is explicitly reconfigured.
 */

import { fetchMerchantProfile } from "../../lib/api/merchant";
import type { ApiResult } from "../../lib/api/types";
import type { MerchantProfile } from "../../lib/types/merchant";

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
        result = await fetchMerchantProfile();
      } catch {
        if (!cancelled) {
          setError("Unable to load merchant profile");
          setLoading(false);
        }
        return;
      }

      if (!result.ok) {
        if (!cancelled) {
          const message =
            "error" in result && typeof result.error === "string"
              ? result.error
              : "Unable to load merchant profile";

          setError(message);
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
          Plan: {merchant.plan_name}
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
