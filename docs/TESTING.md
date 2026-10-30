# Проверки и результаты

31.10.2026. Release `20261031-005`, macOS 27 / Python 3.12 / Node 24 / Google Chrome. Браузерные тесты проверяют пользовательские сценарии и мобильную раскладку; они не являются аудитом доступности или нагрузочной оценкой.

- `.venv/bin/pytest -q`: **39 passed**, одно предупреждение Starlette о будущем переходе TestClient с `httpx` на `httpx2`.
- `.venv/bin/python -m py_compile apps/api/evidencerag/retrieval.py apps/api/evidencerag/store.py apps/api/evidencerag/main.py packages/research/runner.py`: успешно.
- `npm run check`: 0 ошибок, 0 предупреждений. `npm run build`: успешно; JS 76.20 KB (27.52 KB gzip), CSS 20.26 KB (4.84 KB gzip).
- Playwright против `https://osnovanie.duckdns.org`: **8/8 всего**, по 4 сценария в desktop и mobile emulation; JSON-журнал — `experiments/e2e-release-005.json`. Проверены прямые URL, назад/вперёд, новая вкладка, upload/delete, источники, сравнение редакций и отсутствие overflow на 320/390/768/1280 px.
- Серверный smoke на release-005: **17/17**, журнал — `experiments/vps-smoke-release-005.json`. Проверены frontend/assets, TLS cookie, демо, change signal, формальное правило, цитата/оригинал, diff, upload/search/delete, PDF/DOCX, формат/CSRF, изоляция и cleanup. Медиана 5 последовательных запросов на малом наборе — 5.61 ms; это не оценка ёмкости VPS.
- Внешний `/api/health`: HTTP 200; `algorithm=lexical-controller-v2`, `llm_public=false`, `semantic_sufficiency_judge=false`.
- Визуально осмотрены публичная главная и локальная страница метода с текущей сборкой. Палитра архива, типографика, сетка и существующая навигация сохранены.
- Снимок `experiments/infra-after-release-005.json`: контролируемые VPN/Xray unit-состояния и InvocationID, интерфейсы, route/rule/firewall и Docker-network hashes совпали с `experiments/infra-after-publication.json`. Из этого не следует end-to-end проверка всех VPN-клиентов. Существующий Caddy оставлен активным, его конфигурацию и контейнер не меняли.
- Offline pilot run-004: 21 synthetic test-query × 8 конфигураций; подробные метрики и ограничения в `experiments/run-004/REPORT.md`. Answer quality, semantic sufficiency, false abstention, unsupported answer, faithfulness и API cost — null. Сравнение не подтверждает научное преимущество.

Во время первого post-deploy smoke остались два устаревших утверждения, что редакционные изменения должны находиться в `conflicts`. Проверка зафиксировала корректное новое поведение (`version_differences` отдельно); сценарий `scripts/vps_smoke.py` обновлён, итоговый повтор прошёл 17/17. Same-edition disagreement остаётся отдельным проверяемым сценарием в unit/integration tests.

Локальный Playwright E2E (8/8) выполнен до публикации; текущий release дополнительно проверен 8/8 на публичном HTTPS. Mobile — emulation Chromium, не Safari/iOS. Нет независимого semantic judge, faithfulness, OCR, массовой нагрузки или оценки пропускной способности VPS.

## Cookie notice (31.10.2026)

Локально добавлены информационная плашка и прямая страница `/cookies`. Поведение плашки: закрытие хранится только в состоянии страницы и сбрасывается после перезагрузки; новых cookie или browser storage для этого не создаётся. Отдельный выпуск и публичная проверка этого изменения ещё не выполнены.
