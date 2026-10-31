# Аудит приватности браузерной версии — этап 008

## Наблюдаемое поведение

Browser implementation обрабатывает документы в Pyodide Worker и сохраняет рабочее пространство в SQLite WASM/OPFS; указатель пространства расположен в IndexedDB. В отчётах Stage 007 (`docs/BROWSER_PRIVACY_AUDIT.md`, `experiments/browser-migration-007/`) синтетический marker не покинул origin; OPFS harness проверял перезапуск worker и удаление строк. Stage 008 desktop и mobile Playwright на опубликованном сайте: 3/3 новых сценария в каждом проекте; старый migration suite 4/4 в каждом. Зафиксированы only same-origin, no `/api`, no marker leakage, no `Set-Cookie`, no local/sessionStorage entries, корректный wasm MIME. `public-http-headers.json` подтверждает GET routes/assets, cookie/header state.

При загрузке публичной страницы GitVerse получает сетевой запрос и может видеть IP-адрес и HTTP metadata посетителя; браузерное локальное хранение не отменяет эту передачу. Это технический вывод из модели HTTP, а не утверждение о фактическом сроке хранения GitVerse. Отдельная страница cookie информирует о first-party техническом поведении; аналитических/рекламных скриптов приложение не добавляет. В актуальной сборке мета CSP задаёт `default-src 'self'`, локальные worker/wasm и ограниченные `connect-src`, `object-src 'none'`, `base-uri 'self'`, `form-action 'self'`.

## Ограничения

- Проверка сети не является юридическим заключением о соблюдении всех требований РФ/ЕС. Операторские реквизиты, правовое основание, retention на стороне GitVerse и трансграничная обработка требуют отдельной оценки оператора/юриста.
- CSP через meta не может установить `frame-ancestors` и часть response-only директив. На live ответах GitVerse снова отсутствуют CSP response header, HSTS, X-Content-Type-Options, Referrer-Policy и X-Frame-Options; root GET также не содержит Content-Type, хотя вложенные routes корректно отвечают `text/html; charset=utf-8`. Статический host не предоставляет в проекте управляемую настройку response headers. Проверьте актуальные headers после Stage 008 публикации.
- OPFS/IndexedDB находятся в браузерном профиле пользователя; браузер/пользователь может очистить данные, а квоты отличаются. Экспорт — единственный переносимый backup.
- Удаление локального пространства удаляет строки БД штатным кодом, но не является криптографической гарантией стирания flash/cache/backup.
- Не тестировались полный XSS/fuzzing аудит сторонних зависимостей, злонамеренные архивы на все лимиты, профили браузерного приватного режима или изоляция между всеми возможными браузерными origin.

Быстрый source scan `rg -n "innerHTML|outerHTML|new Function|eval\(|localStorage|sessionStorage|document\.cookie|fetch\(|XMLHttpRequest|WebSocket" apps/web/src apps/web/index.html` не нашёл HTML injection/eval sinks; найден server fallback `fetch('/api'+path)` в `App.svelte`. Local build исключает этот API режим; публикуемые сетевые тесты подтверждают отсутствие `/api` requests. Это статический scan, не формальный XSS audit.

Артефакты: `experiments/final-audit-008/npm-audit-production.json`, `npm-audit-full.json`, `pip-audit.json`, Playwright JSON и сетевые отчёты в этой папке.
