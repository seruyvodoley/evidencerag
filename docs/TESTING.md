# Проверки и результаты

31.10.2026, Python 3.12 / Node 20.20.2 / установленный Google Chrome.

- `pytest -q`: 32 теста успешно. Покрыты PDF-страницы, scan-status, DOCX-заголовки/таблицы, Markdown origin, плохие/бинарные файлы, ZIP-bomb, парсер timeout, реальные upload/search, версия/дата, формальное правило, недостаток сведений, scope isolation на read/download/delete/compare/search, каскадное удаление FTS, истечение TTL, CSRF, body/query/document/rate limits, inert prompt injection, поддельные цитаты, отключённая LLM и воспроизводимость offline-метрик. Лог experiments/pytest-final.txt.
- Svelte/TypeScript `npm run check`: 0 errors, 0 warnings. `npm run build`: успешно, раздаётся production bundle.
- Локальные Playwright E2E: 8/8 успешно. Затем те же сценарии против https://osnovanie.91-196-32-58.sslip.io: 8/8 успешно. Настольный Chrome и mobile emulation iPhone 13 на Chromium; это не тест реального Safari/iOS.
- E2E проверяют demo→поиск→различия→редакция→правило→источник→diff, реальный upload→поиск→delete→empty, отказ без данных. Проверка ширин 320/390/768/1280 не выявила overflow. Результаты последнего публичного запуска — experiments/e2e-results.json.
- CUA: визуальный просмотр desktop/mobile, переход к точному источнику, публичный поиск. Снимки docs/screenshots. Проверены label/focus/семантические controls и reduced-motion по frontend-design/web-design-guidelines; это ручной review, не сертификат WCAG и не отдельный axe-аудит.
- VPS smoke: 17/17 успешно; см. experiments/vps-smoke-final.json. Проверены реальные загрузки TXT/DOCX/scan PDF, источники, оригинал, diff, isolation/delete/CSRF, frontend/assets.
- Внешний HTTPS: сертификат проверен стандартным клиентом, / и /api/health HTTP 200, health JSON корректен. Нельзя считать пустой HTTP 200 успешной публикацией: такой дефект listener обнаружен и исправлен до итоговой проверки.
- Откат приложения 003→002→003: оба health check успешны. Общий Caddy не рестартовали; его reload и синтаксис проверены. Фактический reboot и Docker build не выполнялись.
- Offline: 63 synthetic cases в полном наборе, test 21 × 8 стратегий. Два запуска в автоматическом тесте сравнивают все summary-метрики кроме latency; одинаковые результаты. Финальный run-003 фиксирует source hashes. Численные сравнения не подтверждают научное преимущество.
- Локальный короткий load: 40/40 валидных HTTP-поисков при concurrency=4. Это не оценка вместимости VPS.
- pip-audit: известных находок нет; npm production audit 0, полный npm audit 3 low в dev dependencies. Есть предупреждение Starlette о будущем переходе TestClient с httpx на httpx2, текущие тесты проходят.

Не проверено: смысловая entailment/faithfulness, официальный S2G GPU baseline, OCR, encrypted-at-rest, массовая многопользовательская нагрузка, реальный мобильный Safari, клиентский трафик каждого VPN-профиля. Эти ограничения не закрываются количеством прошедших fixtures.

Навигационные E2E дополнительно проверяют самостоятельные URL /documents, /compare, /method, обновление прямого адреса, Назад/Вперёд и открытие страницы в другом табе. API-тесты проверяют отдачу HTML по трём адресам. Значки браузера проверены HTTP-запросами с корректными MIME и непустым содержимым.
