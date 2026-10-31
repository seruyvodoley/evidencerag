# Python / browser parity — этап 008

## Реализация

Browser build `VITE_LOCAL_EXECUTION=true` исполняет существующие Python parser, morphology, SQLite `EvidenceStore`, retrieval и `research_rag.py` через Pyodide worker. Индекс — SQLite WASM/FTS5 в OPFS. API-совместимость проходит через `apps/web/src/browser-local-api.ts` и `apps/web/src/local-engine.worker.ts`; одинаковые модули Python используются в API и browser runtime. В браузерный research-запрос добавлена `initial_top_k: 1`, чтобы воспроизвести Stage 006 исходную диагностическую конфигурацию, не меняя hosted/server режим.

`experiments/final-audit-008/python-browser-parity.json` получен командой `npm run audit --prefix experiments/browser-migration-007`. Исторический detailed report `experiments/browser-migration-007/hybrid-parity.json` фиксирует на синтетической выборке CPython/Pyodide parity для parser, morphology и controller probe; SQLite WASM/native обе 3.54.1, абсолютная разница BM25 score `2.12e-22` при tolerance `1e-18`.

## Реальное browser replay

`apps/web/e2e/audit-008.spec.ts` воспроизводит запрос Stage 006 `Какой срок возврата после изменений?`: первый top-1 не покрывает нужный признак, контроллер должен запросить нужную редакцию и на втором шаге вернуть дословную цитату `Срок возврата: 30 дней`. Синтетическое правило добавлено только в `datasets/demo/catalog.json`; это demo fixture, не независимый benchmark. Трасса сохраняется в `experiments/final-audit-008/stage-006-browser-trace.json` при успешном запуске.

Не следует называть эти результаты полной математической эквивалентностью приложения или доказательством качества. Модель/semantic entailment judge и answer generator отсутствуют; оценка достаточности — формальный/эвристический controller и авторские правила demo; независимого gold set и полной парной проверки всех ветвей нет. Adaptive-k, fixed-k, conflict/version rules и Python research ядро существуют, но все сочетания параметров не прошли широкий browser differential suite этого этапа.
