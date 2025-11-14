// FULL FILE — drop in as-is
export async function api(path: string, init?: RequestInit) {
  const base = process.env.NEXT_PUBLIC_API_URL!;
  const r = await fetch(`${base}${path}`, { cache: "no-store", ...init });
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
  return r.json();
}
