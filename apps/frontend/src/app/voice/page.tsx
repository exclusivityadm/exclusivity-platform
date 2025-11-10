"use client";

import { useState, useEffect } from "react";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/+$/, "") ||
  "https://exclusivity-backend.onrender.com";

export default function VoicePage() {
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [voiceBusy, setVoiceBusy] = useState<null | "orion" | "lyric">(null);
  const [message, setMessage] = useState<string>("");

  // Ping backend /health route
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/health`);
        if (res.ok) {
          setBackendStatus("online");
        } else {
          setBackendStatus("offline");
        }
      } catch {
        setBackendStatus("offline");
      }
    };
    check();
  }, []);

  // Unified voice handler
  async function playVoice(speaker: "orion" | "lyric") {
    try {
      setVoiceBusy(speaker);
      setMessage(`Synthesizing ${speaker}...`);

      const res = await fetch(`${BACKEND_URL}/voice`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          speaker,
          text: speaker === "orion" ? "Orion online and standing by." : "Lyric online and ready.",
        }),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Error ${res.status}: ${errText}`);
      }

      const json = (await res.json()) as { audio_url?: string };
      if (!json.audio_url) throw new Error("No audio URL returned by backend");

      const audio = new Audio(json.audio_url);
      await audio.play();

      setMessage(`${speaker} voice played successfully ✅`);
    } catch (e: any) {
      console.error(e);
      setMessage(`❌ ${e.message || "Voice request failed"}`);
    } finally {
      setVoiceBusy(null);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#0d0f14",
        color: "#f3f4f6",
        padding: "40px",
        fontFamily: "Inter, sans-serif",
      }}
    >
      <h1 style={{ fontSize: "1.8rem", fontWeight: 700, marginBottom: "20px" }}>
        🎙️ AI Copilot Voice Tester
      </h1>

      <div
        style={{
          marginBottom: 20,
          padding: 16,
          borderRadius: 12,
          background: "#111318",
          border: "1px solid #1f2430",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <span
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background:
              backendStatus === "online"
                ? "#22c55e"
                : backendStatus === "offline"
                ? "#ef4444"
                : "#f59e0b",
          }}
        ></span>
        <span>
          Backend status:{" "}
          <b>
            {backendStatus === "checking"
              ? "Checking..."
              : backendStatus === "online"
              ? "Online ✅"
              : "Offline ❌"}
          </b>
        </span>
      </div>

      <div style={{ display: "flex", gap: 20 }}>
        <button
          disabled={voiceBusy !== null}
          onClick={() => playVoice("orion")}
          style={{
            padding: "12px 18px",
            borderRadius: 10,
            border: "1px solid #1d4ed8",
            background: voiceBusy === "orion" ? "#374151" : "#2563eb",
            color: "white",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {voiceBusy === "orion" ? "Synthesizing…" : "Play Orion"}
        </button>

        <button
          disabled={voiceBusy !== null}
          onClick={() => playVoice("lyric")}
          style={{
            padding: "12px 18px",
            borderRadius: 10,
            border: "1px solid #059669",
            background: voiceBusy === "lyric" ? "#374151" : "#10b981",
            color: "white",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {voiceBusy === "lyric" ? "Synthesizing…" : "Play Lyric"}
        </button>
      </div>

      {message && (
        <div
          style={{
            marginTop: 20,
            padding: "10px 14px",
            borderRadius: 8,
            background: "#1a1f2a",
            border: "1px solid #2a2f3e",
            fontSize: 14,
          }}
        >
          {message}
        </div>
      )}

      <footer
        style={{
          marginTop: 40,
          fontSize: 12,
          opacity: 0.7,
          borderTop: "1px solid #1e2430",
          paddingTop: 20,
        }}
      >
        <p>
          Connected backend: <code>{BACKEND_URL}</code>
        </p>
        <p>
          Uses the live <code>/voice</code> POST endpoint (ElevenLabs integration) for Orion and
          Lyric.
        </p>
      </footer>
    </main>
  );
}
