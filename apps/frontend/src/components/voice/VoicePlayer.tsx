"use client";

import { useEffect, useState } from "react";

type Speaker = "orion" | "lyric";
type BackendStatus = "checking" | "online" | "offline";
type ModeUsed = "none" | "stream" | "url";

interface VoicePlayerProps {
  backendUrl: string;
}

const DEFAULT_ORION_TEXT = "Orion online and standing by.";
const DEFAULT_LYRIC_TEXT = "Lyric online and ready.";

export default function VoicePlayer({ backendUrl }: VoicePlayerProps) {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const [activeSpeaker, setActiveSpeaker] = useState<Speaker | null>(null);
  const [message, setMessage] = useState("");
  const [modeUsed, setModeUsed] = useState<ModeUsed>("none");

  // Health check
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${backendUrl.replace(/\/+$/, "")}/health`);
        setBackendStatus(res.ok ? "online" : "offline");
      } catch {
        setBackendStatus("offline");
      }
    };
    check();
  }, [backendUrl]);

  const speakerLabel = (speaker: Speaker) =>
    speaker === "orion" ? "Orion" : "Lyric";

  async function tryStreamingVoice(speaker: Speaker, text: string) {
    const url = `${backendUrl.replace(/\/+$/, "")}/voice/stream`;

    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ speaker, text }),
    });

    const contentType = res.headers.get("content-type") || "";

    // If the endpoint doesn't exist or isn't audio, let the caller fall back
    if (!res.ok || !contentType.includes("audio")) {
      throw new Error(`Streaming not available (status ${res.status})`);
    }

    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const audio = new Audio(objectUrl);
    await audio.play();
    setModeUsed("stream");
  }

  async function tryUrlVoice(speaker: Speaker, text: string) {
    const url = `${backendUrl.replace(/\/+$/, "")}/voice`;

    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ speaker, text }),
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Voice URL failed (${res.status}): ${errText}`);
    }

    const json = (await res.json()) as { audio_url?: string };
    if (!json.audio_url) {
      throw new Error("No audio_url found in response");
    }

    const audio = new Audio(json.audio_url);
    await audio.play();
    setModeUsed("url");
  }

  async function playVoice(speaker: Speaker) {
    const text =
      speaker === "orion" ? DEFAULT_ORION_TEXT : DEFAULT_LYRIC_TEXT;

    try {
      setActiveSpeaker(speaker);
      setMessage(`Calling ${speakerLabel(speaker)}…`);

      // 1) Try future streaming endpoint (safe even if it doesn't exist yet)
      try {
        await tryStreamingVoice(speaker, text);
        setMessage(`${speakerLabel(speaker)} speaking (streaming) 🔊`);
        return;
      } catch (err) {
        console.warn("Streaming unavailable, falling back to audio_url:", err);
      }

      // 2) Fallback to current /voice JSON → audio_url
      await tryUrlVoice(speaker, text);
      setMessage(`${speakerLabel(speaker)} speaking (audio URL) 🔊`);
    } catch (e: any) {
      console.error(e);
      setMessage(`❌ Voice failed: ${e.message || "Unknown error"}`);
    } finally {
      setActiveSpeaker(null);
    }
  }

  const statusDotColor =
    backendStatus === "online"
      ? "#22c55e"
      : backendStatus === "offline"
      ? "#ef4444"
      : "#fbbf24";

  const modeLabel =
    modeUsed === "stream"
      ? "Streaming"
      : modeUsed === "url"
      ? "Audio URL"
      : "Not used yet";

  return (
    <section
      style={{
        padding: 20,
        borderRadius: 16,
        background: "#020617",
        border: "1px solid #1e293b",
        maxWidth: 560,
      }}
    >
      {/* Backend + mode header */}
      <div
        style={{
          marginBottom: 16,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 10,
          fontSize: 14,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: statusDotColor,
            }}
          />
          <span>
            Backend:{" "}
            <strong>
              {backendStatus === "checking"
                ? "Checking…"
                : backendStatus === "online"
                ? "Online ✅"
                : "Offline ❌"}
            </strong>
          </span>
        </div>
        <div style={{ fontSize: 12, opacity: 0.7 }}>
          Mode: <strong>{modeLabel}</strong>
        </div>
      </div>

      {/* Buttons */}
      <div style={{ display: "flex", gap: 12, marginBottom: 14 }}>
        <button
          onClick={() => playVoice("orion")}
          disabled={backendStatus !== "online" || activeSpeaker !== null}
          style={{
            padding: "12px 18px",
            borderRadius: 999,
            border: "none",
            fontWeight: 600,
            cursor:
              backendStatus === "online" && !activeSpeaker
                ? "pointer"
                : "not-allowed",
            background:
              activeSpeaker === "orion"
                ? "#1d4ed8"
                : "linear-gradient(135deg, #2563eb, #38bdf8)",
            color: "white",
            opacity: backendStatus === "online" ? 1 : 0.5,
            minWidth: 130,
          }}
        >
          {activeSpeaker === "orion" ? "Orion speaking…" : "Play Orion"}
        </button>

        <button
          onClick={() => playVoice("lyric")}
          disabled={backendStatus !== "online" || activeSpeaker !== null}
          style={{
            padding: "12px 18px",
            borderRadius: 999,
            border: "none",
            fontWeight: 600,
            cursor:
              backendStatus === "online" && !activeSpeaker
                ? "pointer"
                : "not-allowed",
            background:
              activeSpeaker === "lyric"
                ? "#15803d"
                : "linear-gradient(135deg, #22c55e, #4ade80)",
            color: "white",
            opacity: backendStatus === "online" ? 1 : 0.5,
            minWidth: 130,
          }}
        >
          {activeSpeaker === "lyric" ? "Lyric speaking…" : "Play Lyric"}
        </button>
      </div>

      {/* Status / message */}
      {message && (
        <div
          style={{
            marginTop: 8,
            padding: 10,
            borderRadius: 10,
            background: "#020617",
            border: "1px solid #1e293b",
            fontSize: 14,
          }}
        >
          {message}
        </div>
      )}

      {/* Backend URL info */}
      <div
        style={{
          marginTop: 16,
          fontSize: 11,
          opacity: 0.6,
        }}
      >
        <div>
          Backend URL: <code>{backendUrl}</code>
        </div>
        <div>
          Tries <code>/voice/stream</code> first (if you add it later), then
          falls back to <code>/voice</code> with <code>audio_url</code>.
        </div>
      </div>
    </section>
  );
}
