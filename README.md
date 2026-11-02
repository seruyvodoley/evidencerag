# Основание / EvidenceRAG

Публичная browser-local версия: [GitVerse Pages](https://seruyvodoley.gitverse.site/evidencerag/). Статус текущего релиза см. в [PROJECT_STATUS.md](docs/PROJECT_STATUS.md).

Локальный checkout Stage 010 прошёл unit/integration и desktop/mobile browser-local регрессии. Новый artifact ещё не опубликован; ограничения оценки, результаты и статус независимой проверки приведены в [STAGE_010_EVALUATION.md](docs/STAGE_010_EVALUATION.md).

Работающий прототип проверяемого поиска по документам и сравнения редакций. Русский интерфейс, Svelte 5 + TypeScript; browser-local режим использует Pyodide и SQLite WASM/FTS5, FastAPI остаётся для локального серверного варианта. Публичный browser build не требует внешней модели или платного API.

## Локальный запуск

Нужны Python 3.12+, uv и Node.js 20.19+ (или 22.12+).

```sh
uv sync
cd apps/web
npm ci
npm run build
cd ../..
./scripts/start.sh
```

Открыть http://127.0.0.1:8000 . `npm run dev` в apps/web запускает интерфейс с прокси на уже запущенный API. Данные — в игнорируемой `var/`; SQLite наружу не публикуется.

Экспериментальная browser-local сборка, без API для документов и поиска:

```sh
cd apps/web
VITE_BASE_PATH=/evidencerag/ npm run build:local
```

Выходной каталог — игнорируемый `dist-browser/`; при публикации указать фактический project path. Browser-local build хранит документы в OPFS/IndexedDB и не вызывает собственный API. Режим EvidenceRAG включает ограниченные правила извлечения атрибутов и датированных частичных поправок; это не semantic/NLI модель. Пределы см. в `docs/EXPERIMENT_009.md` и `docs/ANSWER_GENERATION_009.md`.

## Что работает

- PDF с текстовым слоем, DOCX с таблицами, UTF-8 TXT/Markdown; лимиты файла и разбор в отдельном процессе с тайм-аутом.
- Лексический BM25-поиск с нормализацией русского текста, точными фрагментами и происхождением.
- Изолированные временные пространства, закрытый cookie, удаление, срок 24 часа.
- Версии и даты, текстовый diff и явно обозначенные сигналы разных значений полей.
- Пять авторских демонаборов, 10 документов, 63 синтетических сценария.
- Четыре основных стратегии поиска, fixed-10 sensitivity и три целевые абляции, CLI-эксперименты с JSON/CSV и трассами.

Совпадение слов не является доказательством. Короткий ответ формируется только для ограниченных грамматических шаблонов с проверкой цитаты и даты; свободные семантические ответы отключены. Сканы получают статус «требуется распознавание». LLM-адаптер доступен только как код для частных экспериментов, не как публичная функция.

## Проверка и эксперименты

```sh
.venv/bin/pytest -q
cd apps/web
npm run check
npm run build
npm run test:e2e
cd ../..
PYTHONPATH=apps/api .venv/bin/python -m packages.research.runner --output experiments/my-run --split test
```

Для E2E нужен локальный сервер и браузер Playwright (`npx playwright install chromium`). С установленным Google Chrome можно выполнить `E2E_BROWSER_CHANNEL=chrome npm run test:e2e`; именно этот вариант проверен локально. Не запускайте E2E против чужого сервиса. Каталог результатов должен быть новым; никакие пороги по тестовому срезу не подбирались. Корпус слишком мал для научного сравнения.

## Документация

Начните с [состояния проекта](docs/PROJECT_STATUS.md), [передачи контекста](docs/HANDOFF_FOR_CHATGPT.md), [результатов тестов](docs/TESTING.md), [исследовательского статуса](docs/RESEARCH_STATUS.md), [аудита run-003/run-004](docs/RESEARCH_AUDIT_006.md), [протокола корпуса](docs/CORPUS_ANNOTATION_PROTOCOL_006.md), [политики cookie](docs/COOKIE_POLICY.md), [литературы](docs/RESEARCH_LITERATURE.md) и [развёртывания](docs/DEPLOYMENT.md). Актуальный offline retrieval-пилот: [experiments/run-004/REPORT.md](experiments/run-004/REPORT.md); новый single-case diagnostic: [experiments/research-rag-pilot-004/REPORT.md](experiments/research-rag-pilot-004/REPORT.md). Все используемые локально данные авторские и синтетические; результаты не подтверждают качество свободных ответов или научное преимущество.

Публичное развёртывание и фактические изменения VPS указаны в [docs/VPS_AUDIT.md](docs/VPS_AUDIT.md). Рабочий сайт — [osnovanie.duckdns.org](https://osnovanie.duckdns.org).
