> Исторический снимок этапа 007. Последующее live-развёртывание и приёмка этапа 008 описаны в [FINAL_BROWSER_AUDIT_008.md](FINAL_BROWSER_AUDIT_008.md); данный документ фиксирует состояние до публикации Stage 008.

# Python ↔ browser parity — этап 007

Обновлено: 31.10.2026. Контракт проверки состоит из узкого исполняемого synthetic probe в CPython/Pyodide и product Chromium E2E. **Полная эквивалентность всего приложения пока не установлена.**

## Повторить parity probe

```sh
npm ci --prefix experiments/browser-migration-007
npm run audit --prefix experiments/browser-migration-007
```

Один и тот же `probe.py` запускается под CPython и Pyodide. Действующие parser, morphology, retrieval, store и research controller загружаются в Pyodide; для SQLite используется официальный SQLite WASM 3.54.1 через DB-API bridge. Текст, IDs, структуры, статусы, порядок и trace actions сравниваются точно; для FTS BM25 задан абсолютный допуск `1e-18`.

## Фактический результат

- Pyodide `314.0.7`; SQLite WASM и native SQLite в окружении: `3.54.1`.
- `parser_morphology_controller_parity: true`.
- Markdown, DOCX с заголовком/таблицей, текстовый двухстраничный PDF, PDF без текстового слоя (`needs_ocr`) совпали в synthetic fixtures.
- Русская морфология, stable evidence IDs, adaptive-k cutoff, version signal, authored exact-quote controller и trace совпали.
- FTS5 retrieval по двум редакциям работает. Max BM25 absolute score delta `2.117582368135751e-22`, tolerance `1e-18`.
- FTS5 `secure-delete` доступен в SQLite WASM; результат сохранён в [`hybrid-parity.json`](../experiments/browser-migration-007/hybrid-parity.json).

## Product browser verification

Команда из `apps/web/`:

```sh
E2E_URL=http://127.0.0.1:5173 E2E_BROWSER_CHANNEL=chromium npx playwright test e2e/local-migration.spec.ts --project=desktop
```

Результат: **4/4 passed** на Chromium 156 desktop против production bundle, смонтированного под `/evidencerag/`. Проверены base-path URLs, favicon, client navigation и direct-route reload через `404.html`; демо/search/source/version compare/research JSON trace; пользовательский файл сохраняется через reload, ищется, экспортируется, удаляется, импортируется и снова ищется; DOCX table, два PDF page и scan handling. Assertions запрещают cross-origin requests, `/api/*`, отсутствующие assets и page errors. Отчёт с точными fixtures и временами — [`product-e2e-subpath-results.json`](../experiments/browser-migration-007/product-e2e-subpath-results.json).

Отдельный Chromium OPFS smoke в [`browser-opfs-e2e.json`](../experiments/browser-migration-007/browser-opfs-e2e.json) подтвердил SQLite WASM 3.54.1, `secureDelete`, состояние после restart Worker и отсутствие строк после удаления.

## Ограничения

- Synthetic corpus мал; он не покрывает все исходные API contracts, крайние случаи, datasets и экспериментальные ablations.
- Product E2E проверяет UI-контракты, а не побайтовое/структурное сравнение каждого ответа продукта между Python server и браузером.
- Нет large-corpus, конкурентного исполнения, crash recovery, quota, damaged-store/archive parity, wide morphology corpus или budget stress test.
- BM25 tolerance подтверждён на одном сравнении, а не в генеральном наборе запросов.
- Browser тест — один desktop Chromium; Firefox, реальные Safari/iOS и Android не проходили.
- Встроенную SQLite Pyodide не использует продукт: она сообщает 3.39.0 и не проходит требуемую `secure-delete` команду FTS5. Используется SQLite WASM 3.54.1.

Не трактовать успешный probe как доказательство semantic quality, ответной точности, научного превосходства или полной миграции.
