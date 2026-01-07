"use client";

import { Section } from "./Section";

export function InvoicePanel({ invoice }: { invoice: any | null }) {
  return (
    <Section title="Latest Invoice" subtitle="Billing snapshot">
      {!invoice ? (
        <div className="text-sm text-neutral-400">
          No invoice generated yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="rounded-xl border border-neutral-800 p-4">
            <div className="text-xs text-neutral-400">Total</div>
            <div className="text-xl font-semibold">
              {((invoice.total_cents ?? 0) / 100).toFixed(2)}$
            </div>
          </div>
          <div className="rounded-xl border border-neutral-800 p-4">
            <div className="text-xs text-neutral-400">Status</div>
            <div className="text-sm font-medium">{invoice.status}</div>
          </div>
          <div className="rounded-xl border border-neutral-800 p-4">
            <div className="text-xs text-neutral-400">Period</div>
            <div className="text-sm">
              {invoice.period_start && invoice.period_end
                ? `${invoice.period_start} → ${invoice.period_end}`
                : "—"}
            </div>
          </div>
        </div>
      )}
    </Section>
  );
}
