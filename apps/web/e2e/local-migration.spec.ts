import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
const check = expect.configure({ timeout: 30_000 });

test('browser-local demo, search, source and version comparison use no API', async ({ page }, testInfo) => {
  test.setTimeout(180_000);
  page.setDefaultTimeout(30_000);
  const errors: string[] = [];
  const requests: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('request', (request) => requests.push(request.url()));

  await page.goto('./');
  const modeLabel = page.locator('.mode');
  await check(modeLabel).toHaveText('Локально в браузере');
  if (testInfo.project.name === 'mobile') await check(modeLabel).toBeHidden();
  else await check(modeLabel).toBeVisible();
  await check(page.locator('.cookie-notice')).toHaveCount(0);
  await page.getByRole('button', { name: 'Открыть демонстрацию', exact: true }).click();
  await check(page.getByRole('heading', { name: 'Что говорят документы?' })).toBeVisible();
  await page.getByRole('button', { name: 'Найти основания', exact: true }).click();
  await check(page.getByRole('heading', { name: 'Значения менялись между редакциями' })).toBeVisible();
  await check(page.locator('.hit blockquote').filter({ hasText: '3600' })).toBeVisible();
  await page.locator('.filters select').nth(1).selectOption('2.0');
  await page.getByRole('button', { name: 'Найти основания', exact: true }).click();
  await check(page.getByRole('heading', { name: 'Вывод по формальному правилу' })).toBeVisible();
  await page.locator('.formal-answer .source-link').click();
  await check(page.locator('.source-panel article.selected')).toContainText('3600');
  await page.getByRole('link', { name: 'Сравнение редакций', exact: true }).click();
  await page.getByRole('button', { name: 'Сравнить', exact: true }).click();
  await check(page.locator('.diff-new').filter({ hasText: '3600' })).toBeVisible();
  await page.getByRole('link', { name: 'Документы', exact: false }).click();
  await page.locator('.settings summary').click();
  await page.locator('.settings select').selectOption('research');
  await page.getByRole('button', { name: 'Найти основания', exact: true }).click();
  await check(page.locator('.research-trace')).toContainText('authored_exact_quote_rule');
  await check(page.locator('.research-trace')).toContainText('дословные цитаты проверены');
  await page.locator('.research-trace summary').click();
  const [traceDownload] = await Promise.all([
    page.waitForEvent('download', { timeout: 15_000 }),
    page.getByRole('button', { name: 'Скачать JSON-трассу' }).click(),
  ]);
  const trace = JSON.parse(await readFile((await traceDownload.path())!, 'utf8'));
  expect(trace.schema_version).toBe('research-rag-trace-v1');
  expect(trace.trace.length).toBeGreaterThan(0);

  const origin = new URL(page.url()).origin;
  expect(requests.filter((url) => new URL(url).origin !== origin)).toEqual([]);
  expect(requests.some((url) => new URL(url).pathname.startsWith('/api/'))).toBeFalsy();
  expect(errors).toEqual([]);
});

test('browser-local upload persists, searches and deletes without transmitting a marker', async ({ page }) => {
  test.setTimeout(180_000);
  page.setDefaultTimeout(30_000);
  const errors: string[] = [];
  const requests: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('request', (request) => requests.push(request.url()));

  await page.goto('./');
  await page.getByRole('button', { name: 'Загрузить документ', exact: true }).click();
  await page.locator('input[type=file]').setInputFiles({ name: 'private.md', mimeType: 'text/markdown', buffer: Buffer.from('# Инструкция\n\nУникальный маркер: сапфир721\nНапряжение: 12 вольт') });
  await page.locator('input[name=title]').fill('Личный документ');
  await page.getByRole('button', { name: 'Загрузить и обработать', exact: true }).click();
  await check(page.locator('.document-item')).toHaveCount(1, { timeout: 90_000 });
  await check(page.locator('.document-item')).toContainText('Личный документ');

  await page.reload();
  await check(page.locator('.document-item')).toHaveCount(1);
  await page.locator('#question').fill('сапфир721');
  await page.getByRole('button', { name: 'Найти основания', exact: true }).click();
  await check(page.locator('.hit blockquote')).toContainText('сапфир721');
  const [archiveDownload] = await Promise.all([
    page.waitForEvent('download', { timeout: 15_000 }),
    page.getByRole('button', { name: 'Экспортировать' }).click(),
  ]);
  const archivePath = (await archiveDownload.path())!;
  const archive = JSON.parse(await readFile(archivePath, 'utf8'));
  expect(archive.format).toBe('evidencerag-browser-workspace');
  expect(archive.documents).toHaveLength(1);
  expect(Buffer.from(archive.documents[0].original_b64, 'base64').toString()).toContain('сапфир721');
  page.once('dialog', (dialog) => dialog.accept());
  await page.getByRole('button', { name: 'Удалить Личный документ ', exact: false }).click();
  await check(page.locator('.document-item')).toHaveCount(0);
  page.once('dialog', (dialog) => dialog.accept());
  await page.locator('input[type=file][accept="application/json,.json"]').setInputFiles(archivePath);
  await check(page.locator('.document-item')).toHaveCount(1);
  await check(page.locator('.document-item')).toContainText('Личный документ');
  await page.locator('#question').fill('сапфир721');
  await page.getByRole('button', { name: 'Найти основания', exact: true }).click();
  await check(page.locator('.hit blockquote')).toContainText('сапфир721');

  const origin = new URL(page.url()).origin;
  expect(requests.filter((url) => new URL(url).origin !== origin)).toEqual([]);
  expect(requests.some((url) => new URL(url).pathname.startsWith('/api/'))).toBeFalsy();
  expect(errors).toEqual([]);
});

test('browser-local Python parser extracts DOCX tables and PDF pages, identifies scanned PDFs', async ({ page }) => {
  test.setTimeout(180_000);
  page.setDefaultTimeout(30_000);
  const fixtures = resolve(process.cwd(), '../../experiments/browser-migration-007/fixtures');
  await page.goto('./');

  const uploadFixture = async (filename: string, title: string, family: string) => {
    const open = page.getByRole('button', { name: 'Загрузить документ', exact: true });
    if (await open.count()) await open.click();
    else await page.getByRole('button', { name: 'Добавить документ', exact: true }).click();
    const buffer = await readFile(resolve(fixtures, filename));
    await page.locator('input[name=file]').setInputFiles({ name: filename, mimeType: 'application/octet-stream', buffer });
    await page.locator('input[name=title]').fill(title);
    await page.locator('input[name=family]').fill(family);
    await page.getByRole('button', { name: 'Загрузить и обработать', exact: true }).click();
  };

  await uploadFixture('table-heading.docx', 'Таблица DOCX', 'fixture-docx');
  await check(page.locator('.source-panel')).toContainText('Батарея 3600 мАч');
  await check(page.locator('.source-panel')).toContainText('USB | 5V');

  await uploadFixture('two-page.pdf', 'Двухстраничный PDF', 'fixture-pdf');
  await check(page.locator('.source-panel article')).toHaveCount(2);
  await check(page.locator('.source-panel')).toContainText('First battery page');
  await check(page.locator('.source-panel')).toContainText('Second charging page');

  await uploadFixture('scanned.pdf', 'PDF без текстового слоя', 'fixture-scan');
  await check(page.locator('.source-panel')).toContainText('В PDF нет текстового слоя');
  await expect(page.locator('.document-item')).toHaveCount(3);
});
