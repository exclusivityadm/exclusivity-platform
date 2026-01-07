import { NextResponse } from "next/server";

const BACKEND = (process.env.NEXT_PUBLIC_BACKEND_URL || "").replace(/\/$/, "");

export async function GET() {
  if (!BACKEND) {
    return NextResponse.json(
      { ok: false, error: "Missing NEXT_PUBLIC_BACKEND_URL" },
      { status: 500 }
    );
  }

  try {
    const r = await fetch(`${BACKEND}/debug/routes`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });

    const j = await r.json().catch(() => null);

    if (!r.ok) {
      return NextResponse.json(
        { ok: false, error: "Backend not reachable", details: j },
        { status: 502 }
      );
    }

    return NextResponse.json({ ok: true, routes: j }, { status: 200 });
  } catch (e: any) {
    return NextResponse.json(
      { ok: false, error: e?.message || "Backend request error" },
      { status: 502 }
    );
  }
}
