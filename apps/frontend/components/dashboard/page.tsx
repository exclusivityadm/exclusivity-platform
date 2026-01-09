"use client";

import React, { useEffect, useState } from "react";
import { Section } from "@/components/dashboard/Section";
import { HealthBadge } from "@/components/dashboard/HealthBadge";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { BriefingPanel } from "@/components/dashboard/BriefingPanel";
import { PricingPanel } from "@/components/dashboard/PricingPanel";
import { MintActivityPanel } from "@/components/dashboard/MintActivityPanel";
import { InvoicePanel } from "@/components/dashboard/InvoicePanel";
import ActionsPanel from "@/components/dashboard/ActionsPanel";

import { getSystemHealth, getLoyaltyHealth } from "@/lib/dashboardApi";
import { getLatestPricing, getMintJobs, getLatestInvoice } from "@/lib/ui03Api";

function param(name: string) {
  if (typeof window === "undefined") return "";
  return new URL(window.location.href).searchParams.get(name) || "";
}

export default function DashboardPage() {
  const merchantId = param("merchant_id");

  const [sys, setSys] = useState<any | null>(null);
  const [loyalty, setLoyalty] = useState<any | null>(null);
  const [briefing, setBriefing] = useState<any | null>(null);

  const [pricing, setPricing] = useState<any | null>(null);
  const [jobs, setJobs] = useState<any[] | null>(null);
  const [invoice, setInvoice] = useState<any | null>(null);

  useEffect(() => {
    getSystemHealth().then((r) => r.ok && setSys(r.data));
    getLoyaltyHealth().then((r) => r.ok && setLoyalty(r.data));
  }, []);

  useEffect(() => {
    if (!merchantId) return;

    import("@/lib/dashboardApi").then(({ getDailyBriefing }) => {
      getDailyBriefing(merchantId).then((r: any) => r.ok && setBriefing(r.data));
    });

    getLatestPricing(merchantId).then((r) => r.ok && setPricing(r.data));
    getMintJobs(merchantId).then((r) => r.ok && setJobs(r.data));
    getLatestInvoice(merchantId).then((r) => r.ok && setInvoice(r.data));
  }, [merchantId]);

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
            <MetricCard label="System" value={sys?.ok ? "OK" : "—"} />
            <MetricCard label="Loyalty" value={loyalty?.ok ? "OK" : "—"} />
            <MetricCard label="Merchant" value={merchantId || "—"} />
          </div>
        </Section>

        <BriefingPanel briefing={briefing?.briefing ?? briefing} />
        <PricingPanel rec={pricing} />
        <MintActivityPanel jobs={jobs} />
        <InvoicePanel invoice={invoice} />

        {merchantId ? (
          <ActionsPanel merchantId={merchantId} />
        ) : (
          <Section title="Actions">
            <div className="text-sm text-neutral-400">
              Provide <code className="text-neutral-200">?merchant_id=...</code> to enable actions.
            </div>
          </Section>
        )}
      </div>
    </div>
  );
}
