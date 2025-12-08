"use client";

import VoicePlayer from "@/components/voice/VoicePlayer";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/+$/, "") ||
  "https://exclusivity-backend.onrender.com";

export default function VoicePage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#020617",
        color: "#e5e7eb",
        padding: "40px",
        fontFamily: "Inter, system-ui, sans-serif",
      }}
    >
      <h1
        style={{
          fontSize: "1.9rem",
          fontWeight: 700,
          marginBottom: "8px",
        }}
      >
        🎙 AI Copilot Voice Console
      </h1>
      <p
        style={{
          marginBottom: 24,
          fontSize: 14,
          opacity: 0.8,
          maxWidth: 560,
        }}
      >
        Trigger Orion and Lyric through the live backend. This page uses the
        same backend URL as production, so anything that works here mirrors
        real-world behavior.
      </p>

      <VoicePlayer backendUrl={BACKEND_URL} />
    </main>
  );
}
