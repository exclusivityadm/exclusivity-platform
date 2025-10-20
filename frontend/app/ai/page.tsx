'use client';
import { useEffect, useRef, useState } from 'react';
import { speak } from '@/utils/voice';
import AIAvatar from '@/components/ai/AIAvatar';

export default function AIPage() {
  const [text, setText] = useState('Hi there! Ready to test voices?');
  const [speaker, setSpeaker] = useState<'orion'|'lyric'>('orion');
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  async function handleSpeak() {
    setPlaying(true);
    try {
      const url = await speak(text, speaker);
      if (!audioRef.current) audioRef.current = new Audio();
      audioRef.current.src = url;
      await audioRef.current.play();
    } finally {
      setPlaying(false);
    }
  }
  return (
    <div style={{maxWidth: 720, margin: '40px auto', padding: 16}}>
      <h1>Orion & Lyric — Voice Test</h1>
      <div style={{display: 'flex', gap: 16, margin: '16px 0'}}>
        <AIAvatar name="Orion" active={speaker==='orion'} onClick={() => setSpeaker('orion')} />
        <AIAvatar name="Lyric" active={speaker==='lyric'} onClick={() => setSpeaker('lyric')} />
      </div>
      <textarea value={text} onChange={e => setText(e.target.value)} rows={4} style={{width: '100%'}} />
      <div style={{marginTop: 12}}>
        <button onClick={handleSpeak} disabled={playing}>
          {playing ? 'Playing…' : 'Speak'}
        </button>
      </div>
    </div>
  );
}
