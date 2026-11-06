# Проверки и результаты

## Stage 011 — incomplete acceptance (03.11.2026)

- `.venv/bin/pytest -q`: **98 passed**, 1 existing Starlette/httpx deprecation warning.
- `npm run check`: **0 errors, 0 warnings**; `npm run build:local`: succeeded.
- Manual Chromium production preview opened the new dialog and found three entries in a test ZIP. Pyodide initialization remained pending during observation; end-to-end import, indexing, answer/citations and refresh persistence are unverified.
- Production mobile viewport, malicious ZIP cases and the full amendment negative matrix are not verified. No source commit or Pages artifact was published because Stage 011 key browser acceptance did not pass.
- Local CPython synthetic Markdown microprofile (median of 3 runs): 1/3/20 files total parse+metadata+batch-index **2.86/4.62/20.29 ms**. Not a browser/PDF/DOCX performance result.
- Reports: `STAGE_011_AUDIT.md`, `STAGE_011_VERSION_FIX.md`, `STAGE_011_IMPORT_UX.md`, `STAGE_011_EVALUATION.md`.

## Этап 010 (03.11.2026)

- Новые typed claim regressions: `tests/test_stage010_claim_pipeline.py` — авторские synthetic tests, не внешний benchmark. Контрольный browser case загружает три документа, получает четыре атрибутированных утверждения и проверяет цитаты/поправку: `apps/web/e2e/answer-generation-010.spec.ts`.
- `.venv/bin/pytest -q`: **84 passed**, 1 Starlette/httpx deprecation warning.
- `npm run check`: **0 ошибок, 0 предупреждений**. `npm run build`: успешен. `VITE_BASE_PATH=/evidencerag/ VITE_PAGES_BASE_PATH=/evidencerag/ npm run build:local`: успешен.
- `answer-generation-009.spec.ts` + `answer-generation-010.spec.ts`: **2/2 desktop и 2/2 mobile Chromium emulation**; citations, четыре Stage 010 слота, применённая поправка, ограничения и отсутствие external requests.
- `local-migration.spec.ts`: **3/3 desktop и 3/3 mobile Chromium emulation**; demo, поиск/сравнение, upload/reload/delete, DOCX/PDF parser.
- `base-path.spec.ts`: **1/1 desktop и 1/1 mobile Chromium emulation**; прямой адрес, навигация, reload и favicon под `/evidencerag/`.
- Chromium bundle не был установлен в Playwright cache, поэтому E2E запуск выполнен через системный Chrome. Первый запуск без указанного канала браузера закономерно не стартовал.
- Время и память: 50 evaluator runs, Python 3.12.13: median 14.366 ms / p95 15.436 ms; Python tracemalloc peak 0.166 MiB. Это evaluator-only, не cold start и не RSS. Browser-local build: 34 MiB, vendor runtime 29 MiB.
- Независимой выборки, двойной разметки, физического mobile memory профиля и систематического controller ablation на этом этапе нет.

- GitVerse Pages: artifact commit `62efa58cc8e020c18feb9596f962d90de14c4e7f`, собран из source commit `15e5f8417caa5402fa85e2259f7aa0ef9b0050f8`. Публичные HTML, JS, CSS и четыре favicon/touch icon вернули HTTP 200; HTML содержит новый bundle `index-DAAyKUxz.js`.
- `answer-generation-010.spec.ts` на опубликованном HTTPS: **1/1 desktop Chromium**; полный сценарий загрузил три synthetic документа и проверил четыре атрибутированных факта и межсемейную поправку.
- Запуск Pages workflow был инициирован push; номер и интерфейсный статус CI run не зафиксированы отдельно. Live URL и E2E проверены после обновления публичного HTML.

---

## Этап 009 (03.11.2026)

- `.venv/bin/pytest -q`: **72 passed, 0 failed**; одно предупреждение Starlette о переходе TestClient/httpx. Полный JUnit: `experiments/stage009/python-junit.xml`.
- Stage 009 tests: **11**; весь research RAG suite + новые regression: **33 passed**. Новый набор A–J выполняется в `tests/test_stage009_structured_answers.py`; SQLite/FTS интеграция использует реальный store.
- `npm run check`: **0 ошибок, 0 предупреждений**. `npm run build`: успешен; Stage 009 build JS 87.67 KB (30.90 KB gzip), CSS 23.31 KB (5.43 KB gzip).
- `VITE_BASE_PATH=/evidencerag/ VITE_PAGES_BASE_PATH=/evidencerag/ npm run build:local`: успешен для project subpath.
- `answer-generation-009.spec.ts`: **1/1 desktop (10.4 s) + 1/1 mobile Chromium emulation (10.1 s)**. В браузере проверены A–J, цитата и переход в исходный фрагмент, layout без горизонтального переполнения на mobile, absence of external origins and `/api/` calls.
- `local-migration.spec.ts`: **6/6** desktop + mobile emulation; runtime, demo, upload/search/reload/export/import/delete, DOCX/PDF/scan checks. Полные JSON: `experiments/stage009/browser-e2e-{desktop,mobile}.json`, `browser-migration-e2e.json`.
- Известный Python trace `experiments/stage009/run-002/`: 2 chunks, 3 exact source citations, 1 iteration, `sufficient`/`answered`, **8.429 ms**. Это один synthetic regression, не benchmark.
- Публикация: GitVerse Pages run `1994906` successful; live A–J E2E **1/1 desktop (24.4 s) + 1/1 mobile Chromium emulation (21.3 s)**. Live HTML, JS, CSS HTTP 200; JSON: `experiments/stage009/browser-live-{desktop,mobile}.json`. Samsung Internet, iOS Safari, Firefox, полноценный accessibility audit и нагрузка не проверялись.

---

31.10.2026. Локальная проверка stage 006: macOS 27 / Python 3.12. Публичный сайт остаётся на production release `20261031-006` с cookie notice; исследовательский pipeline не развёртывался. Браузерные тесты проверяют пользовательские сценарии и мобильную раскладку; они не являются аудитом доступности или нагрузочной оценкой.

- `.venv/bin/pytest -q`: **61 passed, 0 failed, 0 skipped**, одно предупреждение Starlette о будущем переходе TestClient с `httpx` на `httpx2`. Полный вывод записан в `experiments/pytest-final.txt`; новые 22 теста stage-006 — `tests/test_research_rag.py`.
- `.venv/bin/pytest -q tests/test_research_rag.py`: **22 passed**.
- `.venv/bin/python -m py_compile apps/api/evidencerag/research_rag.py packages/research/runner.py packages/research/trace_runner.py`: успешно.
- Исполненный trace runner: `PYTHONPATH=apps/api .venv/bin/python -m packages.research.trace_runner --output experiments/research-rag-pilot-004` — 2 итерации, завершение `sufficient`, буквальная цитата с проверенной ссылкой; никаких model/API calls. Это один synthetic diagnostic, не benchmark.
- `npm run check`: 0 ошибок, 0 предупреждений. `npm run build`: успешно; JS 76.20 KB (27.52 KB gzip), CSS 20.26 KB (4.84 KB gzip).
- Playwright против `https://osnovanie.duckdns.org`: **8/8 всего**, по 4 сценария в desktop и mobile emulation; JSON-журнал — `experiments/e2e-release-005.json`. Проверены прямые URL, назад/вперёд, новая вкладка, upload/delete, источники, сравнение редакций и отсутствие overflow на 320/390/768/1280 px.
- Серверный smoke на release-005: **17/17**, журнал — `experiments/vps-smoke-release-005.json`. Проверены frontend/assets, TLS cookie, демо, change signal, формальное правило, цитата/оригинал, diff, upload/search/delete, PDF/DOCX, формат/CSRF, изоляция и cleanup. Медиана 5 последовательных запросов на малом наборе — 5.61 ms; это не оценка ёмкости VPS.
- Внешний `/api/health`: HTTP 200; `algorithm=lexical-controller-v2`, `llm_public=false`, `semantic_sufficiency_judge=false`.
- Визуально осмотрены публичная главная и локальная страница метода с текущей сборкой. Палитра архива, типографика, сетка и существующая навигация сохранены.
- Снимок `experiments/infra-after-release-005.json`: контролируемые VPN/Xray unit-состояния и InvocationID, интерфейсы, route/rule/firewall и Docker-network hashes совпали с `experiments/infra-after-publication.json`. Из этого не следует end-to-end проверка всех VPN-клиентов. Существующий Caddy оставлен активным, его конфигурацию и контейнер не меняли.
- Offline pilot run-004: 21 synthetic test-query × 8 конфигураций; подробные метрики и ограничения в `experiments/run-004/REPORT.md`. Answer quality, semantic sufficiency, false abstention, unsupported answer, faithfulness и API cost — null. Сравнение не подтверждает научное преимущество. Аудит run-003/run-004: `docs/RESEARCH_AUDIT_006.md`.
- `npm run check`, `npm run build`, Playwright и VPS smoke не запускались повторно на stage-006: этот этап не менял UI, публичный API или production files. Последние их результаты относятся к cookie/UI и release-005/006, описанным в разделе ниже.

Во время первого post-deploy smoke остались два устаревших утверждения, что редакционные изменения должны находиться в `conflicts`. Проверка зафиксировала корректное новое поведение (`version_differences` отдельно); сценарий `scripts/vps_smoke.py` обновлён, итоговый повтор прошёл 17/17. Same-edition disagreement остаётся отдельным проверяемым сценарием в unit/integration tests.

Локальный Playwright E2E (8/8) выполнен до публикации; текущий release дополнительно проверен 8/8 на публичном HTTPS. Mobile — emulation Chromium, не Safari/iOS. Нет независимого semantic judge, faithfulness, OCR, массовой нагрузки или оценки пропускной способности VPS.

## Cookie notice (31.10.2026)

Добавлены информационная плашка и прямая страница `/cookies`. Поведение плашки: закрытие хранится только в состоянии страницы и сбрасывается после перезагрузки; новых cookie или browser storage для этого не создаётся. `npm run check` — 0 ошибок и предупреждений; `npm run build` — успешно. Локальная browser-проверка подтвердила маршрут, текст политики и доступные ссылки. После публикации release-006 запросы по HTTPS к `/`, `/cookies` и `/api/health` вернули 200; GET страниц не установил cookie. Upload/search к публичному сайту не запускались, отдельный Playwright E2E для этой правки не проводился.

## Browser migration — product build and tests (31.10.2026)

- `npm run check --prefix apps/web`: **0 errors, 0 warnings**.
- `VITE_BASE_PATH=/evidencerag/ npm run build:local --prefix apps/web`: succeeded; builds self-hosted runtime/wheels into separate `apps/web/dist-browser/` and generates `404.html` fallback without replacing the tracked server bundle. Output is about 34 MB; build has not been published.
- Production build under a local static mount at `/evidencerag/`: **4 passed (53.4 s)** in Chromium 156 desktop. Covers app flows plus base-path navigation, favicon, assets, and direct-route reload through the 404 fallback. Assertions reject cross-origin requests, `/api/*`, missing assets and page errors. Full report: `experiments/browser-migration-007/product-e2e-subpath-results.json`.
- `.venv/bin/pytest -q`: **61 passed**, one Starlette `httpx` deprecation warning.
- `npm run audit --prefix experiments/browser-migration-007`: successful CPython/Pyodide synthetic parity probe; JSON artifact `hybrid-parity.json`, BM25 max absolute delta `2.117582368135751e-22` versus tolerance `1e-18`.
- `npm run browser-audit --prefix experiments/browser-migration-007`: successful isolated Chromium OPFS test; SQLite 3.54.1, `secureDelete: true`, persisted across worker restart, 0 rows after delete, no page errors or external requests. Artifact `browser-opfs-e2e.json`.
- The existing release artifact `experiments/e2e-results.json` was restored unchanged after product E2E; new browser-migration result is kept separately.

These are selected local tests, not full parity, load, malicious input, quota, recovery, cross-browser, public hosting, or security audit. The public server-backed service remains active. Only Chromium desktop was used; Firefox, Safari/iOS and mobile devices are untested.

## Stage 008 acceptance deltas (31.10.2026)

- Rebuilt local browser static bundle with `VITE_BASE_PATH=./ VITE_PAGES_BASE_PATH=/evidencerag/ npm run build:local` in `apps/web/`: successful; Pyodide plus 10 pinned wheels, SQLite WASM, two local workers, Svelte JS/CSS.
- New `apps/web/e2e/audit-008.spec.ts` covers route/assets/CSP/mobile-width, Stage 006 second retrieval trace, and offline local TXT upload/search with damaged-PDF and >10 MB rejection. Chromium local preview passed **3/3 desktop and 3/3 mobile emulation**; reports are `local-audit-desktop-pass.json` and `local-audit-mobile-pass.json`.
- The local preview serves direct nested routes with 404 and therefore does not model GitVerse Pages route behavior. Stage008 public run `1971623` deployed commit `15e1241`. Current public acceptance: audit 3/3 desktop + 3/3 mobile emulation and core migration 4/4 desktop + 4/4 mobile emulation. Reports: `public-audit-{desktop,mobile}-pass.json`, `public-core-{desktop,mobile}-pass.json`; previous Stage007 run remains in `public-e2e-desktop.json`.
- Static network audit verifies same-origin only, no `/api`, no marker transmission, no document cookie or browser local/session storage writes. Static hosting still receives request metadata/IP.

- Live performance: first browser engine/demo query ~22.2 s desktop/~18.0 s mobile emulation and ~27.2 MB static runtime/wheels; next offline TXT upload/search 163/255 ms desktop and 795/97 ms mobile. These are one-machine smoke values, not an end-user SLA.
- GitVerse root GET and nested routes were 200; the root response omits Content-Type and the host omits CSP/HSTS/nosniff/referrer/frame security headers. See `public-http-headers.json`; HTML meta CSP is present.
