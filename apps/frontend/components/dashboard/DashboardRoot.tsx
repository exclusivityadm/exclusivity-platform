"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ApiResult,
  getMerchantProfileById,
  getBrandStatusByShop,
} from "@/lib/exclusivityApi";

import EngineStatusCard from "@/components/dashboard/EngineStatusCard";
import LedgerSummaryCard from "@/components/dashboard/LedgerSummaryCard";
import ActionsPanel from "@/components/dashboard/ActionsPanel";

type MerchantProfile = {
  merchant_id: string;
  shop_domain?: string | null;
  name?: string | null;
  created_at?: string | null;
};

type BrandStatus = {
  ok?: boolean;
  status?: string;
  initialized?: boolean;
  shop_domain?: string;
};

export default function DashboardRoot({ merchantId }: { merchantId: string }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [profile, setProfile] = useState<MerchantProfile | null>(null);
  const [brandStatus, setBrandStatus] = useState<BrandStatus | null>(null);

  const shopDomain = useMemo(() => profile?.shop_domain || null, [profile]);

  useEffect(() => {
    let cancelled = false;

    async function hydrate() {
      setLoading(true);
      setError(null);

      const p = await getMerchantProfileById(merchantId);
      if (!p.ok) {
        if (!cancelled) {
          setError(p.error || "Unable to load merchant profile");
          setLoading(false);
        }
        return;
      }

      const prof = p.data as MerchantProfile;
      if (!cancelled) setProfile(prof);

      // Brand status currently keyed by shop_domain (canonical safe path)
      if (prof?.shop_domain) {
        const bs = await getBrandStatusByShop(prof.shop_domain);
        if (!cancelled) {
          if (bs.ok) setBrandStatus(bs.data as BrandStatus);
          else setBrandStatus(null);
        }
      } else {
        if (!cancelled) setBrandStatus(null);
      }

      if (!cancelled) setLoading(false);
    }

    hydrate();
    return () => {
      cancelled = true;
    };
  }, [merchantId]);

  if (loading) {
    return <div className="p-6 text-sm text-gray-500">Loading dashboard…</div>;
  }

  if (error) {
    return (
      <div className="p-6 space-y-2">
        <div className="text-lg font-semibold">Exclusivity Dashboard</div>
        <div className="text-sm text-red-600">{error}</div>
        <div className="text-xs text-gray-500">merchant_id: {merchantId}</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <header className="space-y-1">
        <div className="text-xl font-semibold">Exclusivity Dashboard</div>
        <div className="text-xs text-gray-500">merchant_id: {merchantId}</div>
        <div className="text-xs text-gray-500">
          shop_domain: {shopDomain ?? "(not linked yet)"}
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <EngineStatusCard merchantId={merchantId} shopDomain={shopDomain} />
        <LedgerSummaryCard merchantId={merchantId} />
      </div>

      <ActionsPanel merchantId={merchantId} />

      <section className="border rounded p-4">
        <div className="font-medium mb-2">Merchant Profile (debug)</div>
        <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">
{JSON.stringify(profile, null, 2)}
        </pre>
      </section>

      <section className="border rounded p-4">
        <div className="font-medium mb-2">Brand / Engine Status (debug)</div>
        <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">
{JSON.stringify(brandStatus, null, 2)}
        </pre>
      </section>
    </div>
  );
}
