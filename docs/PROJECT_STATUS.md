# Актуальное состояние — этап 010 (03.11.2026)

Реализовано исправление pipeline достаточности: typed question slots/facts, индекс явных связей редакций, структурная верификация цитат и единый trace/evidence контракт браузерного режима. Контрольный synthetic случай возвращает 9 записей и максимум 5 минут из полной редакции 2026 года, FLAC и 30.11.2026 включительно из межсемейной поправки. Это regression, не независимая оценка. Semantic/NLI judge, сложный парсер норм и преимущество над baseline не заявляются. Отчёты этапа: [аудит](STAGE_010_AUDIT.md), [архитектура](STAGE_010_DESIGN.md), [оценка и ограничения](STAGE_010_EVALUATION.md).

Stage 010/009 answer E2E: 2/2 desktop и 2/2 mobile emulation; migration suite: 3/3 в каждом проекте; Pages base path: 1/1 в каждом проекте. Полный Python набор: 84 passed, один Starlette/httpx deprecation warning. `npm run check` без предупреждений; обычная и Pages browser-local сборки успешны. Независимый corpus/NLI не реализован, поэтому этап не доказывает обобщающую способность. Stage 010 опубликован: source commit `15e5f8417caa5402fa85e2259f7aa0ef9b0050f8`, Pages artifact commit `62efa58cc8e020c18feb9596f962d90de14c4e7f`. Live assets/favicon вернули HTTP 200; Stage 010 browser E2E на публичном HTTPS прошёл 1/1 desktop. Подробности — [GITVERSE_DEPLOYMENT_010.md](GITVERSE_DEPLOYMENT_010.md). Ниже — историческая приёмка Stage 009.

# Актуальное состояние — этап 009 (03.11.2026)

Реализован первый общий (не привязанный к контрольному вопросу) путь rule-based извлечения структурированных атрибутов, датированной применимости и построения короткого цитируемого ответа в браузерном EvidenceRAG. `StructuredClaimEvaluator` работает только на ограниченных грамматических шаблонах; полноценного semantic/NLI judge нет. Сценарий этапа 009 воспроизведён на авторской synthetic fixture: 8 предложений, 25 минут из частичной поправки, электронная сдача; 3 citation claims, 2 source chunks, 1 retrieval iteration, 8.429 ms локального Python pipeline. Это regression, не independent efficacy.

Частичная поправка доступна из отдельной группы только при явном текстовом упоминании даты базовой редакции и маркере изменения. Изменяется только распознанный атрибут. Не моделируются отмены, полная замена отдельной поправкой, юридический приоритет и сложные семантические отношения. Неразрешённый конфликт/пропуск/неизвестная дата приводят к отказу.

Проверки 03.11.2026: `.venv/bin/pytest -q` — 72 passed, 1 Starlette/httpx deprecation warning; Svelte check — 0 ошибок/предупреждений; production build успешен; browser-local A–J E2E 1/1 desktop + 1/1 mobile emulation; browser migration suite 6/6 desktop+mobile. Артефакты: `experiments/stage009/`. Физические Samsung Internet/Safari не проверены.

Stage 009 опубликован на GitVerse Pages: https://seruyvodoley.gitverse.site/evidencerag/ . Artifact commit `0a8b63b`; GitVerse Pages run `1994906` завершился успешно. Live A–J E2E прошёл в Chromium desktop и mobile emulation (1/1 в каждом); live HTML, JS и CSS отвечают HTTP 200. Исходный код этапа — commit `d0743d9`; отчёт публикации — [GITVERSE_DEPLOYMENT_009.md](GITVERSE_DEPLOYMENT_009.md). VPS/VPN/DNS/SSH инфраструктура не менялась.

Подробно: [аудит достаточности](EVIDENCE_SUFFICIENCY_AUDIT_009.md), [разрешение версий](VERSIONED_CLAIM_RESOLUTION_009.md), [построение ответов](ANSWER_GENERATION_009.md), [эксперимент](EXPERIMENT_009.md), [проверки](TESTING.md).

# Историческое состояние — этап 008 (31.10.2026)

Текущий код содержит браузерную сборку, работающую локально через Pyodide/SQLite WASM; публичный адрес GitVerse Pages — https://seruyvodoley.gitverse.site/evidencerag/ . Проект не следует описывать только как прежний VPS MVP. Актуальная приёмка и ограничения приведены в [FINAL_BROWSER_AUDIT_008.md](FINAL_BROWSER_AUDIT_008.md). Stage 008 опубликован Pages commit `15e1241`, GitVerse run `1971623` успешен. На live URL прошли новые acceptance 3/3 desktop + 3/3 mobile emulation и core migration 4/4 desktop + 4/4 mobile emulation. Старые разделы ниже сохраняют историю предыдущих этапов.

Проверки на 31.10.2026: pytest 61 passed; Svelte check 0 ошибок/предупреждений; browser-local build successful; Playwright на опубликованном Stage 008: audit 3/3 desktop + 3/3 mobile emulation; core 4/4 desktop + 4/4 mobile emulation. Production npm audit: 0; полный npm audit: 3 low dev dependency findings.

SSH к проверка указанного владельцем SSH endpoint на порт 22 завершился timeout. Текущее состояние сервера и TunnelDeck не подтверждено; согласно сообщению владельца серверное приложение было отключено им вручную. На сервере в этапе 008 изменений не выполнялось.

# Состояние проекта — 31.10.2026

**Публичный прототип доступен по адресу [osnovanie.duckdns.org](https://osnovanie.duckdns.org).** На VPS работает release `20261031-006`, HTTPS обслуживает уже существующий Caddy. Развёртывание меняло только собственный `evidencerag.service`; Caddy-маршрут и TunnelDeck не менялись.

## Работает

- PDF с текстовым слоем, DOCX, TXT и Markdown: извлечение, индексация, точные выдержки и происхождение до страницы/раздела/позиции.
- Изолированные временные пространства, upload/delete, закрытый cookie и TTL 24 часа.
- Русский FTS5/BM25 поиск, ограничение по версии/дате, текстовый diff, отдельные состояния изменения между редакциями и буквального расхождения внутри одной редакции.
- Пять авторских демо-наборов и offline экспериментальный runner: fixed-k, score-gap adaptive-k, retrieval без judge и прототип EvidenceRAG с абляциями.
- Отдельный local-only stage-006 pipeline для структурированной достаточности, gap/version-directed поиска, ограничений и JSON-трассы; публичное приложение его не вызывает.
- Навигация между `/`, `/documents`, `/compare`, `/method`, favicon SVG/PNG/ICO и мобильная раскладка.

Совпадение слов не доказывает поддержку утверждения. Свободная генерация ответов и semantic judge в публичном приложении отключены. Локальный исследовательский pipeline остаётся `uncertain` без подключённого evaluator; его ограниченный literal answerer может только вернуть точные цитаты по авторскому формальному правилу. OCR, embeddings и публичный LLM endpoint отсутствуют.

## Научная проверка

`experiments/run-004/` содержит 21 синтетический test-вопрос в трёх кластерах и 8 конфигураций. Все варианты нашли обязательные фрагменты; score-gap adaptive-k выбрал меньше фрагментов и показал более высокую evidence precision на этом небольшом наборе. Преимущество EvidenceRAG не показано. Метрики ответов, семантической достаточности, false abstention и faithfulness — `null`, потому что нет answerer и независимого judge. Подробности и точный результат — в [отчёте](../experiments/run-004/REPORT.md) и [методологии](EVALUATION.md).

## Проверки релиза

- Текущая локальная suite: 61 Python unit/integration test прошёл; Svelte check — 0 ошибок и 0 предупреждений; production build успешен для последнего UI-релиза.
- 8 Playwright E2E против публичного HTTPS, включая desktop/mobile: все прошли.
- Серверный smoke: 17/17; public health сообщает `lexical-controller-v2`, семантического judge нет.
- Снимки VPN/Xray-служб, интерфейсов, маршрутов, firewall и Docker networks совпали с предыдущим опубликованным снимком. Caddy не перезапускали и не перенастраивали.

## Ограничения и следующий этап

63 авторских синтетических сценария, только 3 независимых test-кластера, нет real-world набора и двойной экспертной разметки. Нет OCR, semantic entailment, answerer и воспроизведённых сильных baseline. Следующие шаги: собрать независимый датированный корпус, подготовить протокол двойной разметки и оценщика достаточности, затем сравнивать с доступными сильными системами. Эти результаты не подтверждают научную новизну.

Другие эксплуатационные задачи: собственный домен, долгосрочный мониторинг диска и rate limiting за proxy, редактирование метаданных после загрузки, английская локализация и проверка реального Safari. Duck DNS — бесплатная внешняя зависимость.

Подробности: [передача контекста](HANDOFF_FOR_CHATGPT.md), [тесты](TESTING.md), [аудит VPS](VPS_AUDIT.md), [литература](RESEARCH_LITERATURE.md).

## Исследовательский этап 006 — local-only

Проверены ошибки run-003: `false_abstention=1.0` и `answer_exact_match=0` посчитаны при отсутствии answerer и null ответах; конфигурация также включала AppleDouble metadata и dirty checkout. Файл `experiments/pytest-final.txt` обновлён с исторических 32 на фактические 58 актуальных тестов.

Добавлены [исследовательский статус](RESEARCH_STATUS.md), [аудит run-003/run-004](RESEARCH_AUDIT_006.md), [протокол будущего корпуса и разметки](CORPUS_ANNOTATION_PROTOCOL_006.md), модуль `apps/api/evidencerag/research_rag.py` и runner `packages/research/trace_runner.py`. Сохранён исполнившийся trace `experiments/research-rag-pilot-004/`: в одном synthetic случае второй targeted version search дал 1 новый фрагмент и 1 новое формально поддержанное утверждение; всего 2 поисковых вызова, 2 редакции, один literal-citation extract. Ответное качество и семантическая достаточность не измерялись. В run-004 предложенный итеративный метод не добавил новых evidence IDs на 21/21 запросе и уступил score-gap BM25 по evidence precision/среднему размеру контекста.

Подключение semantic/NLI модели, реального versioned corpus, двойная экспертная разметка, парное сравнение обновлённого pipeline с baseline и публичная интеграция остаются незавершёнными. Никакого развёртывания этапа 006 не было; VPS, Caddy, VPN и TunnelDeck не затрагивались. Подробности — [RESEARCH_STATUS.md](RESEARCH_STATUS.md).

## Cookie-уведомление — release-006

Добавлены постоянная информационная плашка и отдельная страница `/cookies`. Они описывают `evidence_session`: first-party cookie, который создаётся только при запуске рабочего пространства, действует 24 часа и имеет `HttpOnly`, `Secure` на HTTPS и `SameSite=Strict`. Аналитических, рекламных и сторонних cookie нет; плашка не выдаёт закрытие за согласие. Подробности — [политика cookie](COOKIE_POLICY.md). Релиз опубликован; проверены публичные HTTPS-ответы `/`, `/cookies` и `/api/health`, чтение страниц не выставило `Set-Cookie`. Это изменение интерфейса не включает аудит остальных правовых требований.

## Stage 007 browser migration — partial local mode

Local execution is integrated in the Svelte product behind `VITE_LOCAL_EXECUTION=true`: Pyodide Worker runs existing Python parser/retrieval/research modules against SQLite WASM FTS5 in OPFS, with an IndexedDB workspace pointer. The production static build passed 4/4 Chromium desktop E2E in a local simulated project subpath, covering base-path navigation/favicon/fallback plus demo, search, comparison, formal ResearchRAG trace, import/export/delete, reload persistence and DOCX/PDF/scan status; tests assert same-origin only and no `/api`. CPython/Pyodide synthetic parity, OPFS harness, 61 Python tests, Svelte check and local static build also passed. Details and artifacts: `BROWSER_ARCHITECTURE.md`, `MIGRATION_REPORT_007.md`, `PYTHON_BROWSER_PARITY.md`, `BROWSER_PERFORMANCE.md`, `BROWSER_PRIVACY_AUDIT.md`, `STATIC_HOSTING.md`, and `VPS_DECOMMISSION_REPORT.md`.

**Migration is not complete.** Build remains opt-in; the current public `osnovanie.duckdns.org` app and FastAPI VPS service are unchanged. No Git remote/static Pages deployment or new URL has been configured; no real Safari/Firefox/mobile checks, full corpus parity, quota/fuzz/crash tests, published-host header/MIME/network audit, or local neural model/OCR exists. No SSH/VPS/Caddy/DNS/firewall/Docker/TunnelDeck operation has been performed. Do not disable EvidenceRAG on VPS until a published replacement and acceptance gates are verified.
