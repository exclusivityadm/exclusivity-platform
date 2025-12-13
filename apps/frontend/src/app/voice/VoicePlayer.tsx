"use client";

import React, { useState, useEffect, useRef } from "react";

interface VoicePlayerProps {
  voiceName: string;
  fetchUrl: string;
}

export default function VoicePlayer({ voiceName, fetchUrl }: VoicePlayerProps) {
  const [loading, setLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  async function generateVoice() {
    try {
      setLoading(true);
      setAudioUrl(null);

      const res = await fetch(fetchUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: `Testing ${voiceName} voice synthesis.` }),
      });

      if (!res.ok) throw new Error("Failed to fetch audio.");

      const data = await res.json();

      if (!data.audio_base64) throw new Error("No audio returned from API.");

      const url = `data:audio/mp3;base64,${data.audio_base64}`;
      setAudioUrl(url);
    } catch (e) {
      console.error("Voice generation error:", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (audioUrl && audioRef.current) {
      audioRef.current.load();
      audioRef.current.play().catch(() => {});
    }
  }, [audioUrl]);

  return (
    <div
      style={{
        background: "#111318",
        padding: "16px",
        borderRadius: "16px",
        border: "1px solid #1f2430",
        marginTop: "12px",
      }}
    >
      <div style={{ fontSize: "18px", fontWeight: 600, marginBottom: "12px" }}>
        {voiceName} Voice Generator
      </div>

      <button
        onClick={generateVoice}
        disabled={loading}
        style={{
          padding: "10px 14px",
          borderRadius: "10px",
          background: loading ? "#4b5563" : "#2563eb",
          border: "1px solid #1d4ed8",
          color: "white",
          fontWeight: 600,
          cursor: loading ? "not-allowed" : "pointer",
        }}
      >
        {loading ? "Generating..." : `Play ${voiceName}`}
      </button>

      <div style={{ marginTop: "14px", opacity: 0.85, fontSize: "14px" }}>
        {audioUrl ? "Playing audio..." : "Click to generate dynamic speech."}
      </div>

      <audio ref={audioRef} controls style={{ marginTop: "18px", width: "100%" }}>
        <source src={audioUrl ?? ""} type="audio/mp3" />
      </audio>

      {/* ------------------------------------------------------------------ */}
      {/* FIXED SECTION — SAFE FOR TURBOPACK (NO RAW {{ }} OR SYMBOL PARSE)   */}
      {/* ------------------------------------------------------------------ */}

      <div style={{ marginTop: "18px", fontSize: "13px", opacity: 0.75, lineHeight: 1.5 }}>
        <strong>Flow:</strong>{" "}
        <code>
          POST /voice → &#123;&#123; &quot;text&quot;, &quot;audio_base64&quot; &#125;&#125;
        </code>{" "}
        → decoded in-browser → played automatically.
      </div>
    </div>
  );
}
