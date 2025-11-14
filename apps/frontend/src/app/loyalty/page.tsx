// FULL FILE — new
"use client";
import { useState } from "react";

export default function Loyalty(){
  const [merchantId, setMerchantId] = useState("");
  const [customer,setCustomer]=useState("");
  const [points,setPoints]=useState(10);
  const [out,setOut]=useState<any>(null);

  return (
    <main className="p-6 space-y-3">
      <h1 className="text-xl font-semibold">Loyalty</h1>
      <div className="flex flex-col gap-2 max-w-xl">
        <input className="border p-2" placeholder="merchant_id" value={merchantId} onChange={e=>setMerchantId(e.target.value)} />
        <div className="flex gap-2">
          <input className="border p-2" placeholder="customer_id" value={customer} onChange={e=>setCustomer(e.target.value)} />
          <input className="border p-2 w-28" type="number" value={points} onChange={e=>setPoints(+e.target.value)} />
          <button className="bg-black text-white px-3 py-2 rounded" onClick={async()=>{
            const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/loyalty/accrue`,{
              method:"POST", headers:{ "Content-Type":"application/json" },
              body: JSON.stringify({ merchant_id: merchantId, customer_id: customer, points, reason:"manual-test" })
            });
            setOut(await r.json());
          }}>Accrue</button>
        </div>
      </div>
      {out && <pre className="bg-gray-100 p-3 rounded text-sm overflow-auto">{JSON.stringify(out,null,2)}</pre>}
    </main>
  );
}
