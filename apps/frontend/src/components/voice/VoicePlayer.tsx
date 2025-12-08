"use client";

import { useEffect, useState } from "react";

type Speaker = "orion" | "lyric";
type BackendStatus = "checking" | "online" | "offline";

interface VoicePlayerProps {
  backendUrl: string;
}

export default function VoicePlayer({ backendUrl }: VoicePlayerProps) {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const [activeSpeaker, setActiveSpeaker] = useState<Speaker | null>(null);
  const [lastText, setLastText] = useState<string>("");
  const [message, setMessage] = useState<string>("");

  const baseUrl = backendUrl.replace(/\/+$/, "");

  // Health check
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${baseUrl}/health`);
        setBackendStatus(res.ok ? "online" : "offline");
      } catch {
        setBackendStatus("offline");
      }
    };
    check();
  }, [baseUrl]);

  async function playVoice(speaker: Speaker) {
    if (backendStatus !== "online") return;

    try {
      setActiveSpeaker(speaker);
      setMessage(`Contacting ${speaker === "orion" ? "Orion" : "Lyric"}…`);

      const res = await fetch(`${baseUrl}/voice`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ speaker }),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`HTTP ${res.status}: ${errText}`);
      }

      const json = (await res.json()) as {
        speaker: string;
        text?: string;
        audio_base64: string;
      };

      const spokenText =
        json.text ||
        (speaker === "orion"
          ? "Orion online, Exclusivity system synchronized."
          : "Lyric ready and voice link confirmed.");

      setLastText(spokenText);

      // Decode base64 -> Blob -> Audio
      const byteString = atob(json.audio_base64);
      const len = byteString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = byteString.charCodeAt(i);
      }

      const blob = new Blob([bytes], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);

      await audio.play();
      setMessage(
        `${speaker === "orion" ? "Orion" : "Lyric"} just spoke (AI generated).`
      );
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

  return (
    <section
      style={{
        padding: 20,
        borderRadius: 16,
        background: "#020617",
        border: "1px solid #1e293b",
        maxWidth: 600,
      }}
    >
      {/* Header: backend status */}
      <div
        style={{
          marginBottom: 16,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
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
        <div style={{ fontSize: 11, opacity: 0.7 }}>
          Endpoint: <code>/voice</code> (JSON + base64)
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
            color: "#ffffff",
            opacity: backendStatus === "online" ? 1 : 0.6,
            minWidth: 140,
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
            color: "#ffffff",
            opacity: backendStatus === "online" ? 1 : 0.6,
            minWidth: 140,
          }}
        >
          {activeSpeaker === "lyric" ? "Lyric speaking…" : "Play Lyric"}
        </button>
      </div>

      {/* Last generated text */}
      {lastText && (
        <div
          style={{
            marginTop: 4,
            padding: 10,
            borderRadius: 10,
            background: "#020617",
            border: "1px solid #1e293b",
            fontSize: 14,
            whiteSpace: "pre-wrap",
          }}
        >
          <strong>Last line:</strong> {lastText}
        </div>
      )}

      {/* Status message */}
      {message && (
        <div
          style={{
            marginTop: 8,
            padding: 8,
            borderRadius: 8,
            background: "#020617",
            border: "1px solid #1e293b",
            fontSize: 13,
            opacity: 0.9,
          }}
        >
          {message}
        </div>
      )}

      <div
        style={{
          marginTop: 16,
          fontSize: 11,
          opacity: 0.6,
        }}
      >
        <div>
          Backend URL: <code>{baseUrl}</code>
        </div>
        <div>
          Flow: <code>POST /voice → {{ "text", "audio_base64" }}</code> → decode
          in browser → play.
        </div>
      </div>
    </section>
  );
}
