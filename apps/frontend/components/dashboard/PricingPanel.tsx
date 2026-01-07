"use client";

import { Section } from "./Section";

export function PricingPanel({ rec }: { rec: any | null }) {
  return (
    <Section title="Pricing Recommendation" subtitle="Gas & margin optimized">
      {!rec ? (
        <div className="text-sm text-neutral-400">
          No recommendation yet. Capture a catalog snapshot to generate one.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="rounded-xl border border-neutral-800 p-4">
            <div className="text-xs text-neutral-400">Uplift</div>
            <div className="text-xl font-semibold">
              {rec.uplift_percent ?? 0}%
            </div>
          </div>
          <div className="rounded-xl border border-neutral-800 p-4">
            <div className="text-xs text-neutral-400">Buffer</div>
            <div className="text-xl font-semibold">
              {(rec.buffer_cents ?? 0) / 100}$
            </div>
          </div>
          <div className="rounded-xl border border-neutral-800 p-4">
            <div className="text-xs text-neutral-400">Generated</div>
            <div className="text-sm">
              {rec.created_at
                ? new Date(rec.created_at).toLocaleString()
                : "—"}
            </div>
          </div>
        </div>
      )}
    </Section>
  );
}
