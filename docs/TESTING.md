# Проверки и результаты

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
