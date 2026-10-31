# Финальный аудит браузерной версии — этап 008

Дата: 31.10.2026. Исходный commit: `904b96a7c3238af522744ebbabf6e65868fac170`. Публичный базовый URL: https://seruyvodoley.gitverse.site/evidencerag/ .

## Текущее заключение

Stage 008 опубликован на GitVerse Pages. Исходный код/аудит — commit `4b5d278`; статический deployment commit — `15e1241`; GitVerse run `1971623` завершил build и deploy успешно. Live index использует `assets/index-IlX9GifG.js`; в нём проверены local research `initial_top_k=1` и новое synthetic version rule. URL не менялся: https://seruyvodoley.gitverse.site/evidencerag/ .

На последнем опубликованном bundle Playwright прошёл 3/3 новых audit сценария desktop, 3/3 mobile emulation, и 4/4 существующих browser migration сценария desktop и 4/4 mobile emulation: **14/14 публичных сценариев**. В них проверены 5 прямых маршрутов, навигация/обновление и base path, favicon, WASM/worker, 2-шаговый Stage 006 trace с точной цитатой, TXT upload+search без сети, отказ damaged PDF/>10 MB, OPFS reload persistence, export/import/delete, DOCX table и двухстраничный PDF, scanned PDF OCR notice; сетевой тест не увидел `/api`, другого origin, `Set-Cookie` или marker в URL. Сырые отчёты `public-audit-{desktop,mobile}-pass.json`, `public-core-{desktop,mobile}-pass.json`.

Local build preview прошёл 3/3 desktop и 3/3 mobile emulation. Preview не воспроизводит GitVerse nested-route HTTP fallback; прямые preview routes отдают 404, поэтому публичные route проверки выполнены отдельно на GitVerse. В первом mobile core E2E тест требовал видимую статусную плашку, которую дизайн скрывает на узкой ширине; ожидание исправлено и повторный полный набор прошёл 4/4. Исходные отчёты первых прогонов оставлены как audit trail.

## Выполнено

- `npm run check` — Svelte/TypeScript: 0 ошибок, 0 предупреждений.
- `.venv/bin/pytest -q` — 61 тест пройден (есть одно предупреждение устаревающего API Starlette/httpx).
- `npm run build:local` — production bundle с Pyodide, SQLite WASM, OPFS и worker собран.
- `npm run audit --prefix experiments/browser-migration-007` — synthetic Python/Pyodide parity runner завершился с кодом 0; сырой JSON: `experiments/final-audit-008/python-browser-parity.json`.
- `npm audit --omit=dev` — 0 production vulnerabilities; полный npm audit находит 3 low в dev-only цепочке deepmerge, без доступного npm fix.
- `pip-audit` — 56 зависимостей, известных уязвимостей нет; stderr фиксирует предупреждения `invalid distribution` в локальном venv.
- На обновлённом live URL `/`, `/documents/`, `/compare/`, `/method/`, `/cookies/` отдали 200. `public-http-headers.json`: актуальные JS, CSS, local-engine worker, WASM и SVG icon отдали 200 с ожидаемыми MIME. GET не установил cookie.

## Не подтверждено / блокеры

- Нет реального Safari/iOS или Firefox, Android device QA, browser process/relaunch всех поддерживаемых браузеров, quota-exhaustion, crash recovery и hostile-document fuzzing. Mobile — Playwright Chromium iPhone emulation, не Safari.
- Широкое покрытие настоящими PDF/DOCX/MD/TXT с двумя локальными версиями, точной проверкой таблиц/страниц и конфликтов не получено в одной сводной автоматизированной матрице. Исторические Stage 007 прогоны подтверждают только перечисленные там конкретные сценарии.
- Desktop test report намеренно сохраняет реальные проходы/непроходы; провал не переименовывается в успех.
- На live GitVerse отсутствуют response headers CSP, HSTS, nosniff, Referrer-Policy и frame protections; root GET не задаёт Content-Type. Meta CSP действует в HTML, но не заменяет response headers. Контролировать эти заголовки через настройки Pages не удалось.
- Проверка SSH к проверка указанного владельцем SSH endpoint на порт 22 завершилась timeout. VPS и TunnelDeck в этой итерации не менялись и их текущее состояние удалённо не подтверждено. Пользователь ранее сообщил, что приложение VPS отключил сам; это не является технической проверкой.

См. [parity](BROWSER_PARITY_008.md), [privacy](PRIVACY_AUDIT_008.md), [performance](PERFORMANCE_008.md), [deployment](GITVERSE_DEPLOYMENT_008.md), [VPS](VPS_DECOMMISSION_008.md), [experiment plan](NEXT_EXPERIMENT_PLAN.md). Отчёты, тестовые данные без персональных сведений и реальные browser artifacts собраны в [архиве Stage 008](../artifacts/evidencerag-reports-stage-008.zip); приватные ключи и VPN-конфигурации в него не входят.
