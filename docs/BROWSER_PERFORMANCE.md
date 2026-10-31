> Исторический снимок этапа 007. Последующее live-развёртывание и приёмка этапа 008 описаны в [FINAL_BROWSER_AUDIT_008.md](FINAL_BROWSER_AUDIT_008.md); данный документ фиксирует состояние до публикации Stage 008.

# Производительность браузерного EvidenceRAG — этап 007

Дата: 31.10.2026. Выполнен локальный build и desktop Chromium E2E; это не полноценный benchmark устройства или сети.

## Измерено на доступном окружении

- Chromium desktop product E2E: 4 сценария, суммарно **53.4 s** по Playwright (включая холодную установку runtime, fixtures и запуск production static build через локальный mount под `/evidencerag/`). Отдельные длительности: 1.8 s base-path/fallback, 13.7 s demo/research, 23.9 s upload/import, 10.6 s parsers. Это не latency одного поиска или индексирования.
- `VITE_BASE_PATH=/evidencerag/ npm run build:local`: завершился успешно; Vite сообщил около 4.1 s для production bundle build, затем подготовлен `404.html` fallback. Длительность подготовки runtime в эту оценку не включена.
- Итоговая папка `apps/web/dist-browser`: примерно **34 MB**; `apps/web/public/vendor`: примерно **29 MB**. Включает Pyodide runtime, Python stdlib, закреплённые wheels, SQLite/WASM и UI assets. Это распакованный размер артефакта, не transfer size.
- Основные сжатые размеры из Vite build: app JS 93.09 KB (32.30 KB gzip); worker 317.90 KB; SQLite WASM 879.08 KB (407.64 KB gzip); `sqlite-worker1` 216.59 KB; OPFS proxy worker 32.46 KB. Pyodide/Wheels каталог не включён в Vite gzip summary, поэтому итоговую загрузку сети надо измерить на host.
- Synthetic Python/SQLite harness сравнил BM25 score: максимальная абсолютная разница `2.117582368135751e-22` при tolerance `1e-18`.

## Не измерено

- Холодный/повторный transfer и startup Pyodide + всех wheels на реальном host; кеширование и compression static host.
- Парсинг/индексация по времени и памяти для обычных/крупных PDF, нескольких документов и редакций.
- Latency повторного поиска, адаптивного top-k, controller и конкурентных операций на реальном корпусе.
- Устройство с малой памятью, мобильное устройство, Firefox, Safari/iOS, Android, приватный режим и квота OPFS.
- Поведение при `QuotaExceededError`, повреждённом хранилище, завершении worker по timeout и recovery.
- Скорость и footprint локальных моделей: моделей нет.

Не делать заявлений о приемлемом мобильном опыте или production throughput до измерения этих значений. Сборка остаётся opt-in и пока не опубликована.
