# Сетевой аудит браузерного режима EvidenceRAG — этап 007

Дата: 31.10.2026. Статус: **сетевое поведение проверено автоматизированно на четырёх локальных Chromium сценариях production build; общий privacy/security audit и проверка опубликованного сайта не завершены**.

## Проверено в local UI

- Сборка с `VITE_LOCAL_EXECUTION=true`: просмотр демонстрации, поиск/сравнение/research trace, загрузка пользовательского Markdown с уникальным маркером, reload, поиск, экспорт, удаление, импорт и повторный поиск; DOCX/PDF fixtures.
- Playwright перехватывает запросы страницы и требует, чтобы их origin совпадал с origin страницы; также проверяется отсутствие `/api/*` и JavaScript page errors. Три migration сценария прошли на production build.
- Четвёртый сценарий под локальным static mount проверяет project-prefix `/evidencerag/`, пути assets/favicon, навигацию и прямой route reload с `404.html` fallback; отсутствующие ресурсы и JS ошибки не обнаружены. Это имитация static origin, не тест настоящего GitVerse.
- Уникальный маркер был в экспортном архиве на локальном устройстве и не наблюдался в сетевом запросе к другому origin. В этих сценариях документы/индекс хранятся в OPFS SQLite; локальный указатель — в IndexedDB.
- Pyodide runtime и Python wheels закреплены и включены в статическую поставку. Product runtime не скачивает Python wheels с CDN/PyPI.
- Добавлена meta CSP с `default-src 'self'`, `connect-src 'self'`, `worker-src 'self'`, ограниченными scripts и `object-src 'none'`. Она проверена совместно с product E2E.
- Browser OPFS harness сообщает `externalRequests: []`, `pageErrors: []`, persistence across worker restart и 0 строк после удаления.

Артефакты: [`product-e2e-subpath-results.json`](../experiments/browser-migration-007/product-e2e-subpath-results.json), [`browser-opfs-e2e.json`](../experiments/browser-migration-007/browser-opfs-e2e.json).

## Что это не доказывает

- Это проверка локального тестового origin, а не опубликованного домена, чужой browser extension, системы и сетевого посредника.
- Публичная версия `https://osnovanie.duckdns.org` остаётся серверной: там документы отправляются на `/api` существующего VPS. Нельзя описывать текущий публичный сайт как local-only.
- Непроверены XSS/fuzzing, вредоносные архивы, все Unicode/parser edge cases, crash recovery, quota exhaustion, OPFS eviction и браузерный private mode.
- CSP meta не устанавливает response-only `frame-ancestors`, HSTS, `X-Content-Type-Options` и прочие HTTP headers. Их должен задавать статический host, и их ещё надо проверить после публикации.
- Не проводилась правовая оценка РФ/ЕС и не подтверждена достаточность Privacy Notice для новой схемы. Данный отчёт не юридическое заключение.

## Acceptance до публичного переключения

После выбора static host снять фактические HAR/request logs для главной, прямых маршрутов, загрузки assets/runtime, поиска, upload/import/export/delete; подтвердить отсутствие обращения к API/внешним origin в local режиме. Проверить MIME, cache, CSP/response headers, историю/404 fallback и network errors с уникальным маркером. Отдельно проверить server-backed fallback и privacy disclosures до его снятия.
