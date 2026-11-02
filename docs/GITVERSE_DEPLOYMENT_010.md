# GitVerse Pages — публикация Stage 010 (03.11.2026)

- Публичный адрес: https://seruyvodoley.gitverse.site/evidencerag/
- Исходный код: GitHub `seruyvodoley/evidencerag`, commit `15e5f8417caa5402fa85e2259f7aa0ef9b0050f8`.
- Статический Pages artifact: GitVerse `seruyvodoley/evidencerag`, ветка `master`, commit `62efa58cc8e020c18feb9596f962d90de14c4e7f`. `DEPLOYMENT_MANIFEST.json` связывает artifact с source commit и SHA-256 каждого файла.
- Публичный HTML перешёл на bundle `assets/index-DAAyKUxz.js`; root HTML, JS, CSS, SVG favicon, ICO favicon, PNG 32×32 и Apple touch icon вернули HTTP 200. Хост не прислал Content-Type для root HTML; ранее наблюдаемые ограничения security headers хостинга остаются предметом отдельного аудита.
- Live Playwright `answer-generation-010.spec.ts`: 1/1 desktop Chromium. Проверен browser-local сценарий на трёх synthetic документах, четырёх фактах, применённой поправке и контроле внешних запросов. Mobile Stage 010 после публикации отдельно не повторялся; он прошёл на локальной Pages-сборке до публикации.
- Отправка artifact commit инициировала публикацию. Номер CI run отдельно не подтверждён; готовность проверена по смене публичного HTML/assets и live E2E.
- Источник не содержит semantic/NLI judge; успех известного synthetic case является регрессией, а не независимой оценкой обобщения или научной эффективности.
- Пользовательский файл `experiments/e2e-results.json` не включён в коммиты. Инфраструктура VPS/VPN/DNS/SSH не менялась.
