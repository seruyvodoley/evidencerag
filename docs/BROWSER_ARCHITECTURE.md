# Браузерная архитектура EvidenceRAG — этап 007

Обновлено: 31.10.2026. Статус: **локальный режим интегрирован в UI и проверен на ограниченных сценариях; публичная миграция не завершена**. По умолчанию приложение остаётся серверным. Только `npm run build:local` включает `VITE_LOCAL_EXECUTION=true`.

## Текущая схема

```text
Сборка по умолчанию (текущий публичный release)
Svelte UI → same-origin /api → FastAPI на VPS → Python + SQLite/FTS5

Отдельная локальная статическая сборка
Svelte UI → browser-local-api → выделенный Web Worker
  ├─ Pyodide: текущие parser.py, retrieval.py, store.py, research_rag.py
  ├─ SQLite WASM 3.54.1: FTS5/BM25 и OPFS SAH Pool VFS
  ├─ OPFS: SQLite workspace, документы, чанки и индекс
  └─ IndexedDB: случайный идентификатор workspace

Python-эксперименты → текущая CPython среда и offline runner (без изменений)
```

Статическая локальная сборка включает закреплённые runtime/wheels на том же origin. Она не вызывает API приложения и не использует внешние модели. В production исходнике флаг выключен, а текущий публичный VPS релиз остаётся серверным до отдельной публикации.

## Карта функций и фактического покрытия

| Существующая функция | Исходный модуль | Браузерная реализация | Проверка | Статус / предел |
|---|---|---|---|---|
| PDF, DOCX, TXT, Markdown parsing, locators и страницы | `apps/api/evidencerag/parser.py` | Тот же Python модуль в Pyodide Worker; локальный API обрабатывает upload | Product Chromium E2E: DOCX таблица, двухстраничный PDF и scanned PDF; Python/Pyodide synthetic parity | Частично подтверждено на fixtures. Нет широкого корпуса и сравнения форматирования/смещений для реальных сложных файлов. OCR отсутствует; сканы получают `needs_ocr`. |
| Русская нормализация и термины | `retrieval.py` | Тот же код + закреплённые `pymorphy3` и словарь в Pyodide | Synthetic CPython/Pyodide morphology parity и русские демо-запросы в Chromium | Ограниченная выборка; не измерены словарные углы и качество на корпусе. |
| SQLite схема, workspace, редакции, chunks и provenance | `store.py` | Действующий `EvidenceStore` через DB-API bridge к SQLite WASM 3.54.1 | Product upload/search/reload/delete/export/import E2E; synthetic harness | CRUD покрыт основными путями, но нет стресс-проверки конкурентности, аварийного завершения или восстановления повреждённой БД. |
| FTS5 BM25, фильтры, стабильные IDs | `store.py`, `retrieval.py` | Тот же код на SQLite WASM; OPFS SAH Pool VFS | Synthetic parity; Chromium OPFS persistence across worker restart; обычный поиск в product E2E | BM25 численно совпал в synthetic probe с Δ ≤ `1e-18`; это не полная parity матрица и не большой корпус. |
| Fixed-k / adaptive-k / версии / field-change signals | `retrieval.py` | Тот же Python-код в Worker | Synthetic deterministic parity; UI проверяет поиск и сравнение двух демо-редакций | Ограниченная parity выборка. Сигналы поля буквальные/лексические и не являются семантическим конфликтным анализом. |
| EvidenceRAG controller, gaps, budget, trace, отказ | `research_rag.py` | Локальный `/research` маршрут вызывает существующий research controller | Synthetic formal-rule parity; product UI проверяет trace JSON и literal quote rule | Проверено на авторском формальном правиле. Семантическая достаточность и NLI judge отсутствуют; без evaluator система не утверждает entailment. |
| Оригиналы документов и их локальный поиск | `main.py`, `store.py` | Local worker API, IndexedDB pointer и OPFS store | E2E upload, reload, поиск уникального маркера, export, delete, import, повторный поиск | Хранилище зависит от браузерной квоты/политики eviction. Пользователю требуется экспортная копия; восстановление после принудительной очистки браузера не гарантируется. |
| Архив экспорта и импорта | Раньше не было browser contract | JSON-архив с оригинальными байтами в base64; импорт строит новое пространство, затем завершает замену старого | Product E2E: экспорт, удаление, импорт и поиск | Проверен только корректный малый архив. Нет исчерпывающих тестов на повреждение, hostile payload и переполнение квоты. |
| Cookie, FastAPI upload, server TTL | `main.py` | В local UI не используются; локальная страница сообщает об OPFS/IndexedDB | Product E2E убеждается, что local mode без cookie notice и API-запросов | Текущий публичный серверный режим по-прежнему использует cookie и VPS. Local-only copy применима лишь к локальной сборке. |
| Research runner, baselines и сохранённые результаты | `packages/research`, `experiments/` | Остаются на CPython; не загружаются посетителям | Исходные Python tests и аудит stage 007 | Существующие результаты не перезаписывались; браузерная миграция не меняет научные выводы. |

## Runtime, CSP и сеть

`apps/web/scripts/prepare-browser-runtime.mjs` помещает Pyodide, SQLite и 10 Python wheels в `apps/web/public/vendor/`, вычисляет SHA-256 wheel manifest и проверяет Pyodide lock metadata. `build:local` создаёт отдельную статическую сборку `apps/web/dist-browser/` и `404.html`, не меняя tracked server-backed `dist/`. `VITE_BASE_PATH` настраивает project prefix; app links, favicon, runtime URLs и route parser используют этот prefix. Sample build с `/evidencerag/` прошёл local static-mount E2E. Итоговый artifact около 34 MB, из них vendor около 29 MB; transfer/cold-load и поведение GitVerse не измерены.

В `apps/web/index.html` добавлена meta CSP: same-origin по умолчанию, WASM eval разрешён только директиве script, запрещены object и внешние подключения. Это дополнительное ограничение браузера, не серверный response header. `frame-ancestors`, HSTS и прочие header-only директивы статический HTML meta не обеспечивает; статический host должен задавать свои проверенные response headers.

В локальном Chromium E2E контролируются все запросы страницы: только тот же origin, без `/api`, внешних origin, ошибок страницы и передачи уникального документа-маркера. Это доказательство только для проверенных сценариев/сборки, не полный аудит браузерного трафика или публичного сайта.

## Не проверено / не реализовано

- Семантическая модель, OCR, embeddings и free-text answer generation не подключены.
- Firefox, настоящий Safari/iOS, Android и приватные режимы не тестировались.
- Не исследованы browser storage quota/eviction, большие корпуса, concurrency и forced worker termination.
- Не проверены XSS/payload fuzzing, все повреждённые архивы и длительное восстановление после аварии.
- Статический сайт не опубликован на GitVerse или другом хостинге; новый публичный URL не получен.
- Старый VPS backend и его доменный маршрут остаются активными; TunnelDeck и VPS не менялись.
