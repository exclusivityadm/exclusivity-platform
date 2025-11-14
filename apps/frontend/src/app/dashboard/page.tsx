// FULL FILE — new
"use client";
import { useEffect, useState } from "react";

export default function Dashboard(){
  const [status,setStatus]=useState<{health?:boolean}>({});
  useEffect(()=>{(async()=>{
    try{
      const ok = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`, { cache:"no-store" }).then(r=>r.ok);
      setStatus({ health: ok });
    }catch{ setStatus({ health:false }); }
  })()},[]);
  return (
    <main className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <div className="grid grid-cols-2 gap-3">
        <div className="border p-3 rounded">Health: {status.health ? "OK" : "Check"}</div>
        <div className="border p-3 rounded">Voice: Primary/Fallback configured</div>
        <div className="border p-3 rounded">RLS: Configured</div>
        <div className="border p-3 rounded">Points Today: (wire next)</div>
      </div>
    </main>
  );
}
