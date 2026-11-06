import { test, expect } from '@playwright/test';
import { addQueuedFile } from './upload-helper';

const QUESTION = 'Какие требования действуют на 3 ноября 2026 года для итогового зачёта по практикуму «Полевой корпус речи»? Укажи количество аудиозаписей, максимальную длительность каждой, формат файлов и крайний срок сдачи. Приведи источники.';

test('browser-local research extracts four facts and applies a cross-family partial amendment', async ({ page }, testInfo) => {
  test.setTimeout(240_000);
  page.setDefaultTimeout(45_000);
  const errors: string[] = [];
  const requests: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => requests.push(request.url()));
  await page.goto('./');
  await page.getByRole('navigation', {name:'Главная навигация'}).getByRole('link', {name:'Документы', exact:false}).click();

  const documents = [
    {title:'Положение о зачёте по практикуму «Полевой корпус речи»', family:'speech-corpus', version:'2025', date:'2025-09-01', text:'4.1 Итоговый зачёт состоит из семи аудиозаписей. Максимальная длительность каждой — не более четырёх минут. 4.2 Файлы принимаются в формате WAV. Срок сдачи — до 30 ноября 2025 года включительно.'},
    {title:'Положение о зачёте по практикуму «Полевой корпус речи»', family:'speech-corpus', version:'2026', date:'2026-09-01', text:'4.1 Итоговый зачёт состоит из девяти аудиозаписей. Максимальная длительность каждой — не более пяти минут. 4.2 Файлы принимаются в формате WAV. Срок сдачи — до 15 ноября 2026 года включительно.'},
    {title:'Поправка к положению о Полевом корпусе речи', family:'speech-corpus-amendment', version:'2026-10', date:'2026-10-20', text:'Поправка к Положение о зачёте по практикуму «Полевой корпус речи». В редакции от 1 сентября 2026 года пункт 4.2 изменить: формат файлов установить FLAC; срок сдачи установить до 30 ноября 2026 года включительно.'},
  ];
  for (const [index, document] of documents.entries()) {
    await addQueuedFile(page,{name:`stage010-${index}.txt`,mimeType:'text/plain',buffer:Buffer.from(document.text)},document);
    await expect(page.locator('.document-item')).toHaveCount(index + 1, {timeout:90_000});
  }

  await page.locator('#question').fill(QUESTION);
  await page.locator('.settings summary').click();
  await page.locator('.settings select').selectOption('research');
  await page.getByRole('button', {name:'Найти основания'}).click();
  await expect(page.locator('.verified-answer')).toContainText('9 аудиозаписей');
  await expect(page.locator('.verified-answer')).toContainText('не более 5 минут');
  await expect(page.locator('.verified-answer')).toContainText('FLAC');
  await expect(page.locator('.verified-answer')).toContainText('2026-11-30');
  await expect(page.locator('.verified-answer .answer-claim')).toHaveCount(4);
  await expect(page.locator('.applied-amendments')).toContainText('Применённые поправки');
  await expect(page.locator('.hit').filter({hasText:'Поправка к положению о Полевом корпусе речи'})).toBeVisible();

  const origin = new URL(page.url()).origin;
  expect(requests.filter(url => new URL(url).origin !== origin)).toEqual([]);
  expect(errors).toEqual([]);
  if (testInfo.project.name === 'mobile') expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
});
