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

  // Circa Haus currently uses Flutter's default hash URL strategy. A plain
  // browser path such as /creator/home loads the web shell but leaves Flutter
  // on its root route. Translate bridge paths into hash routes so the route
  // visible in the browser and the route rendered by Flutter stay aligned.
  const appRoute = rawPath.startsWith('/#/') ? rawPath.slice(2) : rawPath;
  const target = new URL('/', 'https://circahaus.app');
  target.hash = appRoute;
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

async function exchangeEngineeringSession(grant: string, oidc: string) {
  if (!grant && !oidc) return null;
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if (oidc) headers.authorization = `Bearer ${oidc}`;
  const response = await fetch(ENGINEERING_EXCHANGE_URL, {
    method: 'POST',
    headers,
    body: JSON.stringify({ action: 'exchange', ...(grant ? { grant } : {}) }),
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
  await page.evaluate(() => {
    const visit = (root: Document | ShadowRoot): HTMLElement | null => {
      const direct = root.querySelector('flt-semantics-placeholder[aria-label="Enable accessibility"]') as HTMLElement | null;
      if (direct) return direct;
      for (const el of Array.from(root.querySelectorAll('*'))) {
        if ((el as HTMLElement).shadowRoot) {
          const found = visit((el as HTMLElement).shadowRoot!);
          if (found) return found;
        }
      }
      return null;
    };
    visit(document)?.click();
  }).catch(() => undefined);
  await new Promise(resolve => setTimeout(resolve, 900));
}

async function clickSemantic(page: Page, requestedText: string) {
  const targetText = requestedText.trim().toLowerCase();
  if (!targetText) return { clicked: false, reason: 'empty click text' };
  await enableFlutterSemantics(page);
  return page.evaluate((needle) => {
    const roots: Array<Document | ShadowRoot> = [document];
    const candidates: HTMLElement[] = [];
    while (roots.length) {
      const root = roots.shift()!;
      for (const node of Array.from(root.querySelectorAll('*'))) {
        const el = node as HTMLElement;
        if (el.shadowRoot) roots.push(el.shadowRoot);
        if (node.getAttribute('role') === 'button' || node.tagName === 'BUTTON' || node.tagName === 'A') {
          candidates.push(el);
        }
      }
    }
    const labelFor = (el: HTMLElement) =>
      (el.getAttribute('aria-label') || el.innerText || el.textContent || '').trim().toLowerCase();
    const exact = candidates.find(el => labelFor(el) === needle);
    const partial = candidates.find(el => labelFor(el).includes(needle));
    const target = exact || partial;
    if (!target) {
      return {
        clicked: false,
        reason: 'semantic target not found',
        candidates: candidates.map(labelFor).filter(Boolean).slice(0, 100),
      };
    }
    const rect = target.getBoundingClientRect();
    const label = labelFor(target);
    target.click();
    return {
      clicked: true,
      label,
      x: Math.round(rect.x),
      y: Math.round(rect.y),
      width: Math.round(rect.width),
      height: Math.round(rect.height),
    };
  }, targetText);
}

async function captureAccessibilityTree(page: Page) {
  try {
    const client = await page.createCDPSession();
    await client.send('Accessibility.enable');
    const tree = await client.send('Accessibility.getFullAXTree') as { nodes?: Array<Record<string, any>> };
    await client.detach();
    return (tree.nodes || []).slice(0, 800).map((node) => ({
      nodeId: node.nodeId ?? null,
      parentId: node.parentId ?? null,
      ignored: !!node.ignored,
      role: node.role?.value ?? null,
      name: node.name?.value ?? null,
      value: node.value?.value ?? null,
      description: node.description?.value ?? null,
      properties: Array.isArray(node.properties)
        ? node.properties
            .filter((property: any) => ['focusable', 'focused', 'editable', 'disabled', 'checked', 'selected', 'expanded', 'hasPopup'].includes(property.name))
            .map((property: any) => ({ name: property.name, value: property.value?.value ?? null }))
        : [],
    }));
  } catch {
    return [];
  }
}

async function captureSnapshot(page: Page) {
  await enableFlutterSemantics(page);
  const dom = await page.evaluate((storageKey) => {
    const roots: Array<Document | ShadowRoot> = [document];
    const seen = new Set<Node>();
    const nodes: Element[] = [];
    let shadowRootCount = 0;

    while (roots.length) {
      const root = roots.shift()!;
      for (const node of Array.from(root.querySelectorAll('*'))) {
        if (!seen.has(node)) {
          seen.add(node);
          nodes.push(node);
        }
        const shadow = (node as HTMLElement).shadowRoot;
        if (shadow && !seen.has(shadow)) {
          seen.add(shadow);
          shadowRootCount += 1;
          roots.push(shadow);
        }
      }
    }

    const interesting = nodes.filter((node) =>
      node.hasAttribute('aria-label') ||
      node.hasAttribute('role') ||
      ['A', 'BUTTON', 'INPUT', 'TEXTAREA', 'SELECT'].includes(node.tagName) ||
      node.tagName.toLowerCase().startsWith('flt-semantics')
    );

    const interactive = interesting.slice(0, 800).map((node) => {
      const el = node as HTMLElement;
      const input = node as HTMLInputElement;
      const rect = el.getBoundingClientRect();
      return {
        tag: node.tagName.toLowerCase(),
        text: (el.innerText || input.value || '').trim().slice(0, 220),
        ariaLabel: node.getAttribute('aria-label'),
        role: node.getAttribute('role'),
        href: node instanceof HTMLAnchorElement ? node.href : null,
        type: input.type || null,
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      };
    });

    const labels = interesting
      .map(node => node.getAttribute('aria-label'))
      .filter((value): value is string => !!value && value.trim().length > 0)
      .slice(0, 800);

    return {
      title: document.title,
      text: (document.body?.innerText || '').slice(0, 30000),
      labels,
      interactive,
      htmlLength: document.documentElement?.outerHTML.length || 0,
      hasAuthStorage: !!localStorage.getItem(storageKey),
      shadowRootCount,
      fltSemanticsCount: nodes.filter(node => node.tagName.toLowerCase().startsWith('flt-semantics')).length,
      canvasCount: nodes.filter(node => node.tagName.toLowerCase() === 'canvas').length,
    };
  }, AUTH_STORAGE_KEY);
  const accessibility = await captureAccessibilityTree(page);
  return { ...dom, accessibility };
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
  const clickText = request.nextUrl.searchParams.get('click')?.trim() || '';
  const grant = request.nextUrl.searchParams.get('grant')?.trim() || '';
  const oidc = request.headers.get('x-vercel-oidc-token')?.trim()
    || process.env.VERCEL_OIDC_TOKEN?.trim()
    || '';
  const consoleErrors: string[] = [];
  const requestFailures: Array<{ url: string; error: string }> = [];
  let browser: Browser | undefined;

  try {
    const engineeringSession = await exchangeEngineeringSession(grant, oidc);
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
      requestFailures.push({ url: failed.url(), error: failed.failure()?.errorText || 'request failed' });
    });

    if (suite === 'core') {
      const results: Array<Record<string, unknown>> = [];
      for (const path of CORE_ROUTES) {
        const url = new URL('/', 'https://circahaus.app');
        url.hash = path;
        try {
          const response = await page.goto(url.toString(), { waitUntil: 'networkidle0', timeout: 20000 });
          const snapshot = await captureSnapshot(page);
          results.push({ path, finalUrl: page.url(), status: response?.status() ?? null, snapshot });
        } catch (error) {
          results.push({ path, finalUrl: page.url(), error: error instanceof Error ? error.message : String(error) });
        }
      }
      return NextResponse.json({ ok: true, authenticatedEngineeringSession: !!engineeringSession, suite: 'core', routeCount: results.length, results, consoleErrors: consoleErrors.slice(0, 200), requestFailures: requestFailures.slice(0, 200), capturedAt: new Date().toISOString() }, { headers: { 'cache-control': 'no-store' } });
    }

    const response = await page.goto(target.toString(), { waitUntil: 'networkidle0', timeout: 30000 });
    await enableFlutterSemantics(page);

    let action: Record<string, unknown> | null = null;
    if (clickText) {
      action = await clickSemantic(page, clickText);
      await new Promise(resolve => setTimeout(resolve, 1200));
      await page.waitForNetworkIdle({ idleTime: 400, timeout: 5000 }).catch(() => undefined);
    }

    if (mode === 'screenshot' || mode === 'screenshot-json') {
      const png = await page.screenshot({ fullPage: true, type: 'png' });
      if (mode === 'screenshot-json') {
        return NextResponse.json({ ok: true, authenticatedEngineeringSession: !!engineeringSession, requestedUrl: target.toString(), finalUrl: page.url(), status: response?.status() ?? null, action, screenshotBase64: Buffer.from(png).toString('base64'), consoleErrors: consoleErrors.slice(0, 100), requestFailures: requestFailures.slice(0, 100), capturedAt: new Date().toISOString() }, { headers: { 'cache-control': 'no-store' } });
      }
      return new NextResponse(Buffer.from(png), { status: 200, headers: { 'content-type': 'image/png', 'cache-control': 'no-store', 'x-circa-browser-url': page.url() } });
    }

    const snapshot = await captureSnapshot(page);
    return NextResponse.json({ ok: true, authenticatedEngineeringSession: !!engineeringSession, requestedUrl: target.toString(), finalUrl: page.url(), status: response?.status() ?? null, action, snapshot, consoleErrors: consoleErrors.slice(0, 100), requestFailures: requestFailures.slice(0, 100), capturedAt: new Date().toISOString() }, { headers: { 'cache-control': 'no-store' } });
  } catch (error) {
    return NextResponse.json({ ok: false, requestedUrl: target.toString(), error: error instanceof Error ? error.message : String(error), consoleErrors: consoleErrors.slice(0, 100), requestFailures: requestFailures.slice(0, 100) }, { status: 500, headers: { 'cache-control': 'no-store' } });
  } finally {
    await browser?.close().catch(() => undefined);
  }
}
