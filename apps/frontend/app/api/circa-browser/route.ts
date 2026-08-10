import { NextRequest, NextResponse } from 'next/server';
import chromium from '@sparticuz/chromium';
import puppeteer, { type Browser } from 'puppeteer-core';

export const runtime = 'nodejs';
export const maxDuration = 60;
export const dynamic = 'force-dynamic';

const ALLOWED_HOSTS = new Set(['circahaus.app', 'www.circahaus.app']);

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

export async function GET(request: NextRequest) {
  let target: URL;
  try {
    target = targetFrom(request);
  } catch (error) {
    return NextResponse.json({ ok: false, error: String(error) }, { status: 400 });
  }

  const mode = request.nextUrl.searchParams.get('mode') || 'snapshot';
  const consoleErrors: string[] = [];
  const requestFailures: Array<{ url: string; error: string }> = [];
  let browser: Browser | undefined;

  try {
    browser = await openBrowser();
    const page = await browser.newPage();
    await page.setUserAgent('CircaHausInternalEngineeringBrowser/1.0');

    page.on('console', (message) => {
      if (message.type() === 'error') consoleErrors.push(message.text());
    });
    page.on('requestfailed', (failed) => {
      requestFailures.push({
        url: failed.url(),
        error: failed.failure()?.errorText || 'request failed',
      });
    });

    const response = await page.goto(target.toString(), {
      waitUntil: 'networkidle0',
      timeout: 30000,
    });

    if (mode === 'screenshot' || mode === 'screenshot-json') {
      const png = await page.screenshot({ fullPage: true, type: 'png' });
      if (mode === 'screenshot-json') {
        return NextResponse.json({
          ok: true,
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

    const snapshot = await page.evaluate(() => {
      const interactive = Array.from(
        document.querySelectorAll('a,button,input,textarea,select,[role="button"],[role="link"]'),
      ).slice(0, 250).map((node) => {
        const el = node as HTMLElement;
        const input = node as HTMLInputElement;
        return {
          tag: node.tagName.toLowerCase(),
          text: (el.innerText || input.value || '').trim().slice(0, 180),
          ariaLabel: node.getAttribute('aria-label'),
          role: node.getAttribute('role'),
          href: node instanceof HTMLAnchorElement ? node.href : null,
          type: input.type || null,
        };
      });

      return {
        title: document.title,
        text: (document.body?.innerText || '').slice(0, 30000),
        interactive,
        htmlLength: document.documentElement?.outerHTML.length || 0,
      };
    });

    return NextResponse.json({
      ok: true,
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
