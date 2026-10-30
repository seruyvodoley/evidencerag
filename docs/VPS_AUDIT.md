# Фактический аудит VPS, 31.10.2026

Доступ подтверждён существующим SSH-ключом TunnelDeck со строгой проверкой known_hosts. В отчёте нет приватных ключей, пользовательских IP/peer-ключей, cookie или содержимого закрытых маршрутов. Сырой вывод конфигурации не хранится в репозитории.

Измерено перед установкой: Ubuntu 24.04.5 LTS, x86_64, 1 CPU; RAM 1963 MiB, available около 1225 MiB, swap 511 MiB (использовано 288 MiB). Корень 25 GiB, свободно около 13 GiB, 45% занято. Это снимок состояния, не гарантия постоянного резерва.

Docker 29.1.3; действовали ma-alice-https и music-assistant. Caddy в первом контейнере использует host networking и read-only mount Caddyfile. TCP 80/443 уже заняты веб-прокси. UDP 443 также был занят; транспорт не изменяли. Нельзя запускать второй публичный proxy поверх этих портов. Порт 8077 перед установкой свободен; теперь слушает только localhost.

Присутствуют wg0, homeexit, awgtd0, awgfriend0; Xray и связанные xhttp-службы активны. Отсутствие активности конкретного шаблонного awg-unit не трактуется как остановка интерфейса: фактически интерфейсы присутствуют и утилиты показывают недавние handshakes. Привилегированные VPN-конфигурации и peer private keys не читались.

Развёрнут отдельный evidencerag.service и отдельные каталоги /opt/evidencerag, /var/lib/evidencerag. Разрешённый владельцем маршрут добавлен в действующий Caddyfile; сделан graceful reload, контейнер не перезапускали. Автозапуск новой службы enabled. Не менялись SSH, DNS, сеть, sysctl, UFW/iptables/nftables, VPN-клиенты и порты.

Проверка сохранения инфраструктуры: experiments/infra-before-publication.json, infra-after-publication.json и infra-comparison.json. Сравниваются InvocationID/ActiveState основных VPN/Xray units, список VPN-интерфейсов, SHA-256 маршрутов, policy rules, stateless nft ruleset и Docker networks. Все сравнения совпали. Есть свежие handshakes WG и AWG; персональные peer-данные в отчёты не включены.

Это подтверждает отсутствие обнаруженных изменений и рестартов контролируемых служб. Не выполнены клиентский end-to-end тест каждого VPN-профиля, тест скорости/маршрута каждого домашнего устройства и реальная перезагрузка VPS. Полную работоспособность всех VPN-клиентов по одному серверному снимку утверждать нельзя.

Ресурсы приложения: порядка 54–62 MiB cgroup memory в idle/после smoke-поиска на малом наборе. Лимит службы 640 MiB/60% CPU. Тяжёлые научные эксперименты и нагрузочные тесты на VPS не запускались.

## Обновление release-005

31.10.2026 опубликован `/opt/evidencerag/releases/20261031-005`. До установки unit был active, Caddy-контейнер running, на корневом разделе оставалось около 13 GiB. Архив и манифест сверены до запуска installer. Health после установки: `lexical-controller-v2`, внешняя модель и semantic judge выключены. Серверный smoke прошёл 17/17; cgroup memory в момент снимка около 64 MiB. HTTPS E2E — 8/8 всего, по 4 сценария для desktop и mobile Chromium.

В этом выпуске Caddyfile, контейнер Caddy, firewall, SSH, Docker networks, VPN/Xray units и route/rule не менялись. Снимок после публикации совпал по указанным fingerprints и InvocationID с последним сохранённым снимком `experiments/infra-after-publication.json`; актуальный снимок — `experiments/infra-after-release-005.json`. Это проверка после установки и сопоставление с ранее записанным состоянием, не отдельный синхронный «до/после» снимок непосредственно вокруг команды установки. Приложение использует тот же порт, systemd-unit и схему БД; установщик перезапускал только `evidencerag.service`.

## Обновление release-006: уведомление о cookie

31.10.2026 опубликован `/opt/evidencerag/releases/20261031-006`, собранный из commit `4b9ea8e637c8f37b96c8539285df8a560f1d5f40`. SHA-256 архива — `bf8adeae213aeaf4a4d93a5f2f81aedc408f904fcbded98d1644181c46f96a37`; список файлов и хеши — `deploy/release-manifest.json`. Установщик успешно перезапустил только `evidencerag.service`; health подтвердил `lexical-controller-v2`.

Внешние HTTPS GET к `/`, `/cookies` и `/api/health` вернули 200. TLS проверялся обычным клиентом без отключения проверки сертификата. На GET главной и cookie-страницы `Set-Cookie` отсутствовал. Пользовательские upload/search-запросы не отправлялись; полный E2E этого небольшого релиза не запускался. Caddyfile, контейнер Caddy, firewall, SSH, Docker networks, VPN/Xray units и маршруты не менялись.
