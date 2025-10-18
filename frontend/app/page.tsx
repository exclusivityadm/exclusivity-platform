'use client'
import { useState } from 'react'
import axios from 'axios'

const BURL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000'

export default function Home() {
  const [agent, setAgent] = useState<'orion'|'lyric'>('orion')
  const [prompt, setPrompt] = useState('Hello, can you summarize our loyalty status?')
  const [reply, setReply] = useState('')

  async function ask() {
    const res = await axios.post(`${BURL}/ai/start`, { agent, message: prompt })
    setReply(res.data.reply)
  }

  function speak() {
    const url = `${BURL}/voice/speak?text=${encodeURIComponent('This is ' + agent + ' speaking.')}&&agent=${agent}`
    const audio = new Audio(url)
    audio.play()
  }

  return (
    <main style={{padding:24, maxWidth:900, margin:'0 auto'}}>
      <h1>Exclusivity — Orion & Lyric</h1>
      <div style={{display:'flex', gap:8, marginTop:12}}>
        <button onClick={()=>setAgent('orion')} style={{padding:8, background: agent==='orion'?'#111':'#ddd', color: agent==='orion'?'#fff':'#111'}}>Orion</button>
        <button onClick={()=>setAgent('lyric')} style={{padding:8, background: agent==='lyric'?'#111':'#ddd', color: agent==='lyric'?'#fff':'#111'}}>Lyric</button>
      </div>

      <textarea value={prompt} onChange={e=>setPrompt(e.target.value)} style={{width:'100%', height:120, marginTop:12}}/>

      <div style={{display:'flex', gap:12, marginTop:12}}>
        <button onClick={ask} style={{padding:'10px 16px'}}>Ask</button>
        <button onClick={speak} style={{padding:'10px 16px'}}>Test Voice</button>
      </div>

      <h3 style={{marginTop:24}}>Reply</h3>
      <pre style={{whiteSpace:'pre-wrap', background:'#f8fafc', padding:12, borderRadius:8}}>{reply}</pre>
    </main>
  )
}
