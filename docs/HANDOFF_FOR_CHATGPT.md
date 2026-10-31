# Актуальная передача — этап 008 (31.10.2026)

Публичная browser версия: https://seruyvodoley.gitverse.site/evidencerag/ . Исходный HEAD перед этапом: `904b96a7c3238af522744ebbabf6e65868fac170`; рабочее дерево изначально содержало изменённый пользователем `experiments/e2e-results.json` — сохранять его локальные изменения. Код Stage 008 исправляет стартовый top-k в browser research запросе и добавляет авторское synthetic rule; расширяет e2e audit. Отчёты: [приёмка](FINAL_BROWSER_AUDIT_008.md), [parity](BROWSER_PARITY_008.md), [deployment](GITVERSE_DEPLOYMENT_008.md), [VPS](VPS_DECOMMISSION_008.md), [экспериментальный план](NEXT_EXPERIMENT_PLAN.md).

Успешны: pytest 61, Svelte check, local production build, узкий synthetic Python/Pyodide parity runner, 4 desktop Playwright tests старой опубликованной Stage 007 версии. Stage008 e2e корректируется: ранее demo collection осталась выбранной, из-за чего offline test не искал загруженный документ. Повторить после фикса, затем публиковать и проверять public release. SSH на VPS timed out, нельзя подтвердить состояние VPS/TunnelDeck; без удаления/остановки сервисов. Deploy key GitVerse должен быть project-scoped и храниться вне checkout; владелец подтвердил оставить его для последующих deployment.

---

# Передача контекста: «Основание» / EvidenceRAG

Актуально 31.10.2026. Проект полностью начат с пустой директории и доведён до публичного MVP. Владелец попросил использовать загруженные скиллы: применены frontend-design, sites (с приоритетом явно запрошенного VPS перед cloud hosting) и web-design-guidelines. Три дизайн-концепции и выбор цифрового архива задокументированы.

## Назначение и научная постановка

Сервис помогает проверять формулировки в документах, видеть происхождение, изменения редакций и недостаток данных. Это отдельное RAG-направление, не FlySwarm. Тема для обсуждения с Михалёвым: адаптивное формирование доказательного контекста с версиями, достаточностью и затратами. Научная новизна/превосходство пока не подтверждены; согласования научной формулировки руководителем не было. Изученные S2G-RAG, RINSE, VersionRAG и TimelyRAG существенно перекрывают первоначальную идею, поэтому гипотеза сужена до измеримого компромисса применимости/бюджета/отказа.

## Где сайт и код

Публично: https://osnovanie.duckdns.org . Это бесплатный поддомен Duck DNS в аккаунте владельца, своего домена второго уровня нет. HTTPS и реальные публичные E2E проверены.

Локальный корень: `/Volumes/RisingSail/основы программирования/EvidenceRAG`. Репозиторий Git локальный; GitHub remote не создан и push не выполнялся. Секретов/документов пользователей в Git нет. Не брать чувствительные данные из соседнего TunnelDeck.

Ключевые исходники (абсолютные пути):

- `/Volumes/RisingSail/основы программирования/EvidenceRAG/apps/api/evidencerag/main.py` — API, middleware, сессии, upload/search/compare.
- `/Volumes/RisingSail/основы программирования/EvidenceRAG/apps/api/evidencerag/parser.py` — bounded subprocess parsing.
- `/Volumes/RisingSail/основы программирования/EvidenceRAG/apps/api/evidencerag/store.py` — SQLite/FTS5, BLOB originals, TTL/изоляция.
- `/Volumes/RisingSail/основы программирования/EvidenceRAG/apps/api/evidencerag/retrieval.py` — лексический контроллер, сигналы конфликтов, формальная политика.
- `/Volumes/RisingSail/основы программирования/EvidenceRAG/apps/api/evidencerag/llm.py` — отключённый experiment-only адаптер; нет публичного endpoint.
- `/Volumes/RisingSail/основы программирования/EvidenceRAG/apps/web/src/App.svelte` и `style.css` — пользовательский интерфейс.
- `/Volumes/RisingSail/основы программирования/EvidenceRAG/packages/research/runner.py` — независимый offline CLI.
- `/Volumes/RisingSail/основы программирования/EvidenceRAG/datasets/demo/catalog.json` и `datasets/evaluation/cases.json` — авторские демо и эталоны.
- `/Volumes/RisingSail/основы программирования/EvidenceRAG/tests/test_system.py`, `tests/test_parser_timeout.py`, `apps/web/e2e/workbench.spec.ts` — тесты.

Стек: Svelte 5 + TS + Vite static, Python 3.12 FastAPI, SQLite FTS5 BM25 и русская морфология pymorphy3. SvelteKit SSR не нужен; frontend раздаётся FastAPI без Node-процесса на VPS. 1100-символьные chunks с page/locator/offset, до 20 документов/40 МБ на workspace. Cookie HttpOnly/Secure/SameSite Strict, SHA-256 токена в БД, TTL 24 часа и minute cleanup.

## Реально реализовано

PDF с текстом, DOCX с таблицами, TXT/Markdown; UTF-8; scan PDF needs_ocr; загрузка с версией/датой/группой; реальные FTS-поиск/источники/original download/delete; текстовый diff, key:value difference signals, явные состояния no_results/insufficient/unverified/potential_conflict/confirmed_formal. Один доверенный демовопрос с обязательной цитатой и конкретной версией даёт формальный вывод. Поиск не является семантической верификацией. Приватные uploads не могут передать свои «правила доказательства».

5 корпусов, 10 авторских файлов CC0, 63 synthetic scenarios. Включены изменяющиеся версии, внутренний конфликт, missing evidence, лексическая ловушка и multi-document question. Group-disjoint train/device, dev/api, test/service+conflict+bundle. Нет представительского научного benchmark.

## Проверки и результаты

39 unit/integration проходят; Svelte check 0/0, production build успешно. 8 Playwright E2E локально и 8 против текущей публичной версии, desktop и mobile Chromium; ширины 320/390/768/1280. VPS smoke 17/17. JSON текущих публичных E2E — `experiments/e2e-release-005.json`. Стандартный HTTPS-клиент проверил сертификат, главную и health HTTP 200. Локальный короткий load 40/40 при concurrency=4; подробные времена в experiments/local-load.json, не переносить на VPS.

Финальный offline run: `/Volumes/RisingSail/основы программирования/EvidenceRAG/experiments/run-004/`. Чистый source commit `8e3e704a68d9abc7f99c29927208d9c071366dad`, 21 synthetic test-question × 8 configurations, три evaluation clusters. Источники/входы имеют SHA-256, `git_dirty_tracked_before_run=false`. Обязательные spans покрыты полностью. Score-gap adaptive-k: evidence precision 0.702, 2.095 chunks; прототип EvidenceRAG: 0.494, 2.810 chunks. Только три независимые группы; преимущество метода не установлено. Ответчик/semantic judge отсутствуют, поэтому answer quality/false abstention/faithfulness — null. Исторические run-001–003 не перезаписаны; старый False Abstention=1.0 методологически недействителен. Подробности — EVALUATION.md.

LLM API фактически не вызывались. Адаптер проверяет реальные ID/точные цитаты и запрещает свободные выводы без entailment. Его in-memory бюджет не production-ready: нужны ledger/проверенные цены/provider hard cap и согласие. Публичный LLM endpoint сознательно отсутствует.

## VPS без секретов

Ubuntu 24.04.5, x86_64, 1 vCPU, RAM 1963 MiB, свободное место около 13 GiB при последнем обновлении. Собственный user/unit `evidencerag`, backend `127.0.0.1:8077`, release `/opt/evidencerag/releases/20261031-006`, текущий symlink `/opt/evidencerag/current`, приватная SQLite `/var/lib/evidencerag/evidence.sqlite3`. CPUQuota 60%, MemoryMax 640M. Enabled startup; реальный reboot не делался. Память последнего измерения около 64 MiB (из release-005).

Публичный трафик идёт через существующий Docker Caddy `ma-alice-https` в host network; новых контейнеров/сетей не создавали. Владелец явно разрешил в этом чате добавление конкретного временного hostname и graceful reload. Только новый route добавлен к `/root/ma-voice-https/Caddyfile`, backup root-only `/opt/evidencerag/proxy-proposal/Caddyfile.before-publication`. Existing routes сохранены. `bind` нового site совпадает с адресом старого listener: initial wildcard listener давал пустой HTTP 200, это найдено внешним E2E и исправлено. Сертификаты проверялись без отключения TLS verification.

Не менялись VPN/Amnezia/WG/Xray-конфигурации, маршруты, DNS, SSH, firewall, sysctl или Docker networks. Infra snapshots сравнивают состояния/InvocationID, интерфейсы, хеши route/rule/nft/network; совпали. WG/AWG показывают свежие handshakes; end-to-end всех VPN-клиентов не проводился. Не утверждать полную проверку всех домашних маршрутов.

Откат приложения ранее проверен: 003→002→003, health успешен. Для установки 005 схема БД не менялась, installer содержит rollback для собственного symlink/unit; после успешного health откат не понадобился. Proxy backup валидируется; rollback proxy ради демонстрации не делали. См. DEPLOYMENT.md. Из-за отсутствия ensurepip использован uv 0.13.6 из проверенного PyPI wheel в `.tools` каждого release; для 005 бинарник скопирован из известного текущего релиза, его SHA-256 включён в manifest. Системный Python/apt не менялся. Dockerfile/Compose — альтернативы без фактического build.

## Проблемы и следующие действия

Главное научное ограничение — семантический judge и сильный baseline отсутствуют. S2G official CUDA-стенд не запущен; см. `/Volumes/RisingSail/основы программирования/EvidenceRAG/docs/S2G_BASELINE.md`. До статьи расширить независимые корпуса, двойную разметку, date gold и семейный bootstrap; затем измерять selective risk/coverage и budgets. Без этого нельзя обещать «обоснованные свободные ответы» или новизну.

Для следующего продукта: свой домен, мониторинг свободного диска с учётом FTS/WAL, корректное rate limiting за proxy (сейчас общий bucket), редактирование метаданных после upload, английская локализация, реальный Safari/доступность с отдельным инструментом. Данные администраторам VPS доступны, шифрования at-rest нет. OCR и embeddings не реализованы.

Полный npm audit имеет 3 low в dev-цепочке deepmerge/inspector, production 0; pip-audit без известных находок. Предупреждение Starlette TestClient о будущем httpx2 не мешает тестам. Не выдавать отсутствие известных CVE за полную безопасность.

Ключевые документы: `/Volumes/RisingSail/основы программирования/EvidenceRAG/docs/PROJECT_STATUS.md`, `RESEARCH_LITERATURE.md`, `SCIENTIFIC_HYPOTHESIS.md`, `ARCHITECTURE.md`, `EVALUATION.md`, `SECURITY.md`, `VPS_AUDIT.md`, `DEPLOYMENT.md`, `TESTING.md`. Их ссылки внутри репозитория относительные; абсолютный корень приведён выше.

Запуск локально: uv sync; npm ci/check/build в apps/web; ./scripts/start.sh. Offline: PYTHONPATH=apps/api .venv/bin/python -m packages.research.runner --output experiments/<новый-каталог> --split test. Не перезаписывать runs и не запускать длинные эксперименты на VPN-VPS.

## Обновление навигации и значка

Страницы имеют собственные адреса `/`, `/documents`, `/compare`, `/method`. Семантические ссылки поддерживают Ctrl/Cmd-click и контекстное открытие в новой вкладке; History API и popstate обеспечивают Назад/Вперёд, восстановление прокрутки и сохранение форм/результатов между разделами. Backend отдаёт HTML для прямых адресов и обновления. Активный пункт имеет aria-current, после перехода фокус переносится в main. Favicon создан из собственного векторного знака: SVG, PNG, ICO и apple-touch-icon; внешних изображений нет. Release 005 сохраняет эту навигацию.

## Короткий бесплатный адрес подключён

Владелец выбрал бесплатный поддомен, самостоятельно вошёл в Duck DNS через GitHub и прошёл CAPTCHA. Имя osnovanie.duckdns.org успешно добавлено в его аккаунт и указывает на VPS. Token не экспортировался и не сохранялся: использована UI-форма. В Caddy к собственному блоку EvidenceRAG добавлен hostname при публикации более ранней версии; backup Caddyfile сохранён. Для release-005 и release-006 Caddy не изменялся. Внешний HTTPS-клиент проверил сертификат, главную, `/cookies` и health HTTP 200. Старое имя osnovanie.91-196-32-58.sslip.io оставлено рабочим. Cookies между hostname не переносятся; старые рабочие пространства доступны по старому имени. Подробности — DOMAIN_PLAN.md.

## Итерация научного ядра и release-005

| Проверяемое утверждение | Реализация / артефакт | Проверка | Результат / ограничение |
|---|---|---|---|
| История редакций отделена от конфликта в той же редакции | `apps/api/evidencerag/retrieval.py::analyze_field_changes`; `/api/compare` | 39 pytest, `scripts/vps_smoke.py` 17/17, public E2E 8/8 | Буквальные сигналы поля; не семантическое противоречие |
| Baselines и ablations имеют общую схему | `packages/research/runner.py`; `experiments/run-004/` | commit/source/input hashes, deterministic traces | BM25 score-gap — собственная heuristic; без judge |
| Provenance IDs устойчивы, trace объясняет выбор | `stable_document_id`, `stable_evidence_id`, runner `traces.json` | тест стабильных ID и воспроизводимости | Не удостоверяет подлинность или доверие к источнику |
| Публичный релиз проверен по manifest | `deploy/release-manifest.json`, release-005 | archive + 78 file checksums, public health, smoke 17/17, E2E 8/8 | Перезапущен только собственный `evidencerag.service`; Caddy/VPN/firewall не менялись |

Run-004 и payload релиза построены из commit `8e3e704`; последующие изменения этого передаточного файла и smoke-script не меняли исследовательское ядро или опубликованный bundle. Не перезаписывать run-001–003, прошлые snapshots и существующие production releases. Следующий исследовательский шаг — независимый корпус с двойной разметкой; порог по текущему test split не подбирать.

## Cookie notice

В release-006 опубликованы cookie-уведомление и маршрут `/cookies`; они описывают `evidence_session` сроком до 24 часов, атрибуты HttpOnly/Secure/SameSite=Strict и отсутствие аналитики/трекеров. Дата редакции политики — 31.10.2026. Локальные `npm run check` и `npm run build` прошли. Публичные HTTPS GET `/`, `/cookies`, `/api/health` вернули 200; чтение страницы не установило cookie. Upload/search не запускались. При публикации перезапущен только собственный `evidencerag.service`; Caddy, VPN, firewall и маршруты не менялись. Политика не расширяет аудит на прочие правовые требования.

## Stage 006: bounded research RAG pipeline (local-only)

Актуальная незакоммиченная работа в этой итерации — `apps/api/evidencerag/research_rag.py`, `packages/research/trace_runner.py`, `tests/test_research_rag.py` и документы ниже. Публичное приложение и production bundle не менялись, deployment не выполнялся.

- `SufficiencyAssessment`: `sufficient / insufficient / conflicting / uncertain`, exact evidence IDs, structured gaps, version/date constraints, no confidence пока не подключён калиброванный evaluator.
- `FormalRuleEvaluator` положителен только по authored exact quote + allowed version/date. `UnavailableSemanticEvaluator` остаётся `uncertain`; `InjectedSemanticEvaluator` требует `consent=True`, проверяет схему и IDs, при network/model failure или malformed response fail-closed в `uncertain`. Ни NLI weights, ни provider semantic adapter не подключены.
- `run_pipeline`: `retrieve_gap`, `check_version`, `expand_top_k`, stop on sufficient/conflict/no results/no new evidence chunks/no new supported claims/repeated query/iteration, chunk or time budget. Trace separates newly seen source revisions, evidence chunks and supported claims. `EvidenceStoreBackend` is workspace-scoped and uses stable IDs.
- `LiteralExtractAnswerGenerator` emits only a direct source quote after formal sufficiency; `validate_answer` checks source ID and exact quote and rejects paraphrase. This is not general-purpose answer generation or semantic verification.
- Reproducible actual execution: `experiments/research-rag-pilot-004/`. Synthetic service revisions 2024/2025; two SQLite/FTS5 calls; second call found one new revision and evidence chunk and one formal-rule supported claim; final answer is the literal “Срок возврата: 30 дней”. No API calls. This is one diagnostic trace, no comparative result.
- Audit verified run-003's false-abstention/exact-match metrics invalid without an answerer, dirty source, and AppleDouble hashes; run-004 proposed produced no new evidence IDs in its second round on all 21 cases. Full detail: `docs/RESEARCH_AUDIT_006.md`.
- Current full tests: 61 passed, 0 failed, 0 skipped, one Starlette deprecation warning. `experiments/pytest-final.txt` is updated. Frontend, E2E, production API and VPS were not retested for this backend-only stage.
- Status, known literature, gaps and publication criteria: `docs/RESEARCH_STATUS.md`. Source and manual double-annotation protocol: `docs/CORPUS_ANNOTATION_PROTOCOL_006.md`; candidate Python official docs were reviewed for provenance/license but not imported or annotated.

## Stage 007: partial browser migration

User requested browser-local execution, free static hosting and—after all gates pass—safe EvidenceRAG decommission while preserving TunnelDeck. The product now has an opt-in local build (`VITE_LOCAL_EXECUTION=true`), an actual Worker integration, Pyodide running existing Python parser/retrieval/research modules, SQLite WASM 3.54.1 FTS5 + OPFS, IndexedDB workspace pointer, local CRUD, import/export and trace UI. Default build and currently public `osnovanie.duckdns.org` remain server-backed.

- `apps/web/e2e/local-migration.spec.ts` and `base-path.spec.ts`: four passed Chromium desktop scenarios against the production static output mounted at `/evidencerag/` (demo/search/source/version comparison/research trace; upload/reload/search/export/delete/import; DOCX/PDF/scan; project-prefix route, favicon and direct-route fallback). Same-origin/no `/api` assertions pass. Report: `experiments/browser-migration-007/product-e2e-subpath-results.json`.
- `.venv/bin/pytest -q`: 61 passed; `npm run check --prefix apps/web`: clean; `VITE_BASE_PATH=/evidencerag/ npm run build:local --prefix apps/web`: successful (`dist-browser` ~34 MB; vendor ~29 MB). Output is a sample project path and must be rebuilt using the actual GitVerse repo path before publication.
- Narrow CPython/Pyodide synthetic parity probe passes; maximum FTS BM25 absolute delta `2.117582368135751e-22` at tolerance `1e-18`. Separate Chromium OPFS harness passes persistence and deletion checks. Neither constitutes full parity/coverage.
- Static hosting is not configured: this checkout has no Git remote, GitVerse repository/workflow, or deployed URL. Local static mount checked MIME/WASM and the 404 fallback, but actual host response headers, TLS/cache and network privacy remain untested; mobile/Firefox/Safari, quotas, fuzz/crash recovery and large corpus are untested. No local neural model or OCR is present.
- No SSH connection or VPS/Caddy/DNS/firewall/Docker/TunnelDeck/VPN changes occurred; service and data remain untouched. Do not disable VPS until a verified static deployment and acceptance gates pass.

Use `docs/BROWSER_ARCHITECTURE.md`, `docs/MIGRATION_REPORT_007.md`, `docs/PYTHON_BROWSER_PARITY.md`, `docs/BROWSER_PRIVACY_AUDIT.md`, `docs/STATIC_HOSTING.md`, and `docs/VPS_DECOMMISSION_REPORT.md` for detailed coverage. Stage 007 does not establish semantic quality or scientific novelty.

Do not claim semantic sufficiency, correctness of generated answers, better retrieval, or novelty. Next required work is a small immutable real-document corpus, double annotation, an evaluated semantic/NLI backend, and paired baseline/ablation runs with denominators and family-aware uncertainty.
