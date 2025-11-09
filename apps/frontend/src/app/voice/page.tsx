'use client';

import { useState } from 'react';

export default function Voice() {
  const [status, setStatus] = useState<string>('idle');

  async function ping() {
    setStatus('calling backend...');
    const url = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const res = await fetch(`${url}/health`);
    const j = await res.json();
    setStatus(`backend: ${j.status}`);
  }

  return (
    <main style={{padding: 24}}>
      <h2>Voice Check</h2>
      <button onClick={ping}>Ping Backend</button>
      <p>Status: {status}</p>
    </main>
  );
}
