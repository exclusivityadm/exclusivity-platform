/**
 * Unified API client for Exclusivity Frontend
 * Automatically normalizes route paths and handles backend connection
 */
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") || "http://localhost:10000";

/**
 * Normalizes fetch paths (removes leading /api if present)
 */
function normalizePath(path: string): string {
  if (path.startsWith("/api/")) path = path.replace("/api/", "/");
  if (!path.startsWith("/")) path = "/" + path;
  return path;
}

export async function apiFetch<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const normalizedPath = normalizePath(path);
  const url = `${BACKEND_URL}${normalizedPath}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
    if (!res.ok) {
      console.error("API error:", res.status, await res.text());
      throw new Error(`API request failed: ${res.status}`);
    }
    const contentType = res.headers.get("content-type");
    if (contentType?.includes("application/json")) return res.json();
    return (await res.text()) as unknown as T;
  } catch (err) {
    console.error("Failed to fetch:", path, err);
    throw err;
  }
}

/**
 * Example calls:
 * await apiFetch("/voice/orion", { method: "POST", body: JSON.stringify({ text: "Hello" }) });
 * await apiFetch("/health");
 * await apiFetch("/supabase/status");
 */
