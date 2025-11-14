// FULL FILE — new
"use client";
import { useEffect, useState } from "react";

export default function AI(){
  const [merchantId, setMerchantId] = useState("");
  const [qs,setQs]=useState<string[]>([]);
  const [answers,setAnswers]=useState<Record<string,string>>({});

  useEffect(()=>{(async()=>{
    const r=await fetch(`${process.env.NEXT_PUBLIC_API_URL}/ai/init-questions`, { cache:"no-store" });
    const j=await r.json(); setQs(j.questions||[]);
  })()},[]);

  return (
    <main className="p-6 space-y-4 max-w-2xl">
      <h1 className="text-xl font-semibold">AI Brand Setup</h1>
      <input className="border p-2 w-full" placeholder="merchant_id" value={merchantId} onChange={e=>setMerchantId(e.target.value)} />
      <div className="space-y-2">
        {qs.map(q=>(
          <div key={q}>
            <label className="block text-sm">{q}</label>
            <input className="border p-2 w-full" onChange={e=>setAnswers(a=>({...a,[q]:e.target.value}))}/>
          </div>
        ))}
        <button className="bg-black text-white px-3 py-2 rounded" onClick={async()=>{
          await fetch(`${process.env.NEXT_PUBLIC_API_URL}/ai/init-answers`,{
            method:"POST", headers:{ "Content-Type":"application/json" },
            body: JSON.stringify({ merchant_id: merchantId, answers })
          });
          alert("Saved");
        }}>Save</button>
      </div>
    </main>
  );
}
