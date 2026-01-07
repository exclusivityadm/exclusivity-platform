"use client";

import React, { useMemo, useState } from "react";
import { Section } from "./Section";
import { ActionModal } from "./ActionModal";
import { previewAction, executeAction, ActionPayload } from "@/lib/ui04Actions";
import { downloadCsv } from "@/lib/csv";

export function ActionsPanel(props: {
  merchant_id: string;
  pricing: any | null;
  jobs: any[] | null;
  invoice: any | null;
}) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [preview, setPreview] = useState<any | null>(null);
  const [execResult, setExecResult] = useState<any | null>(null);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<ActionPayload | null>(null);

  const failedJobsCount = useMemo(() => {
    const list = props.jobs || [];
    return list.filter((j) => j?.status === "failed").length;
  }, [props.jobs]);

  async function openFor(action: ActionPayload, label: string) {
    setError(null);
    setExecResult(null);
    setPreview(null);
    setPendingAction(action);
    setTitle(label);
    setOpen(true);

    const p = await previewAction(action);

    // ✅ Discriminated union narrowing (canonical)
    if (!p.ok) {
      setError(p.error);
      return;
    }

    setPreview(p.data);
  }

  async function onExecute() {
    if (!pendingAction) return;

    setExecuting(true);
    setError(null);
    setExecResult(null);

    const r = await executeAction(pendingAction);

    setExecuting(false);

    // ✅ Discriminated union narrowing (canonical)
    if (!r.ok) {
      setError(r.error);
      return;
    }

    setExecResult(r.data);
  }

  function exportInvoiceCsv() {
    if (!props.invoice) return;
    downloadCsv("exclusivity-invoice-latest.csv", [props.invoice]);
  }

  return (
    <>
      <Section title="Actions" subtitle="Approve actions before execution">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Apply Pricing */}
          <div className="rounded-xl border border-neutral-800 bg-neutral-950/40 p-4">
            <div className="text-sm font-medium">Apply Pricing</div>
            <div className="mt-1 text-xs text-neutral-400">
              Applies latest recommendation to catalog.
            </div>
            <button
              className="mt-3 w-full rounded-lg bg-white px-3 py-2 text-sm text-black disabled:opacity-60"
              disabled={!props.merchant_id || !props.pricing}
              onClick={() =>
                openFor(
                  {
                    intent: "pricing.apply_recommendation",
                    merchant_id: props.merchant_id,
                    params: {
                      recommendation_id: props.pricing?.id || null,
                    },
                  },
                  "Apply Pricing Recommendation"
                )
              }
            >
              Preview & Approve
            </button>
          </div>

          {/* Retry Failed Mints */}
          <div className="rounded-xl border border-neutral-800 bg-neutral-950/40 p-4">
            <div className="text-sm font-medium">Retry Failed Mints</div>
            <div className="mt-1 text-xs text-neutral-400">
              Retries failed blockchain jobs ({failedJobsCount} failed).
            </div>
            <button
              className="mt-3 w-full rounded-lg bg-white px-3 py-2 text-sm text-black disabled:opacity-60"
              disabled={!props.merchant_id || failedJobsCount === 0}
              onClick={() =>
                openFor(
                  {
                    intent: "blockchain.retry_failed_jobs",
                    merchant_id: props.merchant_id,
                    params: { limit: 25 },
                  },
                  "Retry Failed Blockchain Jobs"
                )
              }
            >
              Preview & Approve
            </button>
          </div>

          {/* Export Invoice */}
          <div className="rounded-xl border border-neutral-800 bg-neutral-950/40 p-4">
            <div className="text-sm font-medium">Export Invoice</div>
            <div className="mt-1 text-xs text-neutral-400">
              Download latest invoice snapshot as CSV.
            </div>
            <button
              className="mt-3 w-full rounded-lg bg-white px-3 py-2 text-sm text-black disabled:opacity-60"
              disabled={!props.invoice}
              onClick={exportInvoiceCsv}
            >
              Download CSV
            </button>
          </div>
        </div>
      </Section>

      <ActionModal
        open={open}
        title={title}
        preview={preview}
        execResult={execResult}
        executing={executing}
        error={error}
        onClose={() => setOpen(false)}
        onExecute={onExecute}
      />
    </>
  );
}
