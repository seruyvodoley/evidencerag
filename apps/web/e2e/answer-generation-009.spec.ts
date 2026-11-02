import { test, expect } from '@playwright/test';

const QUESTION = 'Какие требования к итоговой работе по практикуму «Причастный оборот» действуют? Сколько предложений требуется, сколько минут даётся и в каком виде сдаётся работа?';

test('browser-local answer combines versioned facts and a separately grouped partial amendment', async ({ page }, testInfo) => {
  test.setTimeout(240_000);
  page.setDefaultTimeout(45_000);
  const errors: string[] = [];
  const requests: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => requests.push(request.url()));
  await page.goto('./');
  await page.getByRole('navigation', {name:'Главная навигация'}).getByRole('link', {name:'Документы', exact:false}).click();

  const documents = [
    {title:'Практикум 2025', family:'Синтаксис-ИФиЯК', version:'2025', date:'2025-09-01', text:'Итоговая работа содержит 6 предложений. На выполнение отводится 15 минут. Работа сдаётся на бумаге.'},
    {title:'Практикум 2026', family:'Синтаксис-ИФиЯК', version:'2026', date:'2026-09-01', text:'Итоговая работа содержит 8 предложений. На выполнение отводится 20 минут. Работа сдаётся в электронном виде.'},
    {title:'Поправка 2026', family:'Синтаксис-ИФиЯК-Поправки', version:'2026', date:'2026-10-15', text:'С 15 октября 2026 года в редакции от 1 сентября 2026 года время выполнения изменено: вместо 20 минут устанавливается 25 минут. Остальные положения не отменяются.'},
  ];
  const uploadDocument = async (document:any, index:number) => {
    const open = page.getByRole('button', {name:'Добавить документ'});
    await open.click();
    await page.locator('input[name=file]').setInputFiles({name:`stage009-${index}.txt`,mimeType:'text/plain',buffer:Buffer.from(document.text)});
    await page.locator('input[name=title]').fill(document.title);
    await page.locator('input[name=family]').fill(document.family);
    await page.locator('input[name=version]').fill(document.version);
    await page.locator('input[name=date]').fill(document.date);
    await page.getByRole('button', {name:'Загрузить и обработать'}).click();
    await expect(page.locator('.document-item')).toHaveCount(index + 1, {timeout:90_000});
  };
  for (const [index, document] of documents.entries()) {
    await uploadDocument(document, index);
  }
  await page.locator('#question').fill(QUESTION);
  await page.locator('.filters select').first().selectOption({label:'Синтаксис-ИФиЯК'});
  await page.locator('.filters input[type=date]').fill('2026-10-31');
  await page.locator('.settings summary').click();
  await page.locator('.settings select').selectOption('research');
  await page.getByRole('button', {name:'Найти основания'}).click();
  await expect(page.locator('.verified-answer')).toContainText('8 предложений');
  await expect(page.locator('.verified-answer')).toContainText('25 минут');
  await expect(page.locator('.verified-answer')).toContainText('в электронном виде');
  await expect(page.locator('.answer-claim')).toHaveCount(3);
  await page.locator('.answer-claim').filter({hasText:'25 минут'}).getByRole('button', {name:'Открыть подтверждающий фрагмент'}).click();
  await expect(page.locator('.source-panel article.selected')).toContainText('25 минут');

  // B and C: temporal selection across the complete edition and its partial amendment.
  await page.locator('.filters input[type=date]').fill('2026-10-01');
  await page.getByRole('button', {name:'Найти основания'}).click();
  await expect(page.locator('.verified-answer')).toContainText('20 минут');
  await page.locator('.filters input[type=date]').fill('2025-10-01');
  await page.getByRole('button', {name:'Найти основания'}).click();
  await expect(page.locator('.verified-answer')).toContainText('6 предложений');
  await expect(page.locator('.verified-answer')).toContainText('15 минут');

  // D: a missing requested characteristic stays explicit, with partial facts visible.
  await page.locator('.filters input[type=date]').fill('2026-10-31');
  await page.locator('#question').fill(QUESTION + ' Сколько абзацев требуется?');
  await page.getByRole('button', {name:'Найти основания'}).click();
  await expect(page.locator('.verified-answer')).toHaveCount(0);
  await expect(page.locator('.missing-facts')).toContainText('count:абзац');
  await expect(page.locator('.partial-facts .answer-claim')).toHaveCount(3);

  // E: same-date competing amendments are refused instead of choosing one.
  await uploadDocument({title:'Поправка 2026 — конфликт',family:'Синтаксис-ИФиЯК-Поправки-2',version:'2026',date:'2026-10-15',text:'С 15 октября 2026 года в редакции от 1 сентября 2026 года время изменено: вместо 20 минут устанавливается 30 минут.'},3);
  await page.locator('#question').fill(QUESTION);
  await page.getByRole('button', {name:'Найти основания'}).click();
  await expect(page.getByRole('heading', {name:'Найдены конкурирующие действующие значения'})).toBeVisible();
  await expect(page.locator('.missing-facts')).toContainText('duration');

  // F: lexical paraphrases of a submission mode collapse to the same explicit category.
  await uploadDocument({title:'Цифровая сдача',family:'Парафраз',version:'1',date:'2026-09-01',text:'Работа принимается посредством цифровой системы сдачи.'},4);
  await page.locator('.filters select').first().selectOption({label:'Парафраз'});
  await page.locator('.filters input[type=date]').fill('2026-10-01');
  await page.locator('#question').fill('В каком виде принимается работа?');
  await page.getByRole('button', {name:'Найти основания'}).click();
  await expect(page.locator('.verified-answer')).toContainText('посредством цифровой системы сдачи');

  // H: an unrelated labelled field works with a distinct, dated technical family.
  await uploadDocument({title:'Терморегламент 1',family:'Терморегламент',version:'1',date:'2024-01-01',text:'Температура корпуса: 70 °C.'},5);
  await uploadDocument({title:'Терморегламент 2',family:'Терморегламент',version:'2',date:'2025-01-01',text:'Температура корпуса: 85 °C.'},6);
  await page.locator('.filters select').first().selectOption({label:'Терморегламент'});
  await page.locator('.filters input[type=date]').fill('2025-06-01');
  await page.locator('#question').fill('Какова температура оборудования?');
  await page.getByRole('button', {name:'Найти основания'}).click();
  await expect(page.locator('.verified-answer')).toContainText('85 °C');

  // I: question terms without a linked value do not become a fact.
  await uploadDocument({title:'Лексическая ловушка',family:'Лексическая ловушка',version:'1',date:'2026-01-01',text:'Минуты распределены по разделам. Документ описывает порядок сдачи работы, но не устанавливает длительность в минутах.'},7);
  await page.locator('.filters select').first().selectOption({label:'Лексическая ловушка'});
  await page.locator('#question').fill('Сколько минут даётся?');
  await page.getByRole('button', {name:'Найти основания'}).click();
  await expect(page.locator('.verified-answer')).toHaveCount(0);
  await expect(page.locator('.missing-facts')).toContainText('duration');

  // J: an unrecorded effective date cannot establish a current value.
  await uploadDocument({title:'Документ без даты',family:'Без даты',version:'1',date:'',text:'Итоговая работа содержит 9 предложений. На выполнение отводится 40 минут. Работа сдаётся на бумаге.'},8);
  await page.locator('.filters select').first().selectOption({label:'Без даты'});
  await page.locator('.filters input[type=date]').fill('2026-10-31');
  await page.locator('#question').fill(QUESTION);
  await page.getByRole('button', {name:'Найти основания'}).click();
  await expect(page.locator('.verified-answer')).toHaveCount(0);
  await expect(page.locator('.result-status')).toContainText('Не хватает подтверждений');
  if (testInfo.project.name === 'mobile') {
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  }
  const origin = new URL(page.url()).origin;
  expect(requests.filter(url => new URL(url).origin !== origin)).toEqual([]);
  expect(requests.some(url => new URL(url).pathname.startsWith('/api/'))).toBeFalsy();
  expect(errors).toEqual([]);
});
