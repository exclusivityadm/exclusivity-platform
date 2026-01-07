"use client";

/**
 * ActionsPanel (Phase 06)
 * -----------------------
 * Wires AI action preview + execute.
 * Backend enforces plan gating (Preview tier cannot execute).
 *
 * Endpoints:
 * - POST /ai/action/preview  { merchant_id, action }
 * - POST /ai/action/execute  { merchant_id, action }
 */

import { useMemo, useState } from "react";
import { previewAction, executeAction } from "@/lib/exclusivityApi";

type ActionPreviewResult = any;
type ActionExecuteResult = any;

export default function ActionsPanel({ merchantId }: { merchantId: string }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [preview, setPreview] = useState<ActionPreviewResult | null>(null);
  const [executed, setExecuted] = useState<ActionExecuteResult | null>(null);

  const sampleAction = useMemo(
    () => ({
      type: "daily_briefing_send",
      channel: "email",
      payload: {
        subject: "Today’s Briefing",
        notes: "Sample action from dashboard to validate execution surface.",
      },
    }),
    []
  );

  async function doPreview() {
    setBusy(true);
    setErr(null);
    setExecuted(null);

    const r = await previewAction(merchantId, sampleAction);
    if (!r.ok) {
      setBusy(false);
      setErr(r.error || "Preview failed");
      return;
    }

    setPreview(r.data);
    setBusy(false);
  }

  async function doExecute() {
    setBusy(true);
    setErr(null);

    const r = await executeAction(merchantId, sampleAction);
    if (!r.ok) {
      setBusy(false);
      // Backend may return 403 with message in details
      const msg =
        r.details?.message ||
        r.error ||
        "Execute failed";
      setErr(msg);
      return;
    }

    setExecuted(r.data);
    setBusy(false);
  }

  return (
    <section className="border rounded p-4 space-y-3">
      <div className="font-medium">AI Actions</div>

      <div className="text-xs text-gray-500">
        Preview is always allowed. Execute is tier-gated by backend.
      </div>

      {err && <div className="text-sm text-red-600">{err}</div>}

      <div className="flex gap-2">
        <button
          className="border rounded px-3 py-2 text-sm"
          onClick={doPreview}
          disabled={busy}
        >
          {busy ? "Working…" : "Preview Action"}
        </button>

        <button
          className="border rounded px-3 py-2 text-sm"
          onClick={doExecute}
          disabled={busy}
        >
          {busy ? "Working…" : "Execute Action"}
        </button>
      </div>

      <div className="grid md:grid-cols-2 gap-3">
        <div className="space-y-1">
          <div className="text-xs text-gray-500">Preview result</div>
          <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto min-h-[120px]">
{JSON.stringify(preview, null, 2)}
          </pre>
        </div>

        <div className="space-y-1">
          <div className="text-xs text-gray-500">Execute result</div>
          <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto min-h-[120px]">
{JSON.stringify(executed, null, 2)}
          </pre>
        </div>
      </div>
    </section>
  );
}
