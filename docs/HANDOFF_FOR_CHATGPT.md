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
