"use client";

import { useEffect, useState } from "react";

type ApiOk<T> = { ok: true; data: T };
type ApiErr = { ok: false; error?: string };
type ApiResult<T> = ApiOk<T> | ApiErr;

type RouteInfo = {
  path: string;
  status: string;
};

type LoyaltyHealth = {
  status: "ok" | "degraded" | "down";
};

function getErrorMessage<T>(r: ApiResult<T>, fallback: string) {
  if (!r.ok && "error" in r && typeof r.error === "string" && r.error.trim()) {
    return r.error;
  }
  return fallback;
}

export default function EngineStatusCard() {
  const [routes, setRoutes] = useState<RouteInfo[]>([]);
  const [health, setHealth] = useState<LoyaltyHealth | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const base = process.env.NEXT_PUBLIC_BACKEND_URL || "";

        const rRes = await fetch(`${base}/api/routes`, {
          credentials: "include",
        });

        const r: ApiResult<RouteInfo[]> = rRes.ok
          ? await rRes.json()
          : { ok: false, error: "Failed to load routes" };

        if (!cancelled) {
          if (r.ok) setRoutes(r.data);
          else setErr(getErrorMessage(r, "Failed to load routes"));
        }

        const hRes = await fetch(`${base}/api/loyalty/health`, {
          credentials: "include",
        });

        const h: ApiResult<LoyaltyHealth> = hRes.ok
          ? await hRes.json()
          : { ok: false };

        if (!cancelled && h.ok) {
          setHealth(h.data);
        }
      } catch {
        if (!cancelled) {
          setErr("Unable to contact backend services");
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="rounded-md border p-4">
      <h3 className="text-sm font-medium mb-2">Engine Status</h3>

      {err && <p className="text-sm text-red-600">{err}</p>}

      {!err && (
        <div className="text-sm space-y-1">
          <p>
            Routes detected:{" "}
            <span className="font-medium">{routes.length}</span>
          </p>
          <p>
            Loyalty engine:{" "}
            <span className="font-medium">
              {health?.status || "checking…"}
            </span>
          </p>
        </div>
      )}
    </div>
  );
}
