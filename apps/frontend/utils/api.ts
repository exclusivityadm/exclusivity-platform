// apps/frontend/utils/api.ts

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "https://exclusivity-backend.onrender.com";

/**
 * Helper to normalize request paths (avoiding double slashes)
 */
function normalizePath(path: string): string {
  if (!path.startsWith("/")) path = "/" + path;
  return BACKEND_URL + path;
}

/**
 * Generic API fetcher with automatic error handling
 */
export async function apiFetch(path: string, options: RequestInit = {}) {
  const url = normalizePath(path);

  try {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
      },
      ...options,
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`❌ API ${url} failed: ${response.status} ${errorText}`);
      return { error: `Error ${response.status}` };
    }

    return await response.json();
  } catch (err) {
    console.error(`🚨 Fetch error at ${url}:`, err);
    return { error: "Network error" };
  }
}

/**
 * Health checks
 */
export const checkSystem = async () => apiFetch("/health");
export const checkSupabase = async () => apiFetch("/supabase");
export const checkBlockchain = async () => apiFetch("/blockchain");

/**
 * Voice endpoints — Orion and Lyric
 */
export async function playVoice(type: "orion" | "lyric", text: string) {
  const endpoint = `/voice/${type}`;
  const res = await apiFetch(endpoint, {
    method: "POST",
    body: JSON.stringify({ text }),
  });

  if (res?.audio) {
    const audio = new Audio(`data:audio/mp3;base64,${res.audio}`);
    audio.play();
  } else {
    console.error("⚠️ Voice API returned no audio:", res);
  }
}
