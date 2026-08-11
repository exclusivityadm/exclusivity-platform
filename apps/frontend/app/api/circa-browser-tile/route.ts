import { NextRequest, NextResponse } from 'next/server';
import chromium from '@sparticuz/chromium';
import puppeteer, { type Browser } from 'puppeteer-core';

export const runtime = 'nodejs';
export const maxDuration = 60;
export const dynamic = 'force-dynamic';

const PROJECT_REF = 'fhxhudcixvbqitqdsdzj';
const AUTH_STORAGE_KEY = `sb-${PROJECT_REF}-auth-token`;
const ENGINEERING_EXCHANGE_URL = `https://${PROJECT_REF}.supabase.co/functions/v1/internal-engineering-access`;
const VIEWPORT_WIDTH = 1440;
const VIEWPORT_HEIGHT = 1100;
const TILE_WIDTH = 720;
const TILE_HEIGHT = 550;

function clampInteger(value: string | null, fallback: number, min: number, max: number) {
  const parsed = Number.parseInt(value || '', 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}

function targetFrom(request: NextRequest) {
  const rawPath = request.nextUrl.searchParams.get('path') || '/creator/home';
  if (!rawPath.startsWith('/')) throw new Error('Path must begin with /.');
  const appRoute = rawPath.startsWith('/#/') ? rawPath.slice(2) : rawPath;
  const target = new URL('/', 'https://circahaus.app');
  target.hash = appRoute;
  return target;
}

async function exchangeEngineeringSession(oidc: string) {
  if (!oidc) return null;
  const response = await fetch(ENGINEERING_EXCHANGE_URL, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${oidc}`,
    },
    body: JSON.stringify({ action: 'exchange' }),
    cache: 'no-store',
  });
  const body = await response.json().catch(() => ({})) as Record<string, unknown>;
  if (!response.ok || body.ok !== true || !body.session || typeof body.session !== 'object') {
    throw new Error(`Engineering exchange failed (${response.status}).`);
  }
  return body.session as Record<string, unknown>;
}

async function openBrowser(): Promise<Browser> {
  return puppeteer.launch({
    args: chromium.args,
    executablePath: await chromium.executablePath(),
    headless: true,
    defaultViewport: {
      width: VIEWPORT_WIDTH,
      height: VIEWPORT_HEIGHT,
      deviceScaleFactor: 1,
    },
  });
}

export async function GET(request: NextRequest) {
  let browser: Browser | undefined;
  try {
    const target = targetFrom(request);
    const tile = clampInteger(request.nextUrl.searchParams.get('tile'), 0, 0, 3);
    const quality = clampInteger(request.nextUrl.searchParams.get('quality'), 45, 30, 80);
    const oidc = request.headers.get('x-vercel-oidc-token')?.trim()
      || process.env.VERCEL_OIDC_TOKEN?.trim()
      || '';
    const session = await exchangeEngineeringSession(oidc);
    if (!session) {
      return NextResponse.json({ ok: false, error: 'Authenticated engineering session required.' }, { status: 401 });
    }

    browser = await openBrowser();
    const page = await browser.newPage();
    await page.setUserAgent('CircaHausInternalEngineeringVisualProbe/1.0');
    await page.evaluateOnNewDocument((storageKey, serializedSession) => {
      try { localStorage.setItem(storageKey, serializedSession); } catch (_) {}
    }, AUTH_STORAGE_KEY, JSON.stringify(session));

    const response = await page.goto(target.toString(), { waitUntil: 'networkidle0', timeout: 30000 });
    await new Promise(resolve => setTimeout(resolve, 1200));

    const x = (tile % 2) * TILE_WIDTH;
    const y = Math.floor(tile / 2) * TILE_HEIGHT;
    const jpeg = await page.screenshot({
      type: 'jpeg',
      quality,
      clip: { x, y, width: TILE_WIDTH, height: TILE_HEIGHT },
    });

    const format = request.nextUrl.searchParams.get('format') || 'image';
    if (format === 'json') {
      return NextResponse.json({
        ok: true,
        authenticatedEngineeringSession: true,
        requestedUrl: target.toString(),
        finalUrl: page.url(),
        status: response?.status() ?? null,
        viewport: { width: VIEWPORT_WIDTH, height: VIEWPORT_HEIGHT },
        tile: { index: tile, x, y, width: TILE_WIDTH, height: TILE_HEIGHT },
        mimeType: 'image/jpeg',
        quality,
        screenshotBase64: Buffer.from(jpeg).toString('base64'),
        capturedAt: new Date().toISOString(),
      }, { headers: { 'cache-control': 'no-store' } });
    }

    return new NextResponse(Buffer.from(jpeg), {
      status: 200,
      headers: {
        'content-type': 'image/jpeg',
        'cache-control': 'no-store',
        'x-circa-browser-url': page.url(),
        'x-circa-tile': String(tile),
      },
    });
  } catch (error) {
    return NextResponse.json({ ok: false, error: error instanceof Error ? error.message : String(error) }, {
      status: 500,
      headers: { 'cache-control': 'no-store' },
    });
  } finally {
    await browser?.close().catch(() => undefined);
  }
}
