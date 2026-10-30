# Отключение EvidenceRAG на VPS — этап 007

Статус: **не выполнялось и сейчас небезопасно**.

Локальный browser mode и выбранные тесты теперь существуют, но публичный сайт ещё не переведён на них. Статический host не настроен, опубликованного заменяющего URL нет, полный release/security/parity acceptance не выполнен. Публичный [`osnovanie.duckdns.org`](https://osnovanie.duckdns.org) остаётся серверным приложением и зависит от FastAPI.

Поэтому не выполнялись SSH-соединение, остановка/отключение `evidencerag.service`, правки Caddy или DNS, firewall, Docker, маршрутов, сетевых параметров, TunnelDeck или VPN. VPS, база и резервные копии не менялись. Никаких новых live-состояний VPS в этом этапе не снимали; исторические сведения см. в `VPS_AUDIT.md`.

## Условия для будущего обратимого отключения

1. Публичная статическая версия опубликована на бесплатном host, новый URL доступен по HTTPS.
2. По production URL проверены asset/WASM MIME, worker, CSP и response headers, прямые маршруты/fallback, OPFS persistence, весь smoke и browser network audit.
3. Закрыты browser coverage gates для парсинга, русского поиска, версий, EvidenceRAG controller, export/import/delete, quota/errors и целевых браузеров с явным списком непроверенных платформ.
4. Сохранены внешняя копия release и возможность мгновенного возврата DNS/маршрута; документы/DB/backup не удаляются.
5. На live VPS проверены точные systemd/Caddy зависимости и baseline TunnelDeck; затем обратимо остановлена только собственная EvidenceRAG service. Запустить read-only/live health и VPN smoke после изменения.

Дальше сообщить владельцу URL, результаты rollback smoke и статус TunnelDeck. Данные/backup сохранить; разрушительное удаление не входит в разрешённый scope.
