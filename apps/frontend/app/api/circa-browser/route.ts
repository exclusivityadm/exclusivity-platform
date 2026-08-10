import { NextRequest, NextResponse } from 'next/server';
import chromium from '@sparticuz/chromium';
import puppeteer, { type Browser, type Page } from 'puppeteer-core';

export const runtime = 'nodejs';
export const maxDuration = 60;
export const dynamic = 'force-dynamic';

const ALLOWED_HOSTS = new Set(['circahaus.app', 'www.circahaus.app']);
const PROJECT_REF = 'fhxhudcixvbqitqdsdzj';
const AUTH_STORAGE_KEY = `sb-${PROJECT_REF}-auth-token`;
const ENGINEERING_EXCHANGE_URL = `https://${PROJECT_REF}.supabase.co/functions/v1/internal-engineering-access`;
const CORE_ROUTES = [
  '/',
  '/creator/home',
  '/supporter/home',
  '/saia',
  '/creator/brand-commerce',
  '/creator/qr-center',
  '/creator/campaigns',
  '/settings',
  '/settings/security',
  '/appearance',
  '/admin/security/activity',
];

function targetFrom(request: NextRequest) {
  const rawPath = request.nextUrl.searchParams.get('path') || '/';
  if (!rawPath.startsWith('/')) throw new Error('Path must begin with /.');
  const target = new URL(rawPath, 'https://circahaus.app');
  if (!ALLOWED_HOSTS.has(target.hostname)) throw new Error('Target host is not allowed.');
  return target;
}

async function openBrowser(): Promise<Browser> {
  return puppeteer.launch({
    args: chromium.args,
    executablePath: await chromium.executablePath(),
    headless: true,
    defaultViewport: { width: 1440, height: 1100, deviceScaleFactor: 1 },
  });
}

async function exchangeEngineeringGrant(grant: string) {
  if (!grant) return null;
  const response = await fetch(ENGINEERING_EXCHANGE_URL, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ action: 'exchange', grant }),
    cache: 'no-store',
  });
  const body = await response.json().catch(() => ({})) as Record<string, unknown>;
  if (!response.ok || body.ok !== true || !body.session || typeof body.session !== 'object') {
    const stage = typeof body.stage === 'string' ? body.stage : 'unknown';
    const detail = typeof body.detail === 'string' ? body.detail : (typeof body.error === 'string' ? body.error : 'unknown');
    throw new Error(`Engineering exchange failed (${response.status}) at ${stage}: ${detail}`);
  }
  return body.session as Record<string, unknown>;
}

async function enableFlutterSemantics(page: Page) {
  const placeholder = await page.$('flt-semantics-placeholder[aria-label="Enable accessibility"]');
  if (placeholder) {
    await placeholder.click().catch(() => undefined);
    await new Promise(resolve => setTimeout(resolve, 500));
  }
}

async function captureSnapshot(page: Page) {
  await enableFlutterSemantics(page);
  return page.evaluate((storageKey) => {
    const nodes = Array.from(document.querySelectorAll('[aria-label],[role],a,button,input,textarea,select'));
    const interactive = nodes.slice(0, 500).map((node) => {
      const el = node as HTMLElement;
      const input = node as HTMLInputElement;
      return {
        tag: node.tagName.toLowerCase(),
        text: (el.innerText || input.value || '').trim().slice(0, 220),
        ariaLabel: node.getAttribute('aria-label'),
        role: node.getAttribute('role'),
        href: node instanceof HTMLAnchorElement ? node.href : null,
        type: input.type || null,
      };
    });
    const labels = nodes
      .map(node => node.getAttribute('aria-label'))
      .filter((value): value is string => !!value && value.trim().length > 0)
      .slice(0, 500);
    return {
      title: document.title,
      text: (document.body?.innerText || '').slice(0, 30000),
      labels,
      interactive,
      htmlLength: document.documentElement?.outerHTML.length || 0,
      hasAuthStorage: !!localStorage.getItem(storageKey),
    };
  }, AUTH_STORAGE_KEY);
}

export async function GET(request: NextRequest) {
  let target: URL;
  try {
    target = targetFrom(request);
  } catch (error) {
    return NextResponse.json({ ok: false, error: String(error) }, { status: 400 });
  }

  const mode = request.nextUrl.searchParams.get('mode') || 'snapshot';
  const suite = request.nextUrl.searchParams.get('suite') || '';
  const grant = request.nextUrl.searchParams.get('grant')?.trim() || '';
  const consoleErrors: string[] = [];
  const requestFailures: Array<{ url: string; error: string }> = [];
  let browser: Browser | undefined;

  try {
    const engineeringSession = await exchangeEngineeringGrant(grant);
    browser = await openBrowser();
    const page = await browser.newPage();
    await page.setUserAgent('CircaHausInternalEngineeringBrowser/1.0');

    if (engineeringSession) {
      await page.evaluateOnNewDocument((storageKey, serializedSession) => {
        try { localStorage.setItem(storageKey, serializedSession); } catch (_) {}
      }, AUTH_STORAGE_KEY, JSON.stringify(engineeringSession));
    }

    page.on('console', (message) => {
      if (message.type() === 'error') consoleErrors.push(message.text());
    });
    page.on('requestfailed', (failed) => {
      requestFailures.push({
        url: failed.url(),
        error: failed.failure()?.errorText || 'request failed',
      });
    });

    if (suite === 'core') {
      const results: Array<Record<string, unknown>> = [];
      for (const path of CORE_ROUTES) {
        const url = new URL(path, 'https://circahaus.app');
        try {
          const response = await page.goto(url.toString(), { waitUntil: 'networkidle0', timeout: 20000 });
          const snapshot = await captureSnapshot(page);
          results.push({ path, finalUrl: page.url(), status: response?.status() ?? null, snapshot });
        } catch (error) {
          results.push({ path, finalUrl: page.url(), error: error instanceof Error ? error.message : String(error) });
        }
      }
      return NextResponse.json({
        ok: true,
        authenticatedEngineeringSession: !!engineeringSession,
        suite: 'core',
        routeCount: results.length,
        results,
        consoleErrors: consoleErrors.slice(0, 200),
        requestFailures: requestFailures.slice(0, 200),
        capturedAt: new Date().toISOString(),
      }, { headers: { 'cache-control': 'no-store' } });
    }

    const response = await page.goto(target.toString(), {
      waitUntil: 'networkidle0',
      timeout: 30000,
    });
    await enableFlutterSemantics(page);

    if (mode === 'screenshot' || mode === 'screenshot-json') {
      const png = await page.screenshot({ fullPage: true, type: 'png' });
      if (mode === 'screenshot-json') {
        return NextResponse.json({
          ok: true,
          authenticatedEngineeringSession: !!engineeringSession,
          requestedUrl: target.toString(),
          finalUrl: page.url(),
          status: response?.status() ?? null,
          screenshotBase64: Buffer.from(png).toString('base64'),
          consoleErrors: consoleErrors.slice(0, 100),
          requestFailures: requestFailures.slice(0, 100),
          capturedAt: new Date().toISOString(),
        }, { headers: { 'cache-control': 'no-store' } });
      }
      return new NextResponse(Buffer.from(png), {
        status: 200,
        headers: {
          'content-type': 'image/png',
          'cache-control': 'no-store',
          'x-circa-browser-url': page.url(),
        },
      });
    }

    const snapshot = await captureSnapshot(page);

    return NextResponse.json({
      ok: true,
      authenticatedEngineeringSession: !!engineeringSession,
      requestedUrl: target.toString(),
      finalUrl: page.url(),
      status: response?.status() ?? null,
      snapshot,
      consoleErrors: consoleErrors.slice(0, 100),
      requestFailures: requestFailures.slice(0, 100),
      capturedAt: new Date().toISOString(),
    }, { headers: { 'cache-control': 'no-store' } });
  } catch (error) {
    return NextResponse.json({
      ok: false,
      requestedUrl: target.toString(),
      error: error instanceof Error ? error.message : String(error),
      consoleErrors: consoleErrors.slice(0, 100),
      requestFailures: requestFailures.slice(0, 100),
    }, { status: 500, headers: { 'cache-control': 'no-store' } });
  } finally {
    await browser?.close().catch(() => undefined);
  }
}
