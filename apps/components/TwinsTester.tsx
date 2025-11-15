"use client";

export default function TwinsPlay() {
  const API = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");
  const orionUrl = `${API}/ai/voice-test/orion.stream`;
  const lyricUrl = `${API}/ai/voice-test/lyric.stream`;

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-xl font-semibold">Twins Voice Test</h2>

      <div>
        <p className="mb-2 font-medium">Orion</p>
        <audio controls src={orionUrl} />
      </div>

      <div>
        <p className="mb-2 font-medium">Lyric</p>
        <audio controls src={lyricUrl} />
      </div>
    </div>
  );
}
