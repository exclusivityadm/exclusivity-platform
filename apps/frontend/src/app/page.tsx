"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Json = Record<string, any>;

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/+$/, "") ||
  "http://127.0.0.1:8000";

type FetchState<T> = {
  loading: boolean;
  error: string | null;
  data: T | null;
};

function useFetch<T = any>(path: string | null, deps: any[] = []) {
  const [state, setState] = useState<FetchState<T>>({
    loading: !!path,
    error: null,
    data: null,
  });

  const url = useMemo(() => (path ? `${BACKEND_URL}${path}` : null), [path]);

  useEffect(() => {
    let cancelled = false;
    if (!url) return;

    setState({ loading: true, error: null, data: null });
    fetch(url, { cache: "no-store" })
      .then(async (r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        return r.json() as Promise<T>;
      })
      .then((data) => {
        if (!cancelled) setState({ loading: false, error: null, data });
      })
      .catch((err: any) => {
        if (!cancelled) setState({ loading: false, error: String(err), data: null });
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps.concat(url));

  return state;
}

function Card(props: { title: string; children?: React.ReactNode; footer?: React.ReactNode }) {
  return (
    <div
      style={{
        background: "#111318",
        border: "1px solid #1f2430",
        borderRadius: 16,
        padding: 16,
        width: "100%",
      }}
    >
      <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>{props.title}</div>
      <div style={{ fontSize: 14, lineHeight: 1.6 }}>{props.children}</div>
      {props.footer ? <div style={{ marginTop: 12, opacity: 0.9 }}>{props.footer}</div> : null}
    </div>
  );
}

function Row(props: { label: string; value: any }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "220px 1fr",
        gap: 12,
        padding: "6px 0",
        borderBottom: "1px dashed #222634",
      }}
    >
      <div style={{ color: "#9aa1af" }}>{props.label}</div>
      <div style={{ wordBreak: "break-word" }}>{String(props.value)}</div>
    </div>
  );
}

export default function Page() {
  const health = useFetch<Json>("/health", []);
  const [voiceBusy, setVoiceBusy] = useState<null | "orion" | "lyric">(null);
  const [streamMode, setStreamMode] = useState<boolean>(false);

  const callVoice = useCallback(
    async (speaker: "orion" | "lyric") => {
      try {
        const endpoint = streamMode ? "/voice/stream" : "/voice";
        const text =
          speaker === "orion"
            ? "Orion online — Exclusivity systems synchronized."
            : "Lyric ready — voice link confirmed.";

        const res = await fetch(`${BACKEND_URL}${endpoint}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ speaker, text }),
        });

        if (!res.ok) {
          const errText = await res.text();
          throw new Error(`${res.status} ${res.statusText} — ${errText}`);
        }

        if (streamMode) {
          // Streaming response: play chunks progressively
          const audioContext = new AudioContext();
          const reader = res.body?.getReader();
          if (!reader) throw new Error("No readable stream returned");

          let buffer = new Uint8Array();
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            if (value) buffer = new Uint8Array([...buffer, ...value]);
          }

          const blob = new Blob([buffer], { type: "audio/mpeg" });
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audio.play();
        } else {
          // Base64 static voice
          const data = await res.json();
          if (data?.audio_base64) {
            const audio = new Audio(`data:audio/mpeg;base64,${data.audio_base64}`);
            await audio.play();
          } else {
            throw new Error("No audio data returned");
          }
        }
      } catch (e: any) {
        console.error("Voice error:", e);
        alert(`Voice error: ${e?.message || e}`);
      }
    },
    [streamMode]
  );

  const handleVoice = async (who: "orion" | "lyric") => {
    setVoiceBusy(who);
    await callVoice(who);
    setVoiceBusy(null);
  };

  return (
    <main style={{ padding: 24 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 18 }}>
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: 999,
            background: health.data ? "#22c55e" : "#ef4444",
            boxShadow: "0 0 10px rgba(34,197,94,0.6)",
          }}
        />
        <div style={{ fontSize: 20, fontWeight: 700 }}>Exclusivity — Merchant Console</div>
        <div style={{ marginLeft: "auto", fontSize: 13, opacity: 0.8 }}>
          Backend: <code>{BACKEND_URL}</code>
        </div>
      </div>

      <Card
        title="AI Copilots — Voice System"
        footer={
          <div style={{ fontSize: 12, color: "#9aa1af" }}>
            Toggle between instant playback and real-time streaming.
          </div>
        }
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
          <label style={{ color: "#cbd5e1", fontSize: 14 }}>
            <input
              type="checkbox"
              checked={streamMode}
              onChange={() => setStreamMode(!streamMode)}
              style={{ marginRight: 8 }}
            />
            Enable Streaming Mode
          </label>
        </div>

        <div style={{ display: "flex", gap: 12 }}>
          <button
            onClick={() => handleVoice("orion")}
            disabled={voiceBusy !== null}
            style={{
              padding: "10px 14px",
              background: voiceBusy === "orion" ? "#374151" : "#2563eb",
              border: "1px solid #1d4ed8",
              borderRadius: 10,
              color: "white",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {voiceBusy === "orion" ? "Synthesizing…" : "Play Orion"}
          </button>

          <button
            onClick={() => handleVoice("lyric")}
            disabled={voiceBusy !== null}
            style={{
              padding: "10px 14px",
              background: voiceBusy === "lyric" ? "#374151" : "#10b981",
              border: "1px solid #059669",
              borderRadius: 10,
              color: "white",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {voiceBusy === "lyric" ? "Synthesizing…" : "Play Lyric"}
          </button>
        </div>
      </Card>
    </main>
  );
}
