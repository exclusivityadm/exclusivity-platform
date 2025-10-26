'use client';
import { useState } from 'react';

export default function Home() {
  const [text, setText] = useState('Hello from the Exclusivity twins!');
  const [speaker, setSpeaker] = useState<'orion' | 'lyric'>('orion');
  const [loading, setLoading] = useState(false);

  const playAudio = async () => {
    setLoading(true);
    try {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL || '';
      const res = await fetch(`${base}/voice/speak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, speaker, format: 'mp3' })
      });
      if (!res.ok) throw new Error('TTS request failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play();
    } catch (e:any) {
      alert('Error: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main style={{display:'flex',flexDirection:'column',gap:12, padding:24, maxWidth:720}}>
      <h1>Exclusivity — Voice Test</h1>
      <label>
        Text:
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          rows={4}
          style={{width:'100%'}}
        />
      </label>

      <label>
        Speaker:&nbsp;
        <select value={speaker} onChange={e => setSpeaker(e.target.value as any)}>
          <option value="orion">Orion (male)</option>
          <option value="lyric">Lyric (female)</option>
        </select>
      </label>

      <button onClick={playAudio} disabled={loading}>
        {loading ? 'Generating…' : 'Speak'}
      </button>

      <p style={{opacity:0.7}}>
        Backend URL: {process.env.NEXT_PUBLIC_BACKEND_URL}
      </p>
    </main>
  );
}
