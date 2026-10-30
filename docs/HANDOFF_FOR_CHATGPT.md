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

32 unit/integration проходят; Svelte check 0/0, production build успешно. 8 Playwright E2E локально и 8 против публичного сайта, desktop и mobile Chromium; ширины 320/390/768/1280. VPS smoke 17/17. Снимки в docs/screenshots. Стандартный HTTPS-клиент проверил сертификат, home и health HTTP 200. Локальный короткий load 40/40 при concurrency=4; подробные времена в experiments/local-load.json, не переносить на VPS.

Финальный offline run: `/Volumes/RisingSail/основы программирования/EvidenceRAG/experiments/run-003/`. Сохраняются config/git/source hashes/input hashes, трассы, метрики CSV/JSON, 21 test-case × 8 конфигураций. Четыре baseline и четыре абляции; evidence recall=1 на оцениваемых fixtures, F1 сигналов 0.909, ложный отказ=1 среди достаточных test-вопросов. У versioned нет доказанного преимущества; контекст больше adaptive. Faithfulness null, API cost 0, ответа на test срезе в основном нет. Отрицательный результат не скрывать. Исторические run-001/run-002 сохранены, график по run-001 в quality.svg, методологические ограничения в EVALUATION.md.

LLM API фактически не вызывались. Адаптер проверяет реальные ID/точные цитаты и запрещает свободные выводы без entailment. Его in-memory бюджет не production-ready: нужны ledger/проверенные цены/provider hard cap и согласие. Публичный LLM endpoint сознательно отсутствует.

## VPS без секретов

Ubuntu 24.04.5, x86_64, 1 vCPU, RAM 1963 MiB, free disk около 13 GiB на начало. Собственный user/unit `evidencerag`, backend `127.0.0.1:8077`, release `/opt/evidencerag/releases/20261031-004`, текущий symlink `/opt/evidencerag/current`, приватная SQLite `/var/lib/evidencerag/evidence.sqlite3`. CPUQuota 60%, MemoryMax 640M. Enabled startup; реальный reboot не делался. Измеренная память порядка 54–62 MiB на tiny demo.

Публичный трафик идёт через существующий Docker Caddy `ma-alice-https` в host network; новых контейнеров/сетей не создавали. Владелец явно разрешил в этом чате добавление конкретного временного hostname и graceful reload. Только новый route добавлен к `/root/ma-voice-https/Caddyfile`, backup root-only `/opt/evidencerag/proxy-proposal/Caddyfile.before-publication`. Existing routes сохранены. `bind` нового site совпадает с адресом старого listener: initial wildcard listener давал пустой HTTP 200, это найдено внешним E2E и исправлено. Сертификаты проверялись без отключения TLS verification.

Не менялись VPN/Amnezia/WG/Xray-конфигурации, маршруты, DNS, SSH, firewall, sysctl или Docker networks. Infra snapshots сравнивают состояния/InvocationID, интерфейсы, хеши route/rule/nft/network; совпали. WG/AWG показывают свежие handshakes; end-to-end всех VPN-клиентов не проводился. Не утверждать полную проверку всех домашних маршрутов.

Откат приложения фактически проверен: 003→002→003, health успешен. Схема БД одинакова. Proxy backup валидируется; фактический rollback proxy назад ради демонстрации не делали. См. DEPLOYMENT.md. Из-за отсутствия ensurepip использован uv 0.13.6 из проверенного PyPI wheel в .tools каждого release, системный Python/apt не менялся. Dockerfile/Compose — альтернативы без фактического build.

## Проблемы и следующие действия

Главное научное ограничение — семантический judge и сильный baseline отсутствуют. S2G official CUDA-стенд не запущен; см. `/Volumes/RisingSail/основы программирования/EvidenceRAG/docs/S2G_BASELINE.md`. До статьи расширить независимые корпуса, двойную разметку, date gold и семейный bootstrap; затем измерять selective risk/coverage и budgets. Без этого нельзя обещать «обоснованные свободные ответы» или новизну.

Для следующего продукта: свой домен, мониторинг свободного диска с учётом FTS/WAL, корректное rate limiting за proxy (сейчас общий bucket), редактирование метаданных после upload, английская локализация, реальный Safari/доступность с отдельным инструментом. Данные администраторам VPS доступны, шифрования at-rest нет. OCR и embeddings не реализованы.

Полный npm audit имеет 3 low в dev-цепочке deepmerge/inspector, production 0; pip-audit без известных находок. Предупреждение Starlette TestClient о будущем httpx2 не мешает тестам. Не выдавать отсутствие известных CVE за полную безопасность.

Ключевые документы: `/Volumes/RisingSail/основы программирования/EvidenceRAG/docs/PROJECT_STATUS.md`, `RESEARCH_LITERATURE.md`, `SCIENTIFIC_HYPOTHESIS.md`, `ARCHITECTURE.md`, `EVALUATION.md`, `SECURITY.md`, `VPS_AUDIT.md`, `DEPLOYMENT.md`, `TESTING.md`. Их ссылки внутри репозитория относительные; абсолютный корень приведён выше.

Запуск локально: uv sync; npm ci/check/build в apps/web; ./scripts/start.sh. Offline: PYTHONPATH=apps/api .venv/bin/python -m packages.research.runner --output experiments/<новый-каталог> --split test. Не перезаписывать runs и не запускать длинные эксперименты на VPN-VPS.

## Обновление навигации и значка

Страницы имеют собственные адреса `/`, `/documents`, `/compare`, `/method`. Семантические ссылки поддерживают Ctrl/Cmd-click и контекстное открытие в новой вкладке; History API и popstate обеспечивают Назад/Вперёд, восстановление прокрутки и сохранение форм/результатов между разделами. Backend отдаёт HTML для прямых адресов и обновления. Активный пункт имеет aria-current, после перехода фокус переносится в main. Favicon создан из собственного векторного знака: SVG, PNG, ICO и apple-touch-icon; внешних изображений нет. Production release 20261031-004.

## Короткий бесплатный адрес подключён

Владелец выбрал бесплатный поддомен, самостоятельно вошёл в Duck DNS через GitHub и прошёл CAPTCHA. Имя osnovanie.duckdns.org успешно добавлено в его аккаунт и указывает на VPS. Token не экспортировался и не сохранялся: использована UI-форма. В Caddy к собственному блоку EvidenceRAG добавлен новый hostname, backup Caddyfile.before-duckdns, validate и graceful reload успешны. Внешний HTTPS-клиент проверил сертификат, home и health HTTP 200. Старое имя osnovanie.91-196-32-58.sslip.io оставлено рабочим. Cookies между hostname не переносятся; старые рабочие пространства доступны по старому имени. Подробности — DOMAIN_PLAN.md.
