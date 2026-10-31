# Финальный аудит браузерной версии — этап 008

Дата: 31.10.2026. Исходный commit: `904b96a7c3238af522744ebbabf6e65868fac170`. Публичный базовый URL: https://seruyvodoley.gitverse.site/evidencerag/ .

## Текущее заключение

Миграция браузерного движка уже опубликована на GitVerse в этапе 007. В этом этапе локально проверены актуальная production-сборка и пользовательские потоки; выявлена и исправляется маршрутизация выбора коллекции в acceptance-тесте (демо-коллекция оставалась выбранной после загрузки второго документа). Расширенная сборка этапа 008 локально принята Playwright: **3/3 desktop и 3/3 mobile emulation**. GitVerse deploy key создан для репозитория, локальный deploy ожидает синхронизации и CI-публикации. Поэтому публичный адрес не объявляется обновлённым до проверки CI и его развернутого содержимого.

Текущий Playwright `experiments/final-audit-008/public-e2e-desktop.json`: 4 desktop-сценария прошли на ранее опубликованной версии. Перечень сценариев и сырой отчет — в JSON. Новые acceptance-сценарии сохранены в `experiments/final-audit-008/local-audit-desktop-pass.json` и `local-audit-mobile-pass.json`; оба 3/3 expected, 0 unexpected. Ранний прогон поймал ошибку настройки коллекции в тесте и был исправлен. Preview на `127.0.0.1:5177/evidencerag/` не воспроизводит GitVerse SPA fallback и отдаёт 404 прямым вложенным маршрутам; для проверки их HTTP статуса нужен опубликованный host. На локальном preview client-side navigation и reload внутри страницы проходят; это не подтверждает прямой public fallback.

## Выполнено

- `npm run check` — Svelte/TypeScript: 0 ошибок, 0 предупреждений.
- `.venv/bin/pytest -q` — 61 тест пройден (есть одно предупреждение устаревающего API Starlette/httpx).
- `npm run build:local` — production bundle с Pyodide, SQLite WASM, OPFS и worker собран.
- `npm run audit --prefix experiments/browser-migration-007` — synthetic Python/Pyodide parity runner завершился с кодом 0; сырой JSON: `experiments/final-audit-008/python-browser-parity.json`.
- `npm audit --omit=dev` — 0 production vulnerabilities; полный npm audit находит 3 low в dev-only цепочке deepmerge, без доступного npm fix.
- `pip-audit` — 56 зависимостей, известных уязвимостей нет; stderr фиксирует предупреждения `invalid distribution` в локальном venv.
- GitVerse URL ранее отдавал 200 для `/`, `/documents/`, `/compare/`, `/method/`, `/cookies/`; desktop E2E предыдущего релиза прошёл 4/4.

## Не подтверждено / блокеры

- Новый Stage 008 bundle пока не прошёл CI-публикацию и повторный E2E на опубликованной версии.
- Android, реальный Safari/iOS, Firefox, закрытие и повторное открытие браузера, квота OPFS exhaustion, crash recovery и hostile-document fuzzing не прошли в этой приёмке.
- Широкое покрытие настоящими PDF/DOCX/MD/TXT с двумя локальными версиями, точной проверкой таблиц/страниц и конфликтов не получено в одной сводной автоматизированной матрице. Исторические Stage 007 прогоны подтверждают только перечисленные там конкретные сценарии.
- Desktop test report намеренно сохраняет реальные проходы/непроходы; провал не переименовывается в успех.
- Проверка SSH к `91.196.32.58:22` завершилась timeout. VPS и TunnelDeck в этой итерации не менялись и их текущее состояние удалённо не подтверждено. Пользователь ранее сообщил, что приложение VPS отключил сам; это не является технической проверкой.

См. [parity](BROWSER_PARITY_008.md), [privacy](PRIVACY_AUDIT_008.md), [performance](PERFORMANCE_008.md), [deployment](GITVERSE_DEPLOYMENT_008.md), [VPS](VPS_DECOMMISSION_008.md), [experiment plan](NEXT_EXPERIMENT_PLAN.md).
