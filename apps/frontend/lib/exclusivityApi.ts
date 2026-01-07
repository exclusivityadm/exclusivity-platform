/**
 * Exclusivity API client (frontend)
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

export async function apiGet<T>(path: string): Promise<ApiResult<T>> {
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

export async function apiPost<T>(path: string, body: any): Promise<ApiResult<T>> {
  try {
    const res = await fetch(mustBackend() + path, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body ?? {}),
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

/* ---- Canonical endpoints used by onboarding ---- */

export const getInitQuestions = () =>
  apiGet<{ questions: string[] }>("/ai/init-questions");

export const saveInitAnswers = (merchant_id: string, answers: Record<string, string>) =>
  apiPost("/ai/init-answers", { merchant_id, answers });

export const getMerchantProfileByShop = (shop_domain: string) =>
  apiGet(`/merchant/profile?shop_domain=${encodeURIComponent(shop_domain)}`);

export const getBrandStatusByShop = (shop_domain: string) =>
  apiGet(`/brand/status?shop_domain=${encodeURIComponent(shop_domain)}`);

export const getDebugRoutes = () => apiGet("/debug/routes");
