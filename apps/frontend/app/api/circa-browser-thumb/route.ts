import { NextRequest, NextResponse } from 'next/server';
import chromium from '@sparticuz/chromium';
import puppeteer, { type Browser } from 'puppeteer-core';

export const runtime = 'nodejs';
export const maxDuration = 60;
export const dynamic = 'force-dynamic';

const PROJECT_REF = 'fhxhudcixvbqitqdsdzj';
const AUTH_STORAGE_KEY = `sb-${PROJECT_REF}-auth-token`;
const ENGINEERING_EXCHANGE_URL = `https://${PROJECT_REF}.supabase.co/functions/v1/internal-engineering-access`;

async function exchange(oidc: string) {
  const r = await fetch(ENGINEERING_EXCHANGE_URL, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${oidc}` },
    body: JSON.stringify({ action: 'exchange' }),
    cache: 'no-store',
  });
  const b = await r.json().catch(() => ({})) as Record<string, unknown>;
  return r.ok && b.ok === true && b.session && typeof b.session === 'object'
    ? b.session as Record<string, unknown>
    : null;
}

async function openBrowser(): Promise<Browser> {
  return puppeteer.launch({
    args: chromium.args,
    executablePath: await chromium.executablePath(),
    headless: true,
    defaultViewport: { width: 1440, height: 1100, deviceScaleFactor: 0.12 },
  });
}

export async function GET(request: NextRequest) {
  let browser: Browser | undefined;
  try {
    const rawPath = request.nextUrl.searchParams.get('path') || '/creator/home';
    const route = rawPath.startsWith('/#/') ? rawPath.slice(2) : rawPath;
    const target = new URL('/', 'https://circahaus.app');
    target.hash = route;
    const oidc = request.headers.get('x-vercel-oidc-token')?.trim() || process.env.VERCEL_OIDC_TOKEN?.trim() || '';
    const session = await exchange(oidc);
    if (!session) return NextResponse.json({ ok: false, error: 'auth required' }, { status: 401 });

    browser = await openBrowser();
    const page = await browser.newPage();
    await page.evaluateOnNewDocument((key, value) => {
      try { localStorage.setItem(key, value); } catch (_) {}
    }, AUTH_STORAGE_KEY, JSON.stringify(session));
    await page.goto(target.toString(), { waitUntil: 'networkidle0', timeout: 30000 });
    await new Promise(resolve => setTimeout(resolve, 1000));
    const jpg = await page.screenshot({ fullPage: true, type: 'jpeg', quality: 35 });
    return NextResponse.json({
      ok: true,
      finalUrl: page.url(),
      cssViewport: { width: 1440, height: 1100 },
      deviceScaleFactor: 0.12,
      screenshotBase64: Buffer.from(jpg).toString('base64'),
    }, { headers: { 'cache-control': 'no-store' } });
  } catch (e) {
    return NextResponse.json({ ok: false, error: e instanceof Error ? e.message : String(e) }, { status: 500 });
  } finally {
    await browser?.close().catch(() => undefined);
  }
}
