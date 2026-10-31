# Производительность браузерной версии — этап 008

Сборка: `VITE_BASE_PATH=./ VITE_PAGES_BASE_PATH=/evidencerag/ npm run build:local` из `apps/web/`. Production bundle содержит app JS около 94.36 kB (32.70 kB gzip), CSS около 22.33 kB (5.23 kB gzip), SQLite WASM около 879.08 kB (407.64 kB gzip), SQLite worker около 216.62 kB и local engine worker около 318.24 kB. Pyodide runtime и 10 pinned wheels также входят в комплект и создают заметную начальную загрузку; полный transfer зависит от браузерного кеша и CDN.

Playwright снимает `domContentLoaded`, `load`, Resource Timing, transfer sizes, время готовности runtime, upload и search в `experiments/final-audit-008/`. Не публикуем универсальное число времени, пока текущий acceptance replay не завершился чистым прогоном на опубликованном релизе. Холодный запуск Pyodide длительнее последующих запросов; алгоритмические server timeouts не являются гарантией одинакового wall time на устройствах.

Ограничения продукта: upload ≤10 MB, до 300 PDF pages, извлечённый текст ≤180,000 characters, DOCX expanded archive ≤25 MB и ≤1000 members (источники: parser/worker code и UI). Local worker watchdog 180 s. Серверный parser resource limits не следует переносить на клиент как OS sandbox — браузерный worker даёт отдельный контекст исполнения, но нагрузка и доступная память ограничены самим browser/device. OCR пока нет; scans распознаются как `needs_ocr` и не содержат извлечённого текста.

## Измеренный local preview

В Chromium localhost preview с уже посещёнными route/assets и тёплым кешем Playwright зафиксировал DOMContentLoaded/load 126/134 ms desktop и 27/30 ms mobile emulation. First demo runtime (с загрузкой browser engine) занял 4,610 ms desktop и 5,936 ms mobile emulation; офлайн TXT upload — 97/104 ms, поиск — 99/111 ms соответственно. Артефакты `experiments/final-audit-008/offline-browser-check-{desktop,mobile}.json`; Resource Timing и ответы — `browser-metrics-{desktop,mobile}.json`. Это локальный smoke на одном dev machine, не cold-network и не device benchmark. Результаты не прогнозируют опыт реальных устройств/сетей.
