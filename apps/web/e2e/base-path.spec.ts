import { test, expect } from '@playwright/test';

test('static project base path keeps navigation, reload and favicon local to the repository', async ({ page }, testInfo) => {
  const errors: string[] = [];
  const missingAssets: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('response', (response) => {
    if (response.status() >= 400 && response.request().resourceType() !== 'document') {
      missingAssets.push(`${response.status()} ${response.url()}`);
    }
  });

  await page.goto('./');
  const modeLabel = page.locator('.mode');
  await expect(modeLabel).toHaveText('Локально в браузере');
  if (testInfo.project.name === 'mobile') await expect(modeLabel).toBeHidden();
  else await expect(modeLabel).toBeVisible();
  const brand = page.getByRole('link', { name: 'Основание, главная' });
  await expect(brand).toHaveAttribute('href', '/evidencerag/');
  const iconHref = await page.locator('link[rel="icon"][type="image/svg+xml"]').getAttribute('href');
  expect(new URL(iconHref!, page.url()).pathname).toBe('/evidencerag/favicon.svg');

  await page.getByRole('link', { name: 'Сравнение редакций', exact: true }).click();
  await expect(page).toHaveURL(/\/evidencerag\/compare\/$/);
  await expect(page.getByRole('heading', { name: 'Что изменилось в документе?' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Что изменилось в документе?' })).toBeVisible();
  expect(errors).toEqual([]);
  expect(missingAssets).toEqual([]);
});
