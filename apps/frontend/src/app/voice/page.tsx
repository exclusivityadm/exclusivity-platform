"use client";

import { useState } from "react";

const BACKEND =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "https://exclusivity-backend.onrender.com";

export default function VoicePage() {
  const [active, setActive] = useState<null | "orion" | "lyric">(null);
  const [status, setStatus] = useState("");

  async function speak(speaker: "orion" | "lyric") {
    try {
      setActive(speaker);
      setStatus(`Contacting ${speaker}...`);

      const res = await fetch(`${BACKEND}/voice/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ speaker })
      });

      if (!res.ok) throw new Error("Voice request failed.");

      const reader = res.body?.getReader();
      if (!reader) throw new Error("Stream unavailable");

      const chunks: Uint8Array[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
      }

      const audio = new Audio(URL.createObjectURL(new Blob(chunks, { type: "audio/mpeg" })));
      await audio.play();

      setStatus(`${speaker} responded ✓`);
    } catch (e: any) {
      setStatus("❌ Voice playback failed");
    } finally {
      setActive(null);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#0d0f14",
        color: "#f3f4f6",
        padding: "40px",
        fontFamily: "Inter, sans-serif"
      }}
    >
      <h1 style={{ fontSize: 32, fontWeight: 700, marginBottom: 20 }}>
        🎙️ Orion & Lyric — Voice Copilot Test
      </h1>

      <div style={{ display: "flex", gap: 20, marginBottom: 30 }}>
        <button
          disabled={active !== null}
          onClick={() => speak("orion")}
          style={{
            padding: "14px 22px",
            borderRadius: 10,
            border: "1px solid #1d4ed8",
            background: active === "orion" ? "#374151" : "#2563eb",
            color: "#fff",
            fontWeight: 600,
            cursor: "pointer"
          }}
        >
          {active === "orion" ? "Streaming…" : "Play Orion"}
        </button>

        <button
          disabled={active !== null}
          onClick={() => speak("lyric")}
          style={{
            padding: "14px 22px",
            borderRadius: 10,
            border: "1px solid #059669",
            background: active === "lyric" ? "#374151" : "#10b981",
            color: "#fff",
            fontWeight: 600,
            cursor: "pointer"
          }}
        >
          {active === "lyric" ? "Streaming…" : "Play Lyric"}
        </button>
      </div>

      {status && (
        <div
          style={{
            background: "#1e293b",
            padding: 15,
            borderRadius: 8,
            width: "fit-content",
            border: "1px solid #334155"
          }}
        >
          {status}
        </div>
      )}

      <footer style={{ marginTop: 50, opacity: 0.6, fontSize: 12 }}>
        <p>Backend: <code>{BACKEND}</code></p>
        <p>Voice is generated dynamically via GPT → ElevenLabs → Stream</p>
      </footer>
    </main>
  );
}
