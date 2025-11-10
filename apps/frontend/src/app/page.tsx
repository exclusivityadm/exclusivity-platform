"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Json = Record<string, any>;

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/+$/, "") || "http://127.0.0.1:8000";

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
  }, deps.concat(url));

  return state;
}

export default function Page() {
  // update all fetch paths to match backend routes
  const health = useFetch<Json>("/health", []);
  const systemSummary = useFetch<Json>("/blockchain/status", []);
  const chainStatus = useFetch<Json>("/blockchain/status", []);
  const dbTest = useFetch<Json>("/supabase/test", []);

  // voice test — now posts directly to /voice
  const callVoice = useCallback(async (speaker: "orion" | "lyric") => {
    const res = await fetch(`${BACKEND_URL}/voice`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        speaker,
        text: speaker === "orion" ? "Orion online." : "Lyric online.",
      }),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${res.status} ${res.statusText} — ${text}`);
    }

    const json = (await res.json()) as { audio_url?: string };
    if (!json.audio_url) throw new Error("No audio URL returned");

    const audio = new Audio(json.audio_url);
    await audio.play();
  }, []);

  // ... keep the rest of your UI identical
}
