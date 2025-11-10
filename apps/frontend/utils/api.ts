// apps/frontend/util/api.ts

/**
 * Unified API client for Exclusivity frontend.
 * Matches the current backend: single POST /voice that accepts { speaker, text }.
 */

export async function generateVoice(
  speaker: "Orion" | "Lyric",
  text: string
): Promise<string | null> {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    if (!backendUrl) {
      console.error("❌ Missing NEXT_PUBLIC_BACKEND_URL");
      return null;
    }

    const res = await fetch(`${backendUrl}/voice`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // IMPORTANT: if your backend checks origin/cookies, include credentials here
      body: JSON.stringify({ speaker, text }),
      // next.js edge/runtime-safe option to avoid caching voice calls
      cache: "no-store",
    });

    if (!res.ok) {
      const errText = await res.text().catch(() => "");
      console.error(`❌ /voice failed: ${res.status} ${res.statusText} — ${errText}`);
      return null;
    }

    const data = (await res.json()) as { audio_url?: string };
    if (!data?.audio_url) {
      console.error("⚠️ Backend responded without audio_url");
      return null;
    }

    console.log(`✅ Voice generated for ${speaker}: ${data.audio_url}`);
    return data.audio_url;
  } catch (err) {
    console.error("❌ Failed to fetch /voice:", err);
    return null;
  }
}
