import { expect, type Page } from '@playwright/test';

export type UploadFile = { name: string; mimeType: string; buffer: Buffer };

export async function addQueuedFile(page: Page, file: UploadFile, metadata: { title?: string; family?: string; version?: string; date?: string } = {}) {
  const dialog = page.locator('dialog.upload-dialog').first();
  if (!await dialog.isVisible()) {
    const open = page.getByRole('button', { name: /Загрузить документ|Добавить документ/ }).first();
    await open.click();
  }
  await dialog.locator('input[name=files]').setInputFiles(file);
  const item = dialog.locator('.upload-item').last();
  await expect(item.locator('.upload-item-heading')).toContainText('Готов к добавлению', { timeout: 120_000 });
  const fill = async (label: string, value?: string) => {
    if (value !== undefined) await item.locator('.upload-fields label').filter({ hasText: label }).locator('input').fill(value);
  };
  await fill('Название', metadata.title);
  await fill('Группа редакций', metadata.family);
  await fill('Версия', metadata.version);
  await fill('Действует с', metadata.date);
  await dialog.getByRole('button', { name: /^Добавить 1 документ$/ }).click();
}

export async function clearUploadQueue(page: Page) {
  const dialog = page.locator('dialog.upload-dialog').first();
  if (await dialog.isVisible() && await dialog.locator('.upload-item').count()) {
    await dialog.getByRole('button', { name: 'Очистить очередь' }).click();
  }
}
