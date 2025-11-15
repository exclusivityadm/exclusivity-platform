"use client";

import React, { useMemo } from "react";

export default function BackendPage() {
  const API = useMemo(
    () => (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, ""),
    []
  );
  const orionUrl = API ? `${API}/ai/voice-test/orion.stream` : "";
  const lyricUrl = API ? `${API}/ai/voice-test/lyric.stream` : "";

  return (
    <main className="min-h-dvh bg-white text-black">
      <div className="max-w-xl mx-auto p-6 space-y-6">
        <h1 className="text-2xl font-semibold">Twins Voice Test</h1>

        <div className="rounded border p-4 text-sm">
          <div className="mb-1">
            <span className="font-mono">NEXT_PUBLIC_API_URL</span>:{" "}
            <span className="font-mono">
              {process.env.NEXT_PUBLIC_API_URL || "(empty)"}
            </span>
          </div>
          <div>
            Orion URL:{" "}
            <a className="text-blue-600 underline" href={orionUrl} target="_blank">
              {orionUrl || "(empty)"}
            </a>
          </div>
          <div>
            Lyric URL:{" "}
            <a className="text-blue-600 underline" href={lyricUrl} target="_blank">
              {lyricUrl || "(empty)"}
            </a>
          </div>
        </div>

        <section>
          <p className="mb-2 font-medium">Orion</p>
          <audio controls src={orionUrl} />
        </section>

        <section>
          <p className="mb-2 font-medium">Lyric</p>
          <audio controls src={lyricUrl} />
        </section>
      </div>
    </main>
  );
}
