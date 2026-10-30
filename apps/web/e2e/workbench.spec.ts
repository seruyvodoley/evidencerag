import {test,expect} from '@playwright/test';

test('demo search, version rule, source and comparison',async({page})=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  await page.getByRole('button',{name:'Открыть демонстрацию',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Что говорят документы?'})).toBeVisible();
  await page.getByRole('button',{name:'Найти основания',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Значения менялись между редакциями'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Изменения между редакциями'})).toBeVisible();
  await expect(page.locator('.hit blockquote').filter({hasText:'3600'})).toBeVisible();
  await page.locator('.filters select').nth(1).selectOption('2.0');
  await page.getByRole('button',{name:'Найти основания',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Вывод по формальному правилу'})).toBeVisible();
  await page.locator('.formal-answer .source-link').click();
  await expect(page.locator('.source-panel article.selected')).toContainText('3600');
  await expect(page.getByRole('link',{name:/Скачать оригинал/})).toHaveAttribute('href',/\/api\/documents\/.*\/original/);
  await page.getByRole('link',{name:'Сравнение редакций',exact:true}).click();
  await page.getByRole('button',{name:'Сравнить',exact:true}).click();
  await expect(page.locator('.diff-new').filter({hasText:'3600'})).toBeVisible();
  expect(errors).toEqual([]);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});

test('upload real file, find contents, delete and empty results',async({page})=>{
  await page.goto('/');await page.getByRole('button',{name:'Загрузить документ',exact:true}).click();
  await page.locator('input[type=file]').setInputFiles({name:'private.md',mimeType:'text/markdown',buffer:Buffer.from('# Инструкция\n\nУникальный маркер: сапфир721\nНапряжение: 12 вольт')});
  await page.locator('input[name=title]').fill('Личный документ');
  await page.getByRole('button',{name:'Загрузить и обработать',exact:true}).click();
  await expect(page.locator('.document-item')).toHaveCount(1);
  await page.locator('#question').fill('сапфир721');
  await page.getByRole('button',{name:'Найти основания',exact:true}).click();
  await expect(page.locator('.hit blockquote')).toContainText('сапфир721');
  page.once('dialog',d=>d.accept());
  await page.getByRole('button',{name:'Удалить Личный документ ',exact:false}).click();
  await expect(page.locator('.document-item')).toHaveCount(0);
  await page.getByRole('button',{name:'Найти основания',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Подходящих фрагментов не найдено'})).toBeVisible();
});

test('missing information is not confirmed and layout fits',async({page})=>{
  await page.goto('/');await page.getByRole('button',{name:'Открыть демонстрацию',exact:true}).click();
  await page.getByRole('button',{name:'Сколько стоит замена дисплея?',exact:true}).click();
  await expect(page.locator('.result-status')).toBeVisible();
  await expect(page.locator('.formal-answer')).toHaveCount(0);
  for(const width of [320,390,768,1280]){
    await page.setViewportSize({width,height:844});
    expect(await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}))).toEqual({width,scroll:width});
  }
});


test('page links, direct addresses, reload, history and new tab',async({page,context})=>{
  await page.goto('/');
  const navigation=page.getByRole('navigation',{name:'Главная навигация'});
  await navigation.getByRole('link',{name:'О методе',exact:true}).click();
  await expect(page).toHaveURL(/\/method$/);
  await expect(page.getByRole('heading',{name:/Проверяемость начинается/})).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading',{name:/Проверяемость начинается/})).toBeVisible();
  await navigation.getByRole('link',{name:'Документы',exact:false}).click();
  await expect(page).toHaveURL(/\/documents$/);
  await expect(page.getByRole('heading',{name:'Что говорят документы?'})).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(/\/method$/);
  await expect(page.getByRole('heading',{name:/Проверяемость начинается/})).toBeVisible();
  await page.goForward();
  await expect(page).toHaveURL(/\/documents$/);
  await navigation.getByRole('link',{name:'Сравнение редакций',exact:true}).click();
  await expect(page).toHaveURL(/\/compare$/);
  await expect(page.getByRole('heading',{name:'Что изменилось в документе?'})).toBeVisible();
  const extra=await context.newPage();await extra.goto('/compare');
  await expect(extra.getByRole('heading',{name:'Что изменилось в документе?'})).toBeVisible();
  await extra.close();
  await page.getByRole('link',{name:'Основание, главная',exact:true}).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading',{name:/У каждого вывода/})).toBeVisible();
});
