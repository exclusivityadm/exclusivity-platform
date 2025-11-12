/**
 * Exclusivity Unified API Client
 * Handles all frontend → backend calls, including voice synthesis.
 */

export async function generateVoice(
  speaker: "orion" | "lyric",
  text: string
): Promise<string | null> {
  try {
    const backendUrl =
      process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/+$/, "") ||
      "http://127.0.0.1:8000";

    const res = await fetch(`${backendUrl}/voice`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ speaker, text }),
    });

    if (!res.ok) {
      const errText = await res.text().catch(() => "");
      console.error(`❌ /voice failed: ${res.status} ${res.statusText} — ${errText}`);
      return null;
    }

    const data = await res.json();
    if (data?.audio_base64) {
      console.log(`✅ Voice generated successfully for ${speaker}`);
      return `data:audio/mpeg;base64,${data.audio_base64}`;
    }

    console.warn("⚠️ No audio data returned from backend");
    return null;
  } catch (err) {
    console.error("❌ Voice fetch failed:", err);
    return null;
  }
}

/**
 * Utility helper to play an audio string.
 */
export function playAudio(audioSrc: string) {
  try {
    const audio = new Audio(audioSrc);
    audio.play().catch((e) => {
      console.error("⚠️ Playback failed:", e);
    });
  } catch (err) {
    console.error("❌ Audio playback error:", err);
  }
}
