import { createHash } from 'node:crypto';
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

type BrowserAction =
  | { type: 'click'; x: number; y: number }
  | { type: 'clickText'; text: string; occurrence?: number; contains?: boolean }
  | { type: 'type'; text: string; delay?: number }
  | { type: 'press'; key: string }
  | { type: 'scroll'; deltaY: number; deltaX?: number }
  | { type: 'wait'; ms: number };

function targetFrom(request: NextRequest) {
  const rawPath = request.nextUrl.searchParams.get('path') || '/';
  if (!rawPath.startsWith('/')) throw new Error('Path must begin with /.');

  const appRoute = rawPath.startsWith('/#/') ? rawPath.slice(2) : rawPath;
  const target = new URL('/', 'https://circahaus.app');
  target.hash = appRoute;
  if (!ALLOWED_HOSTS.has(target.hostname)) throw new Error('Target host is not allowed.');
  return target;
}

function clampInteger(value: string | null, fallback: number, min: number, max: number) {
  const parsed = Number.parseInt(value || '', 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}

function parseActions(request: NextRequest): BrowserAction[] {
  const raw = request.nextUrl.searchParams.get('actions');
  if (!raw) return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error('actions must be valid JSON.');
  }
  if (!Array.isArray(parsed)) throw new Error('actions must be a JSON array.');
  if (parsed.length > 20) throw new Error('actions is limited to 20 steps per request.');

  return parsed.map((candidate, index) => {
    if (!candidate || typeof candidate !== 'object') {
      throw new Error(`actions[${index}] must be an object.`);
    }
    const action = candidate as Record<string, unknown>;
    const type = action.type;
    if (type === 'click') {
      const x = Number(action.x);
      const y = Number(action.y);
      if (!Number.isFinite(x) || !Number.isFinite(y)) {
        throw new Error(`actions[${index}] click requires numeric x and y.`);
      }
      return { type, x, y };
    }
    if (type === 'clickText') {
      const text = typeof action.text === 'string' ? action.text.trim() : '';
      if (!text || text.length > 300) {
        throw new Error(`actions[${index}] clickText requires text up to 300 characters.`);
      }
      const occurrence = action.occurrence == null ? 0 : Number(action.occurrence);
      if (!Number.isInteger(occurrence) || occurrence < 0 || occurrence > 50) {
        throw new Error(`actions[${index}] clickText occurrence must be an integer from 0 to 50.`);
      }
      return { type, text, occurrence, contains: action.contains === true };
    }
    if (type === 'type') {
      const text = typeof action.text === 'string' ? action.text : '';
      if (text.length > 4000) throw new Error(`actions[${index}] type text is too long.`);
      const delay = action.delay == null ? 0 : Number(action.delay);
      if (!Number.isFinite(delay) || delay < 0 || delay > 250) {
        throw new Error(`actions[${index}] type delay must be from 0 to 250 ms.`);
      }
      return { type, text, delay };
    }
    if (type === 'press') {
      const key = typeof action.key === 'string' ? action.key.trim() : '';
      if (!key || key.length > 40) throw new Error(`actions[${index}] press requires a valid key.`);
      return { type, key };
    }
    if (type === 'scroll') {
      const deltaY = Number(action.deltaY);
      const deltaX = action.deltaX == null ? 0 : Number(action.deltaX);
      if (!Number.isFinite(deltaY) || !Number.isFinite(deltaX)) {
        throw new Error(`actions[${index}] scroll requires numeric deltaY/deltaX.`);
      }
      return {
        type,
        deltaY: Math.max(-5000, Math.min(5000, deltaY)),
        deltaX: Math.max(-5000, Math.min(5000, deltaX)),
      };
    }
    if (type === 'wait') {
      const ms = Number(action.ms);
      if (!Number.isFinite(ms) || ms < 0 || ms > 5000) {
        throw new Error(`actions[${index}] wait must be from 0 to 5000 ms.`);
      }
      return { type, ms };
    }
    throw new Error(`actions[${index}] has unsupported type.`);
  });
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

    const interactive = interesting.slice(0, 800).map((node, index) => {
      const el = node as HTMLElement;
      const input = node as HTMLInputElement;
      const rect = el.getBoundingClientRect();
      return {
        index,
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

async function clickText(page: Page, text: string, occurrence: number, contains: boolean) {
  await enableFlutterSemantics(page);
  const point = await page.evaluate(({ wanted, ordinal, allowContains }) => {
    const roots: Array<Document | ShadowRoot> = [document];
    const nodes: Element[] = [];
    const targetText = wanted.trim().toLowerCase();

    while (roots.length) {
      const root = roots.shift()!;
      for (const node of Array.from(root.querySelectorAll('*'))) {
        nodes.push(node);
        const shadow = (node as HTMLElement).shadowRoot;
        if (shadow) roots.push(shadow);
      }
    }

    const matches = nodes.filter((node) => {
      if (!node.tagName.toLowerCase().startsWith('flt-semantics')) return false;
      const value = ((node as HTMLElement).innerText || node.textContent || '').trim().toLowerCase();
      return allowContains ? value.includes(targetText) : value === targetText;
    });
    const target = matches[ordinal] as HTMLElement | undefined;
    if (!target) return null;
    const rect = target.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return null;
    return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
  }, { wanted: text, ordinal: occurrence, allowContains: contains });

  if (!point) throw new Error(`Could not find visible Flutter semantic text: ${text}`);
  await page.mouse.click(point.x, point.y);
  return point;
}

async function performActions(page: Page, actions: BrowserAction[]) {
  const results: Array<Record<string, unknown>> = [];
  for (let index = 0; index < actions.length; index += 1) {
    const action = actions[index];
    if (action.type === 'click') {
      await page.mouse.click(action.x, action.y);
      results.push({ index, type: action.type, x: action.x, y: action.y, finalUrl: page.url() });
    } else if (action.type === 'clickText') {
      const point = await clickText(page, action.text, action.occurrence ?? 0, action.contains === true);
      results.push({ index, type: action.type, text: action.text, occurrence: action.occurrence ?? 0, ...point, finalUrl: page.url() });
    } else if (action.type === 'type') {
      await page.keyboard.type(action.text, { delay: action.delay ?? 0 });
      results.push({ index, type: action.type, characterCount: action.text.length, finalUrl: page.url() });
    } else if (action.type === 'press') {
      await page.keyboard.press(action.key as any);
      results.push({ index, type: action.type, key: action.key, finalUrl: page.url() });
    } else if (action.type === 'scroll') {
      await page.mouse.move(720, 550);
      await page.mouse.wheel({ deltaX: action.deltaX ?? 0, deltaY: action.deltaY });
      results.push({ index, type: action.type, deltaX: action.deltaX ?? 0, deltaY: action.deltaY, finalUrl: page.url() });
    } else {
      await new Promise(resolve => setTimeout(resolve, action.ms));
      results.push({ index, type: action.type, ms: action.ms, finalUrl: page.url() });
    }
    if (action.type !== 'wait') await new Promise(resolve => setTimeout(resolve, 350));
  }
  return results;
}

async function screenshotDimensions(page: Page) {
  return page.evaluate(() => ({
    width: Math.max(document.documentElement.scrollWidth, document.body?.scrollWidth || 0, window.innerWidth),
    height: Math.max(document.documentElement.scrollHeight, document.body?.scrollHeight || 0, window.innerHeight),
  }));
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
  const legacyClickText = request.nextUrl.searchParams.get('click')?.trim() || '';
  const grant = request.nextUrl.searchParams.get('grant')?.trim() || '';
  const oidc = request.headers.get('x-vercel-oidc-token')?.trim()
    || process.env.VERCEL_OIDC_TOKEN?.trim()
    || '';
  const consoleErrors: string[] = [];
  const requestFailures: Array<{ url: string; error: string }> = [];
  let browser: Browser | undefined;

  try {
    const engineeringSession = await exchangeEngineeringSession(grant, oidc);
    const actions = mode === 'interact' ? parseActions(request) : [];
    if (mode === 'interact' && !engineeringSession) {
      return NextResponse.json({ ok: false, error: 'Authenticated engineering session required for interaction mode.' }, { status: 401, headers: { 'cache-control': 'no-store' } });
    }

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

    let legacyAction: Record<string, unknown> | null = null;
    if (legacyClickText) {
      const point = await clickText(page, legacyClickText, 0, true);
      await new Promise(resolve => setTimeout(resolve, 900));
      legacyAction = { clicked: true, text: legacyClickText, ...point, finalUrl: page.url() };
    }

    if (mode === 'interact') {
      const actionResults = await performActions(page, actions);
      const snapshot = await captureSnapshot(page);
      return NextResponse.json({ ok: true, authenticatedEngineeringSession: true, requestedUrl: target.toString(), finalUrl: page.url(), status: response?.status() ?? null, action: legacyAction, actions: actionResults, snapshot, consoleErrors: consoleErrors.slice(0, 100), requestFailures: requestFailures.slice(0, 100), capturedAt: new Date().toISOString() }, { headers: { 'cache-control': 'no-store' } });
    }

    if (mode === 'screenshot' || mode === 'screenshot-json') {
      const png = await page.screenshot({ fullPage: true, type: 'png' });
      if (mode === 'screenshot-json') {
        return NextResponse.json({ ok: true, authenticatedEngineeringSession: !!engineeringSession, requestedUrl: target.toString(), finalUrl: page.url(), status: response?.status() ?? null, action: legacyAction, screenshotBase64: Buffer.from(png).toString('base64'), consoleErrors: consoleErrors.slice(0, 100), requestFailures: requestFailures.slice(0, 100), capturedAt: new Date().toISOString() }, { headers: { 'cache-control': 'no-store' } });
      }
      return new NextResponse(Buffer.from(png), { status: 200, headers: { 'content-type': 'image/png', 'cache-control': 'no-store', 'x-circa-browser-url': page.url() } });
    }

    if (mode === 'screenshot-chunk') {
      const quality = clampInteger(request.nextUrl.searchParams.get('quality'), 65, 30, 90);
      const chunkSize = clampInteger(request.nextUrl.searchParams.get('chunkSize'), 50000, 8000, 60000);
      const chunkIndex = clampInteger(request.nextUrl.searchParams.get('chunk'), 0, 0, 10000);
      const jpeg = await page.screenshot({ fullPage: true, type: 'jpeg', quality });
      const buffer = Buffer.from(jpeg);
      const base64 = buffer.toString('base64');
      const totalChunks = Math.max(1, Math.ceil(base64.length / chunkSize));
      if (chunkIndex >= totalChunks) {
        return NextResponse.json({ ok: false, error: 'Requested screenshot chunk is out of range.', chunkIndex, totalChunks }, { status: 416, headers: { 'cache-control': 'no-store' } });
      }
      const dimensions = await screenshotDimensions(page);
      return NextResponse.json({
        ok: true,
        authenticatedEngineeringSession: !!engineeringSession,
        requestedUrl: target.toString(),
        finalUrl: page.url(),
        status: response?.status() ?? null,
        action: legacyAction,
        mimeType: 'image/jpeg',
        quality,
        dimensions,
        byteLength: buffer.length,
        sha256: createHash('sha256').update(buffer).digest('hex'),
        base64Length: base64.length,
        chunkSize,
        chunkIndex,
        totalChunks,
        screenshotBase64Chunk: base64.slice(chunkIndex * chunkSize, (chunkIndex + 1) * chunkSize),
        consoleErrors: consoleErrors.slice(0, 100),
        requestFailures: requestFailures.slice(0, 100),
        capturedAt: new Date().toISOString(),
      }, { headers: { 'cache-control': 'no-store' } });
    }

    const snapshot = await captureSnapshot(page);
    return NextResponse.json({ ok: true, authenticatedEngineeringSession: !!engineeringSession, requestedUrl: target.toString(), finalUrl: page.url(), status: response?.status() ?? null, action: legacyAction, snapshot, consoleErrors: consoleErrors.slice(0, 100), requestFailures: requestFailures.slice(0, 100), capturedAt: new Date().toISOString() }, { headers: { 'cache-control': 'no-store' } });
  } catch (error) {
    return NextResponse.json({ ok: false, requestedUrl: target.toString(), error: error instanceof Error ? error.message : String(error), consoleErrors: consoleErrors.slice(0, 100), requestFailures: requestFailures.slice(0, 100) }, { status: 500, headers: { 'cache-control': 'no-store' } });
  } finally {
    await browser?.close().catch(() => undefined);
  }
}
