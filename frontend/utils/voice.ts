export async function speak(text: string, speaker: 'orion'|'lyric'): Promise<string> {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
  const res = await fetch(`${base}/ai/speak`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ speaker, text })
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || 'TTS failed');
  }
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
