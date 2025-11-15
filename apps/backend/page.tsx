"use client";

import React, { useMemo, useRef } from "react";

export default function BackendPage() {
  const API = useMemo(
    () => (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, ""),
    []
  );

  const orionStream = API ? `${API}/ai/voice-test/orion.stream` : "";
  const lyricStream = API ? `${API}/ai/voice-test/lyric.stream` : "";
  const orionPost = API ? `${API}/voice/` : "";
  const lyricPost = API ? `${API}/voice/` : "";

  const orionEl = useRef<HTMLAudioElement>(null);
  const lyricEl = useRef<HTMLAudioElement>(null);

  async function playViaPost(speaker: "orion" | "lyric", text: string) {
    try {
      const url = speaker === "orion" ? orionPost : lyricPost;
      const res = await fetch(url, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ speaker, text }),
      });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(`POST ${speaker} failed: ${res.status} ${msg}`);
      }
      const data = await res.json();
      const b64 = data.audio_base64 as string;
      if (!b64) throw new Error("No audio_base64 in response");
      const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
      const blob = new Blob([bytes], { type: "audio/mpeg" });
      const objUrl = URL.createObjectURL(blob);
      const el = speaker === "orion" ? orionEl.current : lyricEl.current;
      if (el) {
        el.src = objUrl;
        await el.play();
      } else {
        const a = new Audio(objUrl);
        await a.play();
      }
    } catch (e: any) {
      alert(`Voice error: ${e?.message || String(e)}`);
    }
  }

  return (
    <main className="min-h-dvh bg-white text-black">
      <div className="max-w-xl mx-auto p-6 space-y-8">
        <h1 className="text-2xl font-semibold">Twins Voice Test</h1>

        <div className="rounded border p-4 text-sm space-y-1">
          <div><span className="font-mono">NEXT_PUBLIC_API_URL</span>: <span className="font-mono">{process.env.NEXT_PUBLIC_API_URL || "(empty)"}</span></div>
          <div>Orion stream: <a className="text-blue-600 underline" href={orionStream} target="_blank">{orionStream || "(empty)"}</a></div>
          <div>Lyric stream: <a className="text-blue-600 underline" href={lyricStream} target="_blank">{lyricStream || "(empty)"}</a></div>
        </div>

        {/* Streaming players (best) */}
        <section className="space-y-4">
          <div>
            <p className="mb-2 font-medium">Orion (stream)</p>
            <audio ref={orionEl} controls src={orionStream} />
          </div>
          <div>
            <p className="mb-2 font-medium">Lyric (stream)</p>
            <audio ref={lyricEl} controls src={lyricStream} />
          </div>
        </section>

        {/* JSON → base64 → audio fallback demo */}
        <section className="rounded border p-4 space-y-3">
          <p className="font-medium">Or use JSON POST (base64 → audio)</p>
          <div className="flex gap-2">
            <button
              className="px-3 py-2 rounded bg-black text-white"
              onClick={() => playViaPost("orion", "Hello from Orion via POST.")}
            >
              Orion via POST
            </button>
            <button
              className="px-3 py-2 rounded bg-black text-white"
              onClick={() => playViaPost("lyric", "Hello from Lyric via POST.")}
            >
              Lyric via POST
            </button>
          </div>
          <p className="text-xs text-gray-600">
            The POST endpoint is <code>/voice/</code> and returns <code>audio_base64</code>. The streaming endpoints are recommended for production.
          </p>
        </section>
      </div>
    </main>
  );
}
