import { NextResponse } from "next/server";

const BACKEND = (process.env.NEXT_PUBLIC_BACKEND_URL || "").replace(/\/$/, "");
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || "";
const SHOPIFY_ADMIN_TOKEN = process.env.SHOPIFY_ADMIN_TOKEN || "";

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
  if (!ADMIN_TOKEN) {
    return NextResponse.json(
      { ok: false, error: "Missing ADMIN_TOKEN (server env)" },
      { status: 500 }
    );
  }
  if (!SHOPIFY_ADMIN_TOKEN) {
    return NextResponse.json(
      { ok: false, error: "Missing SHOPIFY_ADMIN_TOKEN (server env)" },
      { status: 500 }
    );
  }

  const body = await req.json().catch(() => null);

  const merchant_id = body?.merchant_id;
  const shop_domain = body?.shop_domain;
  const points_per_dollar = typeof body?.points_per_dollar === "number" ? body.points_per_dollar : 1.0;

  if (!merchant_id || typeof merchant_id !== "string") {
    return NextResponse.json({ ok: false, error: "Missing merchant_id" }, { status: 400 });
  }
  if (!shop_domain || typeof shop_domain !== "string") {
    return NextResponse.json({ ok: false, error: "Missing shop_domain" }, { status: 400 });
  }

  try {
    const r = await fetch(`${BACKEND}/shopify/backfill/run`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-Admin-Token": ADMIN_TOKEN,
      },
      body: JSON.stringify({
        merchant_id,
        shop_domain,
        access_token: SHOPIFY_ADMIN_TOKEN,
        points_per_dollar,
      }),
      cache: "no-store",
    });

    const j = await safeJson(r);

    if (!r.ok) {
      return NextResponse.json(
        { ok: false, error: "Backfill failed", details: j },
        { status: 502 }
      );
    }

    return NextResponse.json(
      { ok: true, merchant_id, shop_domain, started: true, result: j },
      { status: 200 }
    );
  } catch (e: any) {
    return NextResponse.json(
      { ok: false, error: e?.message || "Backfill request error" },
      { status: 502 }
    );
  }
}
