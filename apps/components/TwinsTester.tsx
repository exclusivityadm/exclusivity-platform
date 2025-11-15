"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") || "";

async function playVoice(path: string) {
  if (!API) throw new Error("NEXT_PUBLIC_API_URL is not set");
  const res = await fetch(`${API}${path}`, { method: "GET", credentials: "include" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json(); // { audio_base64, length_bytes, speaker }
  const b64 = String(data.audio_base64 || "").replace(/^data:audio\/\w+;base64,?/, "");
  if (!b64) throw new Error("No audio returned");

  // Base64 -> Uint8Array -> Blob -> ObjectURL -> Audio
  const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const blob = new Blob([bytes], { type: "audio/mpeg" });
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  audio.play().catch(() => {
    // Safari/iOS sometimes needs user gesture; button click counts as one.
  });
}

export default function TwinsTester() {
  const [status, setStatus] = useState<string>("");

  const testOrion = async () => {
    try {
      setStatus("Loading Orion…");
      await playVoice("/ai/voice-test/orion");
      setStatus("Orion playing ✅");
    } catch (e: any) {
      setStatus(`Orion error: ${e?.message || e}`);
    }
  };

  const testLyric = async () => {
    try {
      setStatus("Loading Lyric…");
      await playVoice("/ai/voice-test/lyric");
      setStatus("Lyric playing ✅");
    } catch (e: any) {
      setStatus(`Lyric error: ${e?.message || e}`);
    }
  };

  return (
    <div className="flex flex-col items-start gap-3 p-4 border rounded-lg">
      <h2 className="text-xl font-semibold">Twins Voice Test</h2>
      <button
        onClick={testOrion}
        className="px-4 py-2 rounded-lg bg-black text-white hover:opacity-90"
      >
        ▶ Orion
      </button>
      <button
        onClick={testLyric}
        className="px-4 py-2 rounded-lg bg-gray-900 text-white hover:opacity-90"
      >
        ▶ Lyric
      </button>
      <p className="text-sm text-gray-600">{status}</p>
    </div>
  );
}
