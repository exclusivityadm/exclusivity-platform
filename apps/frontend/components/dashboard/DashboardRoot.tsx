"use client";

/**
 * DashboardRoot
 * ---------------
 * Read-only dashboard hydration layer.
 * Safe under Next.js App Router + Turbopack.
 *
 * Responsibilities:
 * - Fetch merchant profile
 * - Fetch brand / engine status
 * - Handle loading + error states
 * - NEVER mutate data
 *
 * Props:
 * - merchantId (string) — REQUIRED
 */

import { useEffect, useState } from "react";
import {
  getMerchantProfileByShop,
  getBrandStatusByShop,
} from "@/lib/exclusivityApi";

type MerchantProfile = {
  id?: string;
  merchant_id?: string;
  shop_domain?: string;
  name?: string;
  created_at?: string;
};

type BrandStatus = {
  ok?: boolean;
  status?: string;
  initialized?: boolean;
};

export default function DashboardRoot({ merchantId }: { merchantId: string }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<MerchantProfile | null>(null);
  const [brandStatus, setBrandStatus] = useState<BrandStatus | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function hydrate() {
      setLoading(true);
      setError(null);

      try {
        // NOTE:
        // merchantId is currently the shop_domain in early lifecycle
        const profileRes = await getMerchantProfileByShop(merchantId);
        if (!profileRes.ok) {
          throw new Error("Unable to load merchant profile");
        }

        const brandRes = await getBrandStatusByShop(merchantId);
        if (!brandRes.ok) {
          throw new Error("Unable to load brand status");
        }

        if (!cancelled) {
          setProfile(profileRes.data ?? null);
          setBrandStatus(brandRes.data ?? null);
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.message || "Dashboard failed to load");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    hydrate();

    return () => {
      cancelled = true;
    };
  }, [merchantId]);

  /* ---------------- Rendering ---------------- */

  if (loading) {
    return (
      <div className="p-6 text-sm text-gray-500">
        Loading dashboard…
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-sm text-red-600">
        {error}
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <section>
        <h1 className="text-xl font-semibold">Exclusivity Dashboard</h1>
        <p className="text-sm text-gray-500">
          Merchant ID: {merchantId}
        </p>
      </section>

      <section className="border rounded p-4">
        <h2 className="font-medium mb-2">Merchant Profile</h2>
        <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">
{JSON.stringify(profile, null, 2)}
        </pre>
      </section>

      <section className="border rounded p-4">
        <h2 className="font-medium mb-2">Brand / Engine Status</h2>
        <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">
{JSON.stringify(brandStatus, null, 2)}
        </pre>
      </section>
    </div>
  );
}
