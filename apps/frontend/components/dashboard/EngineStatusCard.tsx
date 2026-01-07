"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/exclusivityApi";

type DebugRoutes = { routes?: string[] } | any;

type LoyaltyHealth = {
  ok?: boolean;
  checks?: Record<string, boolean>;
  [k: string]: any;
};

export default function EngineStatusCard({
  merchantId,
  shopDomain,
}: {
  merchantId: string;
  shopDomain: string | null;
}) {
  const [routes, setRoutes] = useState<DebugRoutes | null>(null);
  const [loyalty, setLoyalty] = useState<LoyaltyHealth | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setErr(null);

      const r = await apiGet<DebugRoutes>("/debug/routes");
      if (!cancelled) {
        if (r.ok) setRoutes(r.data);
        else setErr(r.error || "Failed to load routes");
      }

      const lh = await apiGet<LoyaltyHealth>("/loyalty/health");
      if (!cancelled) {
        if (lh.ok) setLoyalty(lh.data);
        else setErr((prev) => prev || lh.error || "Failed to load loyalty health");
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, [merchantId, shopDomain]);

  const checks = loyalty?.checks || {};
  const checkList = Object.keys(checks);

  return (
    <section className="border rounded p-4 space-y-2">
      <div className="font-medium">Engine Status</div>

      {err && <div className="text-sm text-red-600">{err}</div>}

      <div className="text-xs text-gray-500">
        Backend routes: {routes ? "ok" : "unknown"}
      </div>

      <div className="text-xs text-gray-500">
        Loyalty health: {typeof loyalty?.ok === "boolean" ? String(loyalty.ok) : "unknown"}
      </div>

      {checkList.length > 0 && (
        <div className="text-xs">
          <div className="text-gray-500 mb-1">Checks</div>
          <ul className="list-disc pl-4 space-y-1">
            {checkList.map((k) => (
              <li key={k}>
                {k}:{" "}
                <span className={checks[k] ? "text-green-700" : "text-red-700"}>
                  {String(checks[k])}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
