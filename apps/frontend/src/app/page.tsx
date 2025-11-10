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
  // --- live queries ---
  const health = useFetch<Json>("/health", []);
  const systemSummary = useFetch<Json>("/analytics/system-summary", []);
  const chainStatus = useFetch<Json>("/analytics/chain-status", []);
  const dbTest = useFetch<Json>("/loyalty/test-db", []);

  // --- voice playback helpers ---
  const [voiceBusy, setVoiceBusy] = useState<null | "orion" | "lyric">(null);

  const callVoice = useCallback(async (speaker: "orion" | "lyric") => {
    try {
      const text =
        speaker === "orion"
          ? "Hello, this is Orion — your Exclusivity copilot online and ready."
          : "Hi there, Lyric here — Exclusivity systems confirmed and synchronized.";

      const res = await fetch(`${BACKEND_URL}/voice/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ speaker, text }),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`${res.status} ${res.statusText} — ${errText}`);
      }

      const data = await res.json();

      // ✅ updated to support base64 audio from backend
      if (data?.audio_base64) {
        const audio = new Audio(`data:audio/mpeg;base64,${data.audio_base64}`);
        audio.play().catch((e) => console.error("Playback failed:", e));
        console.log(`✅ Voice generated successfully (${speaker})`);
      } else {
        throw new Error("No audio data returned");
      }
    } catch (e: any) {
      console.error("Voice error:", e);
      alert(`Voice error: ${e?.message || e}`);
    }
  }, []);

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
        <div style={{ opacity: 0.75, marginLeft: "auto", fontSize: 12 }}>
          Backend: <code>{BACKEND_URL}</code>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(12, 1fr)",
          gap: 16,
        }}
      >
        {/* System Summary */}
        <div style={{ gridColumn: "span 6" }}>
          <Card title="System Summary">
            {systemSummary.loading && <div>Loading…</div>}
            {systemSummary.error && <div style={{ color: "#ef4444" }}>{systemSummary.error}</div>}
            {systemSummary.data && (
              <>
                <Row label="Version" value={systemSummary.data.system?.version} />
                <Row label="Environment" value={systemSummary.data.system?.environment} />
                <Row label="Debug Mode" value={systemSummary.data.system?.debug_mode} />
                <Row label="Supabase URL" value={systemSummary.data.system?.supabase_url} />
                <Row label="Base RPC URL" value={systemSummary.data.system?.base_rpc_url} />
                <Row
                  label="OpenAI Key Present"
                  value={String(systemSummary.data.system?.openai_key)}
                />
                <Row
                  label="ElevenLabs Key Present"
                  value={String(systemSummary.data.system?.elevenlabs_key)}
                />
                <Row
                  label="Shopify Connected"
                  value={String(systemSummary.data.system?.shopify_connected)}
                />
                <Row label="Render Service" value={systemSummary.data.system?.render_service} />
                <Row label="Vercel Project" value={systemSummary.data.system?.vercel_project} />
              </>
            )}
          </Card>
        </div>

        {/* Chain Status */}
        <div style={{ gridColumn: "span 6" }}>
          <Card title="Blockchain (Base) Status">
            {chainStatus.loading && <div>Loading…</div>}
            {chainStatus.error && <div style={{ color: "#ef4444" }}>{chainStatus.error}</div>}
            {chainStatus.data && (
              <>
                <Row label="Connected" value={String(chainStatus.data.connected)} />
                <Row label="Chain ID (hex)" value={chainStatus.data.chain_id_hex} />
                <Row label="Chain ID (dec)" value={chainStatus.data.chain_id_decimal} />
                <Row label="Minting Enabled" value={chainStatus.data.minting_enabled} />
                <Row label="Aesthetics Enabled" value={chainStatus.data.aesthetics_enabled} />
                <Row
                  label="Brand Wallet"
                  value={chainStatus.data.wallets?.brand_wallet || "(unset)"}
                />
                <Row
                  label="Developer Wallet"
                  value={chainStatus.data.wallets?.developer_wallet || "(unset)"}
                />
                <Row label="Coinbase Network" value={chainStatus.data.coinbase_network} />
                <Row label="Domain Allowlist" value={chainStatus.data.domain_allowlist} />
              </>
            )}
          </Card>
        </div>

        {/* Database Check */}
        <div style={{ gridColumn: "span 6" }}>
          <Card title="Database Check (Supabase)">
            {dbTest.loading && <div>Loading…</div>}
            {dbTest.error && <div style={{ color: "#ef4444" }}>{dbTest.error}</div>}
            {dbTest.data && (
              <>
                <Row label="Connected" value={String(dbTest.data.connected)} />
                {"records" in (dbTest.data || {}) && (
                  <Row label="Sample Records" value={dbTest.data.records} />
                )}
                {"database_url" in (dbTest.data || {}) && (
                  <Row
                    label="DB URL"
                    value={dbTest.data.database_url || "(hidden)"}
                  />
                )}
              </>
            )}
          </Card>
        </div>

        {/* Voice Tests */}
        <div style={{ gridColumn: "span 6" }}>
          <Card
            title="AI Copilots — Voice Test"
            footer={
              <div style={{ fontSize: 12, color: "#9aa1af" }}>
                Clicking a button will send text to ElevenLabs through your backend and play the returned audio.
              </div>
            }
          >
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
        </div>
      </div>
    </main>
  );
}
