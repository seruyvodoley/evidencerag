import { test, expect } from '@playwright/test';

test('static project base path keeps navigation, reload and favicon local to the repository', async ({ page }) => {
  const errors: string[] = [];
  const missingAssets: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('response', (response) => {
    if (response.status() >= 400 && response.request().resourceType() !== 'document') {
      missingAssets.push(`${response.status()} ${response.url()}`);
    }
  });

  await page.goto('./');
  await expect(page.getByText('Локально в браузере')).toBeVisible();
  const brand = page.getByRole('link', { name: 'Основание, главная' });
  await expect(brand).toHaveAttribute('href', '/evidencerag/');
  const iconHref = await page.locator('link[rel="icon"][type="image/svg+xml"]').getAttribute('href');
  expect(iconHref).toBe('/evidencerag/favicon.svg');

  await page.getByRole('link', { name: 'Сравнение редакций', exact: true }).click();
  await expect(page).toHaveURL(/\/evidencerag\/compare$/);
  await expect(page.getByRole('heading', { name: 'Что изменилось в документе?' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Что изменилось в документе?' })).toBeVisible();
  expect(errors).toEqual([]);
  expect(missingAssets).toEqual([]);
});
