"use client";

import React, { useEffect, useState } from "react";
import { Section } from "@/components/dashboard/Section";
import { HealthBadge } from "@/components/dashboard/HealthBadge";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { BriefingPanel } from "@/components/dashboard/BriefingPanel";
import {
  getSystemHealth,
  getLoyaltyHealth,
  getDailyBriefing,
} from "@/lib/dashboardApi";

function param(name: string) {
  if (typeof window === "undefined") return "";
  return new URL(window.location.href).searchParams.get(name) || "";
}

export default function DashboardPage() {
  const merchant_id = param("merchant_id");

  const [sys, setSys] = useState<any | null>(null);
  const [loyalty, setLoyalty] = useState<any | null>(null);
  const [briefing, setBriefing] = useState<any | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setErr(null);
    getSystemHealth().then((r) => r.ok && setSys(r.data));
    getLoyaltyHealth().then((r) => r.ok && setLoyalty(r.data));
    if (merchant_id) {
      getDailyBriefing(merchant_id).then((r) => r.ok && setBriefing(r.data));
    }
  }, [merchant_id]);

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-50 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Exclusivity — Dashboard</h1>
          <div className="flex gap-2">
            <HealthBadge ok={!!sys?.ok} label="System" />
            <HealthBadge ok={!!loyalty?.ok} label="Loyalty" />
          </div>
        </header>

        <Section title="Engine Health">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <MetricCard
              label="System"
              value={sys?.ok ? "OK" : "Unknown"}
              hint="/health"
            />
            <MetricCard
              label="Loyalty"
              value={loyalty?.ok ? "OK" : "Unknown"}
              hint="/loyalty/health"
            />
            <MetricCard
              label="Merchant"
              value={merchant_id || "Not provided"}
              hint="pass ?merchant_id=..."
            />
          </div>
        </Section>

        <BriefingPanel briefing={briefing?.briefing ?? briefing} />

        {err && (
          <div className="text-sm text-red-400">
            {err}
          </div>
        )}
      </div>
    </div>
  );
}
