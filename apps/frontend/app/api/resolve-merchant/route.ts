import { NextResponse } from "next/server";

const BACKEND = (process.env.NEXT_PUBLIC_BACKEND_URL || "").replace(/\/$/, "");

async function safeJson(res: Response) {
  const txt = await res.text();
  try {
    return txt ? JSON.parse(txt) : null;
  } catch {
    return txt;
  }
}

export async function POST(req: Request) {
  if (!BACKEND) {
    return NextResponse.json(
      { ok: false, error: "Missing NEXT_PUBLIC_BACKEND_URL" },
      { status: 500 }
    );
  }

  const body = await req.json().catch(() => null);
  const shop_domain = body?.shop_domain;

  if (!shop_domain || typeof shop_domain !== "string") {
    return NextResponse.json({ ok: false, error: "Missing shop_domain" }, { status: 400 });
  }

  // 1) Try fetch profile
  try {
    const r1 = await fetch(
      `${BACKEND}/merchant/profile?shop_domain=${encodeURIComponent(shop_domain)}`,
      {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      }
    );

    const j1 = await safeJson(r1);

    if (r1.ok && j1) {
      const merchant_id = (j1 as any).merchant_id || (j1 as any).id;
      if (merchant_id) {
        return NextResponse.json(
          { ok: true, merchant_id, shop_domain, created: false },
          { status: 200 }
        );
      }
    }

    // 2) Bootstrap via brand ingest (create merchant record if missing)
    const r2 = await fetch(`${BACKEND}/brand/ingest`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ shop_domain }),
      cache: "no-store",
    });

    await safeJson(r2); // ignore payload; we only care that it succeeded

    // 3) Re-fetch profile
    const r3 = await fetch(
      `${BACKEND}/merchant/profile?shop_domain=${encodeURIComponent(shop_domain)}`,
      {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      }
    );

    const j3 = await safeJson(r3);

    if (r3.ok && j3) {
      const merchant_id = (j3 as any).merchant_id || (j3 as any).id;
      if (merchant_id) {
        return NextResponse.json(
          { ok: true, merchant_id, shop_domain, created: true },
          { status: 200 }
        );
      }
    }

    return NextResponse.json(
      { ok: false, error: "Unable to resolve merchant identity", details: { profile: j1, after_ingest: j3 } },
      { status: 404 }
    );
  } catch (e: any) {
    return NextResponse.json(
      { ok: false, error: e?.message || "Resolve merchant error" },
      { status: 500 }
    );
  }
}
