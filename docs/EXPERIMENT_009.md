# Этап 009 — воспроизводимость и результаты

Дата выполнения: 03.11.2026 (Asia/Krasnoyarsk). URL текущего браузерного продукта: https://seruyvodoley.gitverse.site/evidencerag/ . Stage 009 опубликован: GitVerse Pages artifact commit `0a8b63b`, CI run `1994906` успешен; live A–J E2E прошёл на desktop и mobile Chromium emulation. Подробности и HTTP asset checks: [GITVERSE_DEPLOYMENT_009.md](GITVERSE_DEPLOYMENT_009.md).

## Известный сценарий (только regression)

Документы и gold-поля хранятся в `experiments/stage009/fixtures/ifiyak-known-case.json`. Это авторская синтетическая копия известного пользовательского случая; он исключён из независимого efficacy score.

Runner использует настоящий `EvidenceStoreBackend`/SQLite FTS5, русские query terms, структурированный evaluator и citation validator. Последний trace: `experiments/stage009/run-002/trace.json`; конфигурация, исходные SHA-256 и среда: `config.json`; краткий результат: `result.json`. `run-001` сохранён как предыдущий прогон.

| Метрика known-case regression | Измерено |
|---|---:|
| Оценка / ответ | `sufficient` / `answered` |
| Значения совпали с авторской fixture | 3 из 3 атрибутов |
| Подтверждающие citations | 3 |
| Выбранные chunks | 2 |
| Retrieval/evaluator iterations | 1; второй проход не понадобился |
| Время Python pipeline | 8.429 ms в последнем локальном запуске |
| Внешняя модель / сеть | нет |

Значения: 8 предложений и электронный вид из редакции 2026 от 01.09.2026; 25 минут из поправки 15.10.2026. Вопросы на 01.10.2026 и 01.10.2025, пропуск, конфликт, переформулировка, частичная поправка, независимая область, лексическая ловушка и неизвестная дата проверены тестами A–J.

## Независимый контроль и пределы метрик

Тест H — маленький авторский технический регламент, не независимый real-world benchmark. Все десять сценариев в `tests/test_stage009_structured_answers.py` синтетические и известны разработчику. Они проверяют ветви программы, не статистическое качество/переносимость.

Не выполнялось сопоставимое новое сравнение Fixed-k / Adaptive-k / Sufficiency-guided / Proposed на независимом gold: готовая разметка run-004 содержит lexical evidence spans, но не атрибуты/применимость/правильность ответов, а для Stage 009 нет независимого NLI judge. Измерять answer precision/recall, faithfulness, semantic sufficiency, false refusal, calibration или преимущество по этим fixture было бы подгонкой. Исторические метрики run-004 не изменялись.

Измерение 8.429 ms — одна локальная Python/SQLite синтетическая трасса, не benchmark. Browser-local E2E known scenario: desktop 10.4 s, mobile emulation 10.1 s в локальном прогоне; live GitVerse A–J E2E: desktop 24.4 s и mobile emulation 21.3 s (общая длительность теста с загрузкой runtime). Это не чистое время алгоритма и не измерение на Samsung/реальном Android. Live JSON: `experiments/stage009/browser-live-{desktop,mobile}.json`.

## Проверки

- `.venv/bin/pytest -q`: финальный прогон 72 passed, 0 failed, одно предупреждение Starlette/httpx; JUnit: `experiments/stage009/python-junit.xml`.
- `npm run check`: 0 ошибок/предупреждений; `npm run build`: успешно.
- Browser-local production bundle, mounted под `/evidencerag/`; A–J `answer-generation-009.spec.ts`: desktop 1/1, mobile Chromium emulation 1/1. Проверены multi-document answer, source links, conflict/refusal, no API/external requests. JSON: `experiments/stage009/browser-e2e-desktop.json`, `browser-e2e-mobile.json`.
- `local-migration.spec.ts`: desktop+mobile 6/6; demo, import/export/delete, DOCX/PDF and no `/api`. JSON: `browser-migration-e2e.json`.
- Samsung Internet и Safari физически не проверены. GitVerse Pages Stage 009 подтверждён: run `1994906` успешен, live A–J прошёл desktop/mobile Chromium emulation; физические Samsung Internet и iOS Safari не проверялись.

## Фальшивые ответы и отказы

Обнаруженная ошибка ранней версии этапа: browser UI передавал `initial_top_k=1`; на трёх документах он считал основную редакцию достаточной до retrieval поправки. E2E поймал ответ 20 вместо 25. Параметр удалён, используется обычный начальный k=5; после исправления известный тест проходит. Это исправление предотвращает конкретную ошибку, но не доказывает полноту retrieval в больших корпусах.

Извлечение формы сдачи основано на глагольных regex: негативные/условные контексты могут быть ошибочно распознаны. При конфликтующих одинаково датированных значениях evaluator отказывает. При неизвестной дате отказывает. Для неподдерживаемой формулировки без атрибутного шаблона semantic answer не строится.

## Научная интерпретация

Stage 009 добавляет детерминированные правила извлечения явных атрибутов, частичную датированную замену и механический source check — не новую научную гипотезу и не семантическую модель. Версионные правила и sufficiency-guided retrieval уже изучались в литературе. Ни превосходство над S2G-RAG, ни новизна, ни фактическая верность на свободных документах не установлены.
