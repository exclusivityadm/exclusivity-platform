/**
 * Dashboard API client
 * Engine-first, auth-agnostic
 *
 * Env:
 *   NEXT_PUBLIC_BACKEND_URL
 */

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; status?: number; details?: any };

const BACKEND = (process.env.NEXT_PUBLIC_BACKEND_URL || "").replace(/\/$/, "");

function mustBackend(): string {
  if (!BACKEND) throw new Error("Missing NEXT_PUBLIC_BACKEND_URL");
  return BACKEND;
}

async function safeJson(res: Response) {
  const txt = await res.text();
  try {
    return txt ? JSON.parse(txt) : null;
  } catch {
    return txt;
  }
}

async function apiGet<T>(path: string): Promise<ApiResult<T>> {
  try {
    const res = await fetch(mustBackend() + path, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const payload = await safeJson(res);
    if (!res.ok)
      return { ok: false, error: "Request failed", status: res.status, details: payload };
    return { ok: true, data: payload as T };
  } catch (e: any) {
    return { ok: false, error: e?.message || "Network error" };
  }
}

/* ---- Canonical dashboard endpoints ---- */

export const getSystemHealth = () => apiGet<any>("/health");
export const getLoyaltyHealth = () => apiGet<any>("/loyalty/health");

export const getDailyBriefing = (merchant_id: string) =>
  apiGet<any>(`/ai/daily-briefing?merchant_id=${encodeURIComponent(merchant_id)}`);
