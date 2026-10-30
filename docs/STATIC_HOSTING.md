# Static hosting — этап 007

Статус на 31.10.2026: **static bundle готовится локально, сайт не опубликован**.

## Готовый артефакт и команды

- `cd apps/web && VITE_BASE_PATH=/evidencerag/ npm run build:local` self-hosts Pyodide runtime/wheels в `public/vendor`, делает локальную Vite сборку с `VITE_LOCAL_EXECUTION=true` в отдельный `dist-browser/` и копирует `index.html` в `404.html` для SPA fallback. `dist/` остаётся production bundle текущего server-backed сайта.
- Vite base path настраивается через `VITE_BASE_PATH`. Static mount harness проверил sample project prefix `/evidencerag/`, assets, favicon и reload маршрута через fallback; при публикации заменить prefix на фактический путь проекта.
- Последний `apps/web/dist-browser` занимает около 34 MB (примерно 29 MB vendor); точный transfer/compression и individual file limits у выбранного host не проверялись. Этот build output игнорируется Git и локально воспроизводится командой выше.
- `index.html` содержит CSP meta; response-only security headers должен задать host.

## GitVerse Pages

По проверенной документации GitVerse Pages — free static hosting для тарифа Free, описывает project URL `https://<owner>.gitverse.site/<repo-name>` и максимальный artifact size 500 MB; для сложных сборок предусмотрен custom CI workflow. Документация: [Pages overview](https://gitverse.ru/docs/pages/overview/) и [Pages docs](https://gitverse.ru/docs/pages/docs/).

В этом локальном окружении нет git remote, настроенного GitVerse репозитория, credentials или workflow. Сайт не опубликован; сертификат, URL, MIME types для Pyodide/WASM, response security headers, 404/SPA rewrite, OPFS, cache и E2E на host не проверены. Локальный static mount проверил production artifact и типы `.mjs`/`.wasm`, но не GitVerse. Документационное соответствие не заменяет deploy smoke.

## Перед публикацией

1. Создать/выбрать static repository и настроить GitVerse Pages workflow под `VITE_BASE_PATH`.
2. Публиковать только output `apps/web/dist-browser` с зафиксированным source commit и artifact manifest; не включать backend, credentials, реальные пользовательские документы или локальные базы.
3. Проверить главный и прямые маршруты `/documents`, `/compare`, `/method`, fallback, HTTPS, WASM MIME, Worker, CORS/COOP при необходимости и response headers.
4. Прогнать product E2E по опубликованному URL с network interception; проверить загрузку runtime/wheels, upload/search/import/export/delete и unique marker.
5. Измерить холодную загрузку и compression. Сайт остаётся opt-in local bundle, пока эти проверки и прочие gates не завершены.

Не использовать VPS/Caddy как «статический хостинг без сервера» для выполнения условия об отказе от собственного VPS. До работающей публикации и smoke нельзя отключать действующую FastAPI службу.
