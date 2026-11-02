# Актуальный исследовательский статус — этап 009 (03.11.2026)

Stage 009 добавил ограниченный детерминированный механизм для структурированных атрибутов, явной частичной поправки, отказа при конфликте/unknown date и механической проверки quote-to-fact. Он не является NLI/semantic judge. Авторский known-case regression A дал 3/3 ожидаемых атрибута, 2 chunks/1 итерацию; A–J synthetic branch tests прошли. Эти случаи созданы для отладки и не используются как независимое свидетельство качества. См. [audit](EVIDENCE_SUFFICIENCY_AUDIT_009.md), [version resolution](VERSIONED_CLAIM_RESOLUTION_009.md), [answer generation](ANSWER_GENERATION_009.md), [experiment](EXPERIMENT_009.md).

Сравнение Fixed-k / Adaptive-k / Sufficiency-guided / Proposed на новом независимом annotated corpus не выполнено. Run-004 историчен и не измеряет answer quality. Научное преимущество и новизна не установлены. Публичная версия на этом срезе ещё Stage 008; VPS/TunnelDeck не тронуты.

# Исторический исследовательский статус — этап 008 (31.10.2026)

Новые результаты Stage 008 не подтверждают эмпирическое преимущество метода. Python ядро остаётся источником воспроизводимых научных запусков; браузер — локальная пользовательская реализация. Текущие границы parity и план независимого эксперимента описаны в [BROWSER_PARITY_008.md](BROWSER_PARITY_008.md) и [NEXT_EXPERIMENT_PLAN.md](NEXT_EXPERIMENT_PLAN.md). Новая трасса demo (если успешно воспроизведена) является авторским синтетическим smoke test и не меняет исторические run-003/run-004/Stage 006.

# История исследовательского статуса EvidenceRAG — этап 006

Обновлено 31.10.2026. Это честный журнал состояния, не планируемый результат статьи.

## Тема и гипотеза

**Рабочая тема:** адаптивное управление поиском доказательств в RAG с явной применимостью версий документов.

**Гипотеза:** при одинаковом бюджете структурированная оценка достаточности, явное описание информационного пробела и проверка версии могут иногда повысить долю ответов, подтверждённых применимыми источниками, по сравнению с фиксированным и адаптивным top-k. Возможный выигрыш должен быть измерен вместе с лишними поисками, контекстом и отказами. Подтверждённой новизны нет.

## Исследовательские вопросы и текущие ответы

| Вопрос | Текущий статус |
|---|---|
| RQ1. Улучшает ли оценка достаточности отбор доказательств? | Неизвестно: нет semantic/NLI judge и independent gold на реальном корпусе. Авторское formal-rule покрытие не является общей оценкой достаточности. |
| RQ2. Приносит ли целевой поиск нужный фрагмент? | В одном исполненном синтетическом диагностическом случае — да: второй запрос принёс 1 новый фрагмент из редакции 2025 и 1 новое formal-rule утверждение. В run-004 iterative expansion не принёс новых ID на 21/21 вопросе. Обобщения нет. |
| RQ3. Уменьшает ли учёт версий ответы по устаревшим источникам? | Не измерено на ответах. В run-004 абляция без версий пропустила единственное размеченное version-change signal (1 положительный случай); это тест сигнала, не правильности конечного ответа. |
| RQ4. Улучшает ли совместный метод ответ при равных затратах? | Неизвестно: ответчик общего назначения и сопоставимый semantic judge отсутствуют. |
| RQ5. Где метод уступает baseline? | В run-004 BM25 score-gap baseline дал лучшую macro evidence precision при меньшем среднем контексте, а proposed-контроллер совпал с абляцией без итераций по итоговым ID и потратил дополнительные поисковые вызовы. Подробнее в [аудите](RESEARCH_AUDIT_006.md). |

## Что опубликовано и где граница новизны

- [Adaptive-k, EMNLP 2025](https://aclanthology.org/2025.emnlp-main.1017/) выбирает число passages по порогу similarity. Наш BM25 score-gap — адаптация идеи порогового отбора, не репликация.
- [S2G-RAG, ACL 2026](https://aclanthology.org/2026.acl-long.1185/) уже изучает learned sufficiency judgement, структурированные gaps и следующий retrieval. Наличие у нас аналогичного цикла не является новизной.
- [TimelyRAG, Findings EMNLP 2026](https://aclanthology.org/2026.findings-emnlp.398/) рассматривает временное ранжирование evolving documents.
- [ProStruct-RAG, EMNLP 2026](https://aclanthology.org/2026.emnlp-main.294/) использует timestamped propositions и отношения update/contradict/support.
- [VersionRAG](https://arxiv.org/abs/2510.08109) рассматриваем как препринт; peer-reviewed venue в текущем обзоре не подтверждён.

Версионность, iterative gap search, adaptive-k и конфликтный анализ уже встречаются в литературе. Возможный будущий вклад может оказаться в методике оценки для конкретного класса документов, временной области применимости или изучении компромиссов отказа/затрат — только если результаты независимого теста это покажут. См. [карту литературы](RESEARCH_LITERATURE.md).

## Реально реализовано

1. Исходный публичный продукт и lexical runner сохраняют прежнее поведение. Публичный `/api/search` и UI не подключены к экспериментальным компонентам.
2. Добавлен автономный исследовательский pipeline в `apps/api/evidencerag/research_rag.py`: структурированный контракт sufficiency, explicit `uncertain`, точные формальные правила, gap/version-directed next actions, бюджет, дедупликация, fail-closed ответы и JSON trace.
3. `EvidenceStoreBackend` использует существующее workspace-scoped SQLite/FTS5 хранилище и стабильные IDs. Семантический интерфейс принимает подключаемый backend только при явном `consent=True`; его отсутствие, ошибка или отказ не переходит в `sufficient`.
4. Answerer заменяемый. Нынешний answerer только выдаёт дословные формально поддержанные выдержки. Валидация проверяет ID/текст цитаты и не пропускает paraphrase как семантически верный ответ.
5. Диагностические тесты используют mock/test-double только в unit-тестах; они не являются измерением качества модели.

Не реализованы/не проверены: конкретная NLI-модель, provider adapter с жёстким бюджетным ledger, semantic calibration, answerer свободного текста, независимая экспертная разметка, внешний corpus snapshot, production API endpoint.

## Эксперименты и реальные числа

### Исторический retrieval-пилот run-004

| Метод | Macro evidence precision | Evidence recall | Required-span coverage | Среднее число фрагментов |
|---|---:|---:|---:|---:|
| Fixed-k (5) | 0.505 | 1.000 | 1.000 | 2.619 |
| Adaptive-k score-gap (BM25) | **0.702** | 1.000 | 1.000 | **2.095** |
| Sufficiency-guided без judge | 0.490 | 1.000 | 1.000 | 2.905 |
| Proposed EvidenceRAG | 0.494 | 1.000 | 1.000 | 2.810 |

Для каждой стратегии было 21 query в 3 document clusters. Evidence precision/recall — среднее по 14/21 queries с применимым gold evidence set. Required-span coverage — среднее по размеченным вопросам с обязательными строками (см. `metrics.csv`). Confusion counts для same-edition signals: 4 положительных gold case; для dated-version signals: 1 положительный case. Ошибка в одну задачу сильно меняет эти числа. Не публиковать p-value или CI как обобщаемый результат при трёх кластерах.

### Исполненный трассировочный случай stage-006

`experiments/research-rag-pilot-004/` — один run на двух синтетических редакциях. 2 retrieval-вызова, 2 новых evidence chunks из 2 revisions, 1 новая поддержанная формальным правилом claim, 1 прямой цитатный extract. Ответ совпадает с авторским правилом, поэтому нельзя считать его независимой оценкой answer correctness. Нет semantic model, baseline comparison, генерации свободного ответа, статистики.

Метрики правильности и подтверждённости конечных ответов в обоих результатах не измерены. Единственный ответ пилота — `Срок возврата: 30 дней`, verbatim из synthetic version `2025`; label в трассе `literal_citation_checked`, не `semantic_verified`.

## Что нельзя заявлять в научной статье

- Что EvidenceRAG превосходит Fixed-k, Adaptive-k, S2G-RAG или другие опубликованные методы.
- Что lexical coverage, BM25 score, regex field signal или authored rule обеспечивают semantic entailment.
- Что один синтетический trace подтверждает переносимость, answer correctness или новизну.
- Что `run-003` измерил false-abstention или accuracy генератора.
- Что 168 трасс — 168 независимых статистических наблюдений.
- Что эксперимент на одном VPS/Linux или Mac представляет production throughput без отдельного протокола.

## Что нужно до полноценной публикации

1. Зафиксировать небольшой независимый версионный корпус с source snapshots, лицензией, хешами и происхождением.
2. Двойная независимая разметка вопросов, необходимых evidence sets, временной применимости, конфликтов и рационального отказа; задокументировать арбитраж.
3. Выбрать и оценить реальный semantic/NLI evaluator, не используя его для построения собственного gold; отдельно показать его confusion matrix и калибровку.
4. Согласовать один answerer для всех методов либо начать с retrieval/sufficiency, где качество не смешивается с generation.
5. Реализовать сравнение Fixed-k, точной/явно адаптированной Adaptive-k, sufficiency-guided и proposed при одинаковых корпусе, query, evidence budgets и процедуре оценки; добавить ablations.
6. Проводить paired analysis по query и учитывать family clusters. Пререгистрировать метрики/правила обработки `uncertain` и отказов; CI/проверки публиковать только с достаточным количеством независимых семейств.
7. Разобрать ошибки и негативные исходы. Новизну формулировать только после анализа первичной литературы и результата сравнения.

## Stage 007 browser migration status

The product now contains an opt-in browser-local build. It runs the existing Python parser, morphology, FTS/retrieval and research controller in Pyodide inside a Worker, backed by SQLite WASM 3.54.1 and local OPFS/IndexedDB storage. Selected desktop Chromium product flows and one narrow Python/Pyodide synthetic parity probe pass. Results and coverage limits are in `MIGRATION_REPORT_007.md`, `PYTHON_BROWSER_PARITY.md`, and `BROWSER_PRIVACY_AUDIT.md`.

The browser migration is a product/runtime study and does not change scientific claims above. Full parity is not established; the public app remains server-backed because no static host/repository is configured, and there is no published browser-local URL. No local semantic model, OCR, or general answer generation exists. The VPS service, stored data, backups, Caddy, TunnelDeck and VPN were not changed. These product tests are not evidence of semantic quality, answer correctness, retrieval superiority or scientific novelty.
