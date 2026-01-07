"use client";

import { useState } from "react";
import { previewAction } from "@/lib/exclusivityApi";

/* ---------------------------------
   Local canonical result
---------------------------------- */

type PreviewOk = {
  ok: true;
  data: any;
};

type PreviewFail = {
  ok: false;
  message: string;
};

type PreviewResult = PreviewOk | PreviewFail;

/* ---------------------------------
   Component
---------------------------------- */

export default function ActionsPanel({ merchantId }: { merchantId: string }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [preview, setPreview] = useState<any>(null);

  async function runPreview(action: Record<string, any>) {
    setBusy(true);
    setErr(null);

    // ✅ FIX: pass merchantId explicitly
    const res = await previewAction(merchantId, action);

    const normalized: PreviewResult = res.ok
      ? { ok: true, data: res.data }
      : { ok: false, message: "Preview failed" };

    if (!normalized.ok) {
      setErr(normalized.message);
      setBusy(false);
      return;
    }

    setPreview(normalized.data);
    setBusy(false);
  }

  return (
    <div className="p-4 border rounded space-y-3">
      <div className="font-semibold">AI Actions</div>

      {err && <div className="text-sm text-red-600">{err}</div>}

      <button
        disabled={busy}
        onClick={() =>
          runPreview({
            type: "daily_summary",
          })
        }
        className="px-3 py-1 rounded bg-black text-white text-sm disabled:opacity-50"
      >
        {busy ? "Previewing…" : "Preview Action"}
      </button>

      {preview && (
        <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto">
          {JSON.stringify(preview, null, 2)}
        </pre>
      )}
    </div>
  );
}
