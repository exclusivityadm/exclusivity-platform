"use client";

import React, { useMemo, useState, useEffect } from "react";

type HeaderRow = { name: string; value: string | null };

export default function BackendPage() {
  const API_RAW = process.env.NEXT_PUBLIC_API_URL || "";
  const API = useMemo(() => API_RAW.replace(/\/+$/, ""), [API_RAW]);
  const orionUrl = API ? `${API}/ai/voice-test/orion.stream` : "";
  const lyricUrl = API ? `${API}/ai/voice-test/lyric.stream` : "";

  const [orion, setOrion] = useState<{status?: number; headers?: HeaderRow[]}>({});
  const [lyric, setLyric] = useState<{status?: number; headers?: HeaderRow[]}>({});
  const [err, setErr] = useState<string>("");

  async function check(url: string, setter: (v: any)=>void) {
    try {
      const res = await fetch(url, { method: "GET" });
      const rows: HeaderRow[] = [];
      ["content-type","access-control-allow-origin","accept-ranges","content-range","content-length","location"]
        .forEach(h => rows.push({ name: h, value: res.headers.get(h)}));
      setter({ status: res.status, headers: rows });
    } catch (e: any) {
      setter({ status: -1, headers: [{ name: "error", value: String(e?.message || e) }] });
    }
  }

  useEffect(() => {
    if (!API) setErr("NEXT_PUBLIC_API_URL not set for this deployment (Vercel).");
  }, [API]);

  return (
    <main className="min-h-dvh bg-white text-black">
      <div className="max-w-2xl mx-auto p-6 space-y-8">
        <h1 className="text-2xl font-semibold">Twins Voice Debug</h1>

        <section className="rounded border p-4 space-y-2">
          <div className="text-sm">
            <div>env <code>NEXT_PUBLIC_API_URL</code>: <code>{API_RAW || "(empty)"}</code></div>
            <div>Resolved API: <code>{API || "(empty)"}</code></div>
            <div>Orion URL: <a className="text-blue-600 underline" href={orionUrl} target="_blank">{orionUrl || "(empty)"}</a></div>
            <div>Lyric URL: <a className="text-blue-600 underline" href={lyricUrl} target="_blank">{lyricUrl || "(empty)"}</a></div>
          </div>
          {err && <p className="text-red-600 text-sm">{err}</p>}
          <div className="flex gap-3">
            <button className="px-3 py-2 rounded bg-black text-white" onClick={()=>check(orionUrl, setOrion)}>Check Orion headers</button>
            <button className="px-3 py-2 rounded bg-black text-white" onClick={()=>check(lyricUrl, setLyric)}>Check Lyric headers</button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <p className="font-medium mb-1">Orion HEAD</p>
              <p>Status: {orion.status ?? "-"}</p>
              <ul className="mt-1 space-y-0.5">
                {(orion.headers || []).map((h,i)=>(
                  <li key={i}><code>{h.name}</code>: <code>{h.value ?? ""}</code></li>
                ))}
              </ul>
            </div>
            <div>
              <p className="font-medium mb-1">Lyric HEAD</p>
              <p>Status: {lyric.status ?? "-"}</p>
              <ul className="mt-1 space-y-0.5">
                {(lyric.headers || []).map((h,i)=>(
                  <li key={i}><code>{h.name}</code>: <code>{h.value ?? ""}</code></li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        <section className="rounded border p-4 space-y-4">
          <div>
            <p className="mb-2 font-medium">Orion (should play audio/mpeg)</p>
            <audio controls src={orionUrl} />
          </div>
          <div>
            <p className="mb-2 font-medium">Lyric (should play audio/mpeg)</p>
            <audio controls src={lyricUrl} />
          </div>
        </section>
      </div>
    </main>
  );
}
