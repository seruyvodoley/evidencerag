# Производительность браузерной версии — этап 008

Сборка: `VITE_BASE_PATH=./ VITE_PAGES_BASE_PATH=/evidencerag/ npm run build:local` из `apps/web/`. Production bundle содержит app JS около 94.36 kB (32.70 kB gzip), CSS около 22.33 kB (5.23 kB gzip), SQLite WASM около 879.08 kB (407.64 kB gzip), SQLite worker около 216.62 kB и local engine worker около 318.24 kB. Pyodide runtime и 10 pinned wheels также входят в комплект и создают заметную начальную загрузку; полный transfer зависит от браузерного кеша и CDN.

После live deploy Playwright измерил GET document DCL/load 521/524 ms desktop и 405/413 ms mobile emulation в тёплом browser context. App JS/CSS/initial worker transfer — около 445 KB; после первого действия, запускающего Pyodide, браузер скачал примерно 27.2 MB runtime/stdlib/wheels. Первый demo/search runtime занял 22.2 s desktop и 18.0 s mobile emulation. Дальше offline TXT upload/search: 163/255 ms desktop и 795/97 ms mobile emulation. Сырые метрики `browser-metrics-public-{desktop,mobile}.json` и `offline-browser-check-public-{desktop,mobile}.json`. Это один host и один dev machine, не cold-cache/device/network benchmark.

Ограничения продукта: upload ≤10 MB, до 300 PDF pages, извлечённый текст ≤180,000 characters, DOCX expanded archive ≤25 MB и ≤1000 members (источники: parser/worker code и UI). Local worker watchdog 180 s. Серверный parser resource limits не следует переносить на клиент как OS sandbox — браузерный worker даёт отдельный контекст исполнения, но нагрузка и доступная память ограничены самим browser/device. OCR пока нет; scans распознаются как `needs_ocr` и не содержат извлечённого текста.

## Измеренный local preview

В Chromium localhost preview DCL/load были 25/28 ms desktop и 21/23 ms mobile emulation при тёплом контексте. Runtime+первый demo/search — 8,953/5,235 ms; TXT upload — 149/154 ms, поиск — 212/264 ms. См. `offline-browser-check-preview-{desktop,mobile}.json` и `browser-metrics-preview-{desktop,mobile}.json`. Это local mount, не оценка host/реальных устройств.
