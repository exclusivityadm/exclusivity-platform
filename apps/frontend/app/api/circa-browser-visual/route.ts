import { createHash } from 'node:crypto';
import { NextRequest, NextResponse } from 'next/server';
import chromium from '@sparticuz/chromium';
import puppeteer, { type Browser } from 'puppeteer-core';

export const runtime = 'nodejs';
export const maxDuration = 60;
export const dynamic = 'force-dynamic';

const PROJECT_REF = 'fhxhudcixvbqitqdsdzj';
const AUTH_STORAGE_KEY = `sb-${PROJECT_REF}-auth-token`;
const ENGINEERING_EXCHANGE_URL = `https://${PROJECT_REF}.supabase.co/functions/v1/internal-engineering-access`;

function targetFrom(request: NextRequest) {
  const rawPath = request.nextUrl.searchParams.get('path') || '/';
  if (!rawPath.startsWith('/')) throw new Error('Path must begin with /.');
  const appRoute = rawPath.startsWith('/#/') ? rawPath.slice(2) : rawPath;
  const target = new URL('/', 'https://circahaus.app');
  target.hash = appRoute;
  return target;
}

function boundedInt(value: string | null, fallback: number, min: number, max: number) {
  const parsed = Number.parseInt(value || '', 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}

async function exchangeEngineeringSession(oidc: string) {
  if (!oidc) throw new Error('Vercel OIDC token is unavailable.');
  const response = await fetch(ENGINEERING_EXCHANGE_URL, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${oidc}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify({ action: 'exchange' }),
    cache: 'no-store',
  });
  const body = await response.json().catch(() => ({})) as Record<string, unknown>;
  if (!response.ok || body.ok !== true || !body.session || typeof body.session !== 'object') {
    const stage = typeof body.stage === 'string' ? body.stage : 'unknown';
    const detail = typeof body.detail === 'string'
      ? body.detail
      : (typeof body.error === 'string' ? body.error : 'unknown');
    throw new Error(`Engineering exchange failed (${response.status}) at ${stage}: ${detail}`);
  }
  return body.session as Record<string, unknown>;
}

async function openBrowser(): Promise<Browser> {
  return puppeteer.launch({
    args: chromium.args,
    executablePath: await chromium.executablePath(),
    headless: true,
    defaultViewport: { width: 1440, height: 1100, deviceScaleFactor: 1 },
  });
}

export async function GET(request: NextRequest) {
  let browser: Browser | undefined;
  try {
    const target = targetFrom(request);
    const oidc = request.headers.get('x-vercel-oidc-token')?.trim()
      || process.env.VERCEL_OIDC_TOKEN?.trim()
      || '';
    const session = await exchangeEngineeringSession(oidc);

    browser = await openBrowser();
    const page = await browser.newPage();
    await page.setUserAgent('CircaHausInternalEngineeringVisualProbe/1.0');
    await page.evaluateOnNewDocument((storageKey, serializedSession) => {
      try { localStorage.setItem(storageKey, serializedSession); } catch (_) {}
    }, AUTH_STORAGE_KEY, JSON.stringify(session));

    const response = await page.goto(target.toString(), {
      waitUntil: 'networkidle0',
      timeout: 30000,
    });
    await new Promise(resolve => setTimeout(resolve, 600));

    const client = await page.createCDPSession();
    const shot = await client.send('Page.captureScreenshot', {
      format: 'jpeg',
      quality: 38,
      fromSurface: true,
      captureBeyondViewport: false,
      clip: {
        x: 0,
        y: 0,
        width: 1440,
        height: 1100,
        scale: 0.25,
      },
    }) as { data: string };
    await client.detach();

    const bytes = Buffer.from(shot.data, 'base64');
    const sha256 = createHash('sha256').update(bytes).digest('hex');
    const chunkSize = boundedInt(request.nextUrl.searchParams.get('chunkSize'), 1200, 200, 3000);
    const totalChunks = Math.max(1, Math.ceil(shot.data.length / chunkSize));
    const chunkIndex = boundedInt(request.nextUrl.searchParams.get('chunk'), 0, 0, Math.max(0, totalChunks - 1));
    const start = chunkIndex * chunkSize;
    const screenshotBase64Chunk = shot.data.slice(start, start + chunkSize);

    return NextResponse.json({
      ok: true,
      authenticatedEngineeringSession: true,
      requestedUrl: target.toString(),
      finalUrl: page.url(),
      status: response?.status() ?? null,
      mimeType: 'image/jpeg',
      sourceDimensions: { width: 1440, height: 1100 },
      visualDimensions: { width: 360, height: 275 },
      byteLength: bytes.length,
      sha256,
      base64Length: shot.data.length,
      chunkSize,
      chunkIndex,
      totalChunks,
      chunkSha256: createHash('sha256').update(screenshotBase64Chunk).digest('hex'),
      screenshotBase64Chunk,
      capturedAt: new Date().toISOString(),
    }, { headers: { 'cache-control': 'no-store' } });
  } catch (error) {
    return NextResponse.json({
      ok: false,
      error: error instanceof Error ? error.message : String(error),
    }, { status: 500, headers: { 'cache-control': 'no-store' } });
  } finally {
    await browser?.close().catch(() => undefined);
  }
}
