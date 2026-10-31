import { test, expect } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const base = process.env.E2E_URL || 'https://seruyvodoley.gitverse.site/evidencerag/';
const artifactDir = resolve(process.cwd(), '../../experiments/final-audit-008');
const capturePrefix = process.env.E2E_CAPTURE_PREFIX || (new URL(base).hostname === '127.0.0.1' ? 'preview' : 'public');
const check = expect.configure({ timeout: 45_000 });

test('published route matrix, static assets, CSP and mobile viewport', async ({ page }, testInfo) => {
  const pageErrors: string[] = [];
  const localStaticMount = new URL(base).hostname === '127.0.0.1';
  const consoleErrors: string[] = [];
  const failedRequests: string[] = [];
  const responses: Array<{ url: string; status: number; resourceType: string; contentType: string | null; contentLength: number | null; setsCookie: boolean }> = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error' && !(localStaticMount && /404 \(Not Found\)/.test(message.text()))) consoleErrors.push(message.text());
  });
  page.on('requestfailed', request => failedRequests.push(`${request.failure()?.errorText}: ${request.url()}`));
  page.on('response', response => responses.push({
    url: response.url(), status: response.status(), resourceType: response.request().resourceType(), contentType: response.headers()['content-type'] || null,
    contentLength: Number(response.headers()['content-length']) || null,
    setsCookie: Boolean(response.headers()['set-cookie']),
  }));

  const routes = [
    { path: '', title: 'Основание — ответы начинаются с источников' },
    { path: 'documents/', title: 'Работа с документами — Основание' },
    { path: 'compare/', title: 'Сравнение редакций — Основание' },
    { path: 'method/', title: 'Метод и ограничения — Основание' },
    { path: 'cookies/', title: 'Политика cookie — Основание' },
  ];
  const routeStatuses: Array<{ route: string; status: number | null }> = [];
  for (const route of routes) {
    const response = await page.goto(new URL(route.path, base).href);
    routeStatuses.push({ route: route.path || '/', status: response?.status() ?? null });
    await expect(page.locator('main')).toBeVisible();
    await expect(page).toHaveTitle(route.title);
  }

  await page.goto(base);
  await page.getByRole('link', { name: 'Cookie', exact: true }).click();
  await expect(page.getByText(/GitVerse технически получает IP-адрес/)).toBeVisible();
  await page.goto(base);
  await page.getByRole('button', { name: 'Открыть демонстрацию', exact: true }).click();
  await check(page.getByRole('heading', { name: 'Что говорят документы?' })).toBeVisible();
  await page.getByRole('button', { name: 'Найти основания', exact: true }).click();
  await check(page.getByRole('heading', { name: 'Значения менялись между редакциями' })).toBeVisible();
  const metaCsp = await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute('content');
  const icons = await page.locator('link[rel~="icon"], link[rel="apple-touch-icon"]').evaluateAll(items =>
    items.map(item => (item as HTMLLinkElement).href));
  const browserStorage = await page.evaluate(() => ({
    cookies: document.cookie,
    localStorageEntries: localStorage.length,
    sessionStorageEntries: sessionStorage.length,
    evidenceSessionCookie: document.cookie.split(';').some(item => item.trim().startsWith('evidence_session=')),
  }));
  const resourceSnapshot = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
    return {
      domContentLoadedMs: nav.domContentLoadedEventEnd,
      loadEventMs: nav.loadEventEnd,
      transferBytes: resources.reduce((sum, item) => sum + item.transferSize, 0),
      resources: resources.map(item => ({ name: item.name, durationMs: item.duration, transferSize: item.transferSize })),
      viewport: { width: innerWidth, height: innerHeight, documentWidth: document.documentElement.scrollWidth },
    };
  });
  await mkdir(artifactDir, { recursive: true });
  await page.screenshot({ path: resolve(artifactDir, `${capturePrefix}-home-${testInfo.project.name}-default.png`), fullPage: true });
  await page.setViewportSize({ width: 320, height: 800 });
  const mobileWidth = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
  const outgoingOrigins = [...new Set(responses.map(item => new URL(item.url).origin))];
  expect(outgoingOrigins).toEqual([new URL(base).origin]);
  expect(responses.filter(item => item.status >= 400 && item.resourceType !== 'document')).toEqual([]);
  expect(routeStatuses.every(item => item.status === (localStaticMount && item.route !== '/' ? 404 : 200))).toBeTruthy();
  expect(responses.some(item => item.setsCookie)).toBeFalsy();
  expect(responses.some(item => item.url.endsWith('.wasm') && item.contentType?.includes('application/wasm'))).toBeTruthy();
  expect(icons.length).toBeGreaterThanOrEqual(3);
  expect(icons.every(icon => new URL(icon).pathname.startsWith('/evidencerag/'))).toBeTruthy();
  expect(metaCsp).toContain("default-src 'self'");
  expect(browserStorage.evidenceSessionCookie).toBeFalsy();
  expect(browserStorage.localStorageEntries).toBe(0);
  expect(browserStorage.sessionStorageEntries).toBe(0);
  expect(mobileWidth.document).toBeLessThanOrEqual(mobileWidth.viewport);
  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
  expect(failedRequests).toEqual([]);

  await page.screenshot({ path: resolve(artifactDir, `${capturePrefix}-home-${testInfo.project.name}-320.png`), fullPage: true });
  await writeFile(resolve(artifactDir, `browser-metrics-${capturePrefix}-${testInfo.project.name}.json`), JSON.stringify({
    project: testInfo.project.name, routes: routeStatuses, metaCsp, icons,
    outgoingOrigins, responses, totalResponseBytes: responses.reduce((sum, item) => sum + (item.contentLength || 0), 0),
    browserStorage, pageErrors, consoleErrors, failedRequests,
    initialLoad: resourceSnapshot, mobile320: mobileWidth,
  }, null, 2));
});

test('browser reproduces the stage-006 version-directed second retrieval', async ({ page }) => {
  test.setTimeout(180_000);
  page.setDefaultTimeout(45_000);
  await page.goto(base);
  await page.getByRole('button', { name: /Правила мастерской «Контур»/ }).click();
  await check(page.getByRole('heading', { name: 'Что говорят документы?' })).toBeVisible();
  await page.locator('#question').fill('Какой срок возврата после изменений?');
  await page.locator('.settings summary').click();
  await page.locator('.settings select').selectOption('research');
  await page.getByRole('button', { name: 'Найти основания', exact: true }).click();
  await check(page.locator('.research-trace')).toContainText('дословные цитаты проверены');
  await page.locator('.research-trace summary').click();
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Скачать JSON-трассу' }).click(),
  ]);
  const { readFile } = await import('node:fs/promises');
  const trace = JSON.parse(await readFile((await download.path())!, 'utf8'));
  expect(trace.strategy).toBe('sufficiency_gap_controller_v1');
  expect(trace.trace.length).toBeGreaterThanOrEqual(2);
  expect(trace.trace[0].action).toBe('check_version');
  expect(trace.trace[0].assessment.status).toBe('insufficient');
  expect(trace.trace[1].action).toBe('stop_sufficient');
  expect(trace.trace[1].new_evidence_claim_count).toBe(1);
  expect(trace.trace[1].selected_evidence_ids).not.toEqual(trace.trace[0].selected_evidence_ids);
  expect(trace.answer.claims[0].citations[0].quote).toBe('Срок возврата: 30 дней');
  await mkdir(artifactDir, { recursive: true });
  await writeFile(resolve(artifactDir, `stage-006-browser-trace-${capturePrefix}.json`), JSON.stringify(trace, null, 2));
});

test('local processing and privacy survive disabling network after core assets are warmed', async ({ page, context }, testInfo) => {
  test.setTimeout(240_000);
  page.setDefaultTimeout(45_000);
  const requests: string[] = [];
  const responses: Array<{ url: string; status: number; contentType: string | null; contentLength: number | null; setsCookie: boolean }> = [];
  const pageErrors: string[] = [];
  const workers: string[] = [];
  page.on('request', request => requests.push(request.url()));
  page.on('response', response => responses.push({
    url: response.url(), status: response.status(), contentType: response.headers()['content-type'] || null,
    contentLength: Number(response.headers()['content-length']) || null,
    setsCookie: Boolean(response.headers()['set-cookie']),
  }));
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('worker', worker => workers.push(worker.url()));

  await page.goto(base);
  const runtimeStart = Date.now();
  await page.getByRole('button', { name: 'Открыть демонстрацию', exact: true }).click();
  await check(page.getByRole('heading', { name: 'Что говорят документы?' })).toBeVisible();
  await page.getByRole('button', { name: 'Найти основания', exact: true }).click();
  await check(page.getByRole('heading', { name: 'Значения менялись между редакциями' })).toBeVisible();
  const runtimeReadyMs = Date.now() - runtimeStart;
  await expect.poll(() => workers.length).toBeGreaterThan(0);
  expect(requests.some(url => url.endsWith('.wasm'))).toBeTruthy();

  await context.setOffline(true);
  await page.getByRole('button', { name: /^(Загрузить документ|Добавить документ)$/ }).click();
  await page.locator('input[name=file]').setInputFiles({
    name: 'offline-check.txt', mimeType: 'text/plain',
    buffer: Buffer.from('Эксплуатация. Private marker: offlinecitrine. Service interval: twelve months.'),
  });
  await page.locator('input[name=title]').fill('Offline acceptance');
  const uploadStart = Date.now();
  await page.getByRole('button', { name: 'Загрузить и обработать', exact: true }).click();
  await check(page.locator('.document-item').filter({ hasText: 'Offline acceptance' })).toBeVisible({ timeout: 90_000 });
  const uploadMs = Date.now() - uploadStart;
  await page.getByLabel('Набор').selectOption({ label: 'Все документы' });
  await page.locator('#question').fill('offlinecitrine');
  const searchStart = Date.now();
  await page.getByRole('button', { name: 'Найти основания', exact: true }).click();
  await expect(page.locator('.hit blockquote')).toContainText('offlinecitrine');
  const searchMs = Date.now() - searchStart;

  expect(requests.some(url => new URL(url).pathname.startsWith('/api/'))).toBeFalsy();
  expect(requests.filter(url => new URL(url).origin !== new URL(base).origin)).toEqual([]);
  expect(requests.some(url => url.includes('offlinecitrine'))).toBeFalsy();
  expect(pageErrors).toEqual([]);

  await page.getByRole('button', { name: 'Добавить документ', exact: true }).click();
  await page.locator('input[name=file]').setInputFiles({
    name: 'damaged.pdf', mimeType: 'application/pdf', buffer: Buffer.from('not a PDF'),
  });
  await page.locator('input[name=title]').fill('Повреждённый файл');
  await page.getByRole('button', { name: 'Загрузить и обработать', exact: true }).click();
  await check(page.locator('dialog[open] [role="alert"]')).toContainText('Некорректная сигнатура PDF');
  expect(await page.locator('.document-item').count()).toBe(3);

  await page.locator('input[name=file]').setInputFiles({
    name: 'oversized.txt', mimeType: 'text/plain', buffer: Buffer.alloc(10_000_001, 65),
  });
  await page.locator('input[name=title]').fill('Слишком большой файл');
  await page.getByRole('button', { name: 'Загрузить и обработать', exact: true }).click();
  await check(page.locator('dialog[open] [role="alert"]')).toContainText('Файл должен быть не больше 10 МБ');
  expect(await page.locator('.document-item').count()).toBe(3);
  await mkdir(artifactDir, { recursive: true });
  await writeFile(resolve(artifactDir, `offline-browser-check-${capturePrefix}-${testInfo.project.name}.json`), JSON.stringify({
    status: 'passed', runtimeReadyMs, uploadMs, searchMs, offline: true,
    workerUrls: workers,
    requestUrls: requests.map(url => {
      const parsed = new URL(url);
      return `${parsed.origin}${parsed.pathname}`;
    }),
    responses, pageErrors,
  }, null, 2));
  await context.setOffline(false);
});
