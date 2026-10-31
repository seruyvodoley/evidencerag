> Исторический снимок этапа 007. Последующее live-развёртывание и приёмка этапа 008 описаны в [FINAL_BROWSER_AUDIT_008.md](FINAL_BROWSER_AUDIT_008.md); данный документ фиксирует состояние до публикации Stage 008.

# Отчёт о миграции EvidenceRAG — этап 007

Обновлено: 31.10.2026. Статус: **частичная локальная миграция интегрирована и прошла выбранные тесты; публичное переключение и отключение VPS заблокированы незакрытыми release gates**.

## Что сделано

- В существующий Svelte UI добавлен opt-in режим `VITE_LOCAL_EXECUTION=true`; сборка по умолчанию и публичный сайт остаются серверными.
- Worker запускает Pyodide и текущие модули Python parser, morphology, `EvidenceStore`, retrieval и `research_rag.py`. SQLite WASM 3.54.1 предоставляет FTS5 и OPFS VFS; Python соединяется через локальный DB-API bridge.
- Добавлены локальная обработка PDF/DOCX/TXT/Markdown, browser workspace, русский поиск, версии/сравнение, исследовательский `/research`, trace JSON, удаление и JSON экспорт/импорт.
- Runtime и 10 pinned wheels self-hosted в build output; во время runtime код не устанавливает пакеты с PyPI/CDN. Локальный режим ограничен same-origin CSP meta.
- Локальная сборка создаётся отдельно в `apps/web/dist-browser`, чтобы не заменять tracked server-backed `apps/web/dist`. Поддержан Vite base path для GitVerse project URL: маршруты, favicon, runtime и SPA fallback.
- Добавлены продуктовые Playwright E2E тесты и результаты production static mount в [`product-e2e-subpath-results.json`](../experiments/browser-migration-007/product-e2e-subpath-results.json).
- Старое `experiments/e2e-results.json` восстановлено из HEAD после запуска отдельного сценария, чтобы не перезаписать релизный E2E журнал.

## Выполненные проверки

- `.venv/bin/pytest -q`: **61 passed**, 1 предупреждение Starlette/httpx TestClient.
- `npm run check --prefix apps/web`: **0 ошибок, 0 предупреждений**.
- `VITE_BASE_PATH=/evidencerag/ npm run build:local --prefix apps/web`: успешен. Артефакт `apps/web/dist-browser` около 34 MB; `public/vendor` около 29 MB, сетевой transfer/cold-load не измерен. Обычный server-backed `apps/web/dist` не заменён этой командой.
- Playwright Chromium 156, desktop project, production build под локальным статическим origin `/evidencerag/`: **4/4 за 53.4 s**. Проверены навигация и favicon в поддиректории, reload прямого маршрута через `404.html`, демо/search/source/version compare/research trace, upload/reload/search/export/delete/import, DOCX table, двухстраничный PDF и scan recognition. Внешние requests, `/api`, page errors и missing assets не обнаружены. Журнал: [`product-e2e-subpath-results.json`](../experiments/browser-migration-007/product-e2e-subpath-results.json).
- CPython/Pyodide synthetic parity: parser, morphology, stable IDs, retrieval/controller и FTS5 работают; BM25 max absolute Δ `2.117582368135751e-22` при tolerance `1e-18`. Подробный результат: [`hybrid-parity.json`](../experiments/browser-migration-007/hybrid-parity.json).
- Отдельный Chromium OPFS harness: SQLite 3.54.1, FTS5 `secure-delete`, persistence across worker restart, после удаления 0 строк и 0 page errors. Журнал: [`browser-opfs-e2e.json`](../experiments/browser-migration-007/browser-opfs-e2e.json).

Эти тесты подтверждают выбранные synthetic fixtures и сценарии на одном Chromium desktop. Они не устанавливают полную алгоритмическую эквивалентность, общую производительность, корректность ответа или качество научного метода.

## Статус относительно конечной цели

| Gate | Состояние |
|---|---|
| Browser local UI и документный цикл | Частично выполнен; основные маршруты имеют E2E, края/квоты и широкий corpus не проверены |
| Парсер, морфология, FTS/BM25, controller | Частично проверено на небольшой synthetic parity suite; полного покрытия всех актуальных возможностей нет |
| Передача документов в API | Не обнаружена в проверенных local UI E2E; это не full privacy/security audit |
| Статический build / fallback | Сборка и route fallback проверены через локальный static mount; целевой GitVerse host не опубликован и не проверен |
| Новый публичный URL и HTTPS | Не выполнено |
| Мобильные/Firefox/Safari | Не выполнено; есть только desktop Chromium E2E |
| Semantic/NLI модели, OCR, local LLM | Не реализованы; моделей нет |
| Отказ от собственного VPS / стоимость хостинга | Не достигнут; VPS по-прежнему обслуживает публичный сайт |
| Проверка/сохранность TunnelDeck после migration | VPS не трогали; пост-миграционной проверки нет |

## Почему нельзя переключать публичный сайт или отключать backend

У локального build нет настроенного Git remote, аккаунта/репозитория GitVerse или другого готового static host target. Новый публичный URL и реальные host headers/MIME/cache/HTTPS/network ещё не проверены; локальная подстановка static mount подтверждает только содержимое build и ожидаемое поведение project path/fallback. Поэтому текущий публичный DuckDNS сайт всё ещё обслуживается FastAPI; отключение `evidencerag.service` нарушило бы его работу.

Не выполнялись SSH, изменения systemd/Caddy/DNS/firewall/Docker/VPN, остановка VPS backend или удаление данных/backup. Это соответствует условию не отключать старый сервис до прохождения этапов A–K. TunnelDeck не трогали.

## Следующие необходимые шаги

1. Настроить статический repository/host target и опубликовать build с проверенными заголовками и корректными маршрутами.
2. Прогнать smoke и network audit по фактическому URL; проверить asset MIME, CSP, worker/WASM, cache и прямые маршруты.
3. Проверить квоты, крупные/повреждённые документы и архивы; измерить cold-load, indexing и search на целевом host/доступных браузерах.
4. Расширить deterministic parity corpus на все исследовательские сценарии и закрепить тестовые inputs/outputs.
5. Только после прохождения этих gates проверить точные systemd/Caddy зависимости на VPS, сделать обратимую остановку только EvidenceRAG и отдельно подтвердить, что TunnelDeck доступен. Сохранить DB и резервные копии.

Migration feasibility и успешные тесты не означают научную новизну или подтверждённую semantic sufficiency. Python research ядро и прежние экспериментальные результаты сохранены.
