import { test, expect } from '@playwright/test';
import { zipSync, strToU8 } from 'fflate';

test('Stage 011 ZIP queue, proposed metadata, amendment, correction and OPFS persistence', async ({ page }) => {
  test.setTimeout(300_000);
  page.setDefaultTimeout(60_000);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('./');
  await page.getByRole('button', { name: 'Загрузить документ', exact: true }).click();
  const texts = {
    'full-2025.md': '# Положение о зачёте по практикуму «Полевой корпус речи» 2025\n\nПолная редакция действует с 1 сентября 2025 года. Итоговый зачёт состоит из 6 аудиозаписей. Максимальная длительность каждой — не более 3 минут. Файлы принимаются в формате WAV. Срок сдачи — до 25 ноября 2025 года включительно.',
    'full-2026.md': '# Положение о зачёте по практикуму «Полевой корпус речи» 2026\n\nПолная редакция действует с 1 сентября 2026 года. Итоговый зачёт состоит из 9 аудиозаписей. Максимальная длительность каждой — не более 5 минут. Файлы принимаются в формате WAV. Срок сдачи — до 18 ноября 2026 года включительно.',
    'amendment.md': '# Поправка к положению о зачёте по практикуму «Полевой корпус речи» 2026\n\nПоправка действует с 20 октября 2026 года. В пункте 3 регламента 2026 года формат сдаваемых аудиофайлов изменён: вместо WAV необходимо предоставлять FLAC. В пункте 4 регламента 2026 года срок сдачи перенесён: вместо 18 ноября 2026 года комплект материалов принимается до 30 ноября 2026 года включительно. Пункты 1, 2, 5 и 6 полной редакции от 1 сентября 2026 года остаются без изменений.',
  };
  const archive = zipSync(Object.fromEntries(Object.entries(texts).map(([name, text]) => [name, strToU8(text)])));
  await page.locator('input[name=files]').setInputFiles({ name: 'speech-corpus.zip', mimeType: 'application/zip', buffer: Buffer.from(archive) });
  const dialog = page.locator('dialog.upload-dialog').first();
  await expect(dialog.locator('.upload-item')).toHaveCount(3);
  await expect(dialog.locator('.upload-item-heading').filter({ hasText: 'full-2025.md' })).toContainText('Готов к добавлению', { timeout: 120_000 });
  await expect(dialog.locator('.upload-item-heading').filter({ hasText: 'full-2026.md' })).toContainText('Готов к добавлению', { timeout: 120_000 });
  await expect(dialog.locator('.upload-item-heading').filter({ hasText: 'amendment.md' })).toContainText('Готов к добавлению', { timeout: 120_000 });
  await expect(dialog.locator('.upload-fields').nth(0).locator('input').nth(3)).toHaveValue('2025-09-01');
  await expect(dialog.locator('.upload-fields').nth(1).locator('input').nth(3)).toHaveValue('2026-09-01');
  await expect(dialog.locator('.upload-fields').nth(2).locator('input').nth(3)).toHaveValue('2026-10-20');
  await expect(dialog.getByText(/effective|document_heading_year|normalized_title_suggestion|explicit_effective_date/)).toBeVisible();
  await dialog.getByRole('button', { name: 'Добавить 3 документа', exact: true }).click();
  await expect(page.locator('.document-item')).toHaveCount(3, { timeout: 120_000 });
  await expect(page.locator('.document-item')).toContainText('2026-10-20');

  await page.locator('#question').fill('Какие требования действуют на 3 ноября 2026 года для итогового зачёта по практикуму «Полевой корпус речи»? Укажи количество аудиозаписей, максимальную длительность каждой, формат файлов и крайний срок сдачи. Приведи источники.');
  await page.locator('.filters input[type=date]').fill('2026-11-03');
  await page.locator('.settings summary').click();
  await page.locator('.settings select').selectOption('research');
  await page.getByRole('button', { name: 'Найти основания', exact: true }).click();
  await expect(page.locator('.verified-answer')).toContainText('9 аудиозаписей');
  await expect(page.locator('.verified-answer')).toContainText('не более 5 минут');
  await expect(page.locator('.verified-answer')).toContainText('FLAC');
  await expect(page.locator('.verified-answer')).toContainText('2026-11-30');
  await expect(page.locator('.verified-answer .answer-claim')).toHaveCount(4);

  const amendmentRow = page.locator('.document-item').filter({ hasText: 'Поправка к положению' });
  await amendmentRow.getByRole('button', { name: /Изменить сведения/ }).click();
  const editor = page.locator('dialog[open]').last();
  await editor.locator('label').filter({ hasText: 'Действует с' }).locator('input').fill('2026-11-04');
  await editor.getByRole('button', { name: 'Сохранить сведения' }).click();
  await page.locator('.filters input[type=date]').fill('2026-11-03');
  await page.getByRole('button', { name: 'Найти основания', exact: true }).click();
  await expect(page.locator('.verified-answer')).toContainText('WAV');
  await expect(page.locator('.verified-answer')).toContainText('2026-11-18');

  await page.locator('.document-item').filter({ hasText: 'Поправка к положению' }).getByRole('button', { name: /Изменить сведения/ }).click();
  const editorAgain = page.locator('dialog[open]').last();
  await editorAgain.locator('label').filter({ hasText: 'Действует с' }).locator('input').fill('2026-10-20');
  await editorAgain.getByRole('button', { name: 'Сохранить сведения' }).click();
  await page.locator('.filters input[type=date]').fill('2026-11-03');
  await page.getByRole('button', { name: 'Найти основания', exact: true }).click();
  await expect(page.locator('.verified-answer')).toContainText('FLAC');
  await page.reload();
  await expect(page.locator('.document-item')).toHaveCount(3);
  await page.locator('#question').fill('Какие требования действуют на 3 ноября 2026 года для итогового зачёта по практикуму «Полевой корпус речи»? Укажи количество аудиозаписей, максимальную длительность каждой, формат файлов и крайний срок сдачи. Приведи источники.');
  await page.locator('.filters input[type=date]').fill('2026-11-03');
  await page.locator('.settings summary').click();
  await page.locator('.settings select').selectOption('research');
  await page.getByRole('button', { name: 'Найти основания', exact: true }).click();
  await expect(page.locator('.verified-answer')).toContainText('FLAC');
  expect(errors).toEqual([]);
});
