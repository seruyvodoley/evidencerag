# Публикация GitVerse Pages — этап 009

Публичный URL: https://seruyvodoley.gitverse.site/evidencerag/ . Статика этапа 009 собрана из исходного commit `d0743d9`, помещена в Pages artifact repository и отправлена commit `0a8b63b4e3c9f26c26f5db914ec317e553330cac` (`0a8b63b`). GitVerse Pages workflow run `1994906` завершился успешно; build job `3943841` успешен. Публикация идёт из artifact репозитория, checkout исходников не имеет remote и остаётся локальным.

## Проверка live

- Index: HTTP 200; загружает `/evidencerag/assets/index-DMIg_zOT.js` и `/evidencerag/assets/index-tFFhyzAq.css`.
- JavaScript и CSS assets: HTTP 200, корректные `application/javascript` и `text/css`.
- Live Playwright local-runtime E2E A–J: Chromium desktop **1/1, 24.4 s**; mobile viewport emulation **1/1, 21.3 s**. Проверены версия/даты, применение отдельной частичной поправки, конфликт, пропуск и отказ, цитирование; ограничения внешних origin/API запросов — согласно спецификации теста.
- Полные browser JSON: `experiments/stage009/browser-live-desktop.json`, `browser-live-mobile.json`.
- После завершения CI опубликованный index сменил JS/CSS fingerprint с Stage 008 на Stage 009. Проверка производилась с `Cache-Control: no-cache`.

Эти данные подтверждают выпуск и пользовательский regression flow, но не подтверждают юридическую корректность правил, работу на физических устройствах, независимую семантическую точность или научное превосходство. GitVerse Pages размещает статические HTML/JS/WASM ресурсы; приложение выполняет обработку локально в браузере. Сервер VPS, Caddy, VPN, DNS, firewall и SSH конфигурация не менялись.
