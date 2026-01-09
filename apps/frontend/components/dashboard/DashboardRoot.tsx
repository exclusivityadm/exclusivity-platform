"use client";

import { useEffect, useState } from "react";
import type { MerchantProfile } from "../../lib/types/merchant";

type ApiOk<T> = {
  ok: true;
  data: T;
};

type ApiErr = {
  ok: false;
  error?: string;
};

type ApiResult<T> = ApiOk<T> | ApiErr;

/**
 * NOTE:
 * The frontend calls the backend over HTTP.
 * We do NOT import backend API helpers into the frontend.
 */

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
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/merchant/profile`,
          {
            credentials: "include",
          }
        );

        if (!res.ok) {
          result = { ok: false, error: "Backend request failed" };
        } else {
          result = await res.json();
        }
      } catch {
        result = { ok: false, error: "Network error contacting backend" };
      }

      if (!result.ok) {
        if (!cancelled) {
          setError(
            typeof result.error === "string"
              ? result.error
              : "Unable to load merchant profile"
          );
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
