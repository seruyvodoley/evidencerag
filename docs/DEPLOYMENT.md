# Развёртывание и откат

Фактический публичный URL: https://osnovanie.duckdns.org . HTTPS с проверкой сертификата и браузерными сценариями проверен 31.10.2026. Бесплатное имя предоставлено Duck DNS и зарегистрировано в аккаунте владельца; это зависимость от стороннего DNS, а не собственный домен второго уровня. Старый sslip.io-адрес оставлен рабочим. Позже можно подключить свой домен.

## Реальная архитектура VPS

Код: `/opt/evidencerag/releases/20261031-004`, symlink `/opt/evidencerag/current`. Системный пользователь/группа `evidencerag`, unit `/etc/systemd/system/evidencerag.service`, БД в `/var/lib/evidencerag/evidence.sqlite3`. Backend только `127.0.0.1:8077`, один worker, лимит CPU 60%, MemoryMax 640M. HTTPS обслуживает существующий Docker Caddy `ma-alice-https` с host networking. Новых контейнеров/сетей не создавали.

Изменён только новый собственный systemd-unit и согласованное дополнение `/root/ma-voice-https/Caddyfile`. Приложение запускается после reboot через enabled unit; фактическую перезагрузку VPS не делали. Root/systemd и Docker Caddy владелец инфраструктуры сохраняет под своим управлением. Ключи в проект не копировались.

В Ubuntu отсутствовал ensurepip. Системный Python/apt не менялись: бинарник uv 0.13.6 получен из PyPI wheel с проверкой SHA-256 и размещён только в release/.tools. В каждом релизе собственная `.venv`. У исходных файлов на внешнем Mac-диске были закрытые права; installer явно устанавливает чтение кода сервисным пользователем и запрещает запись группе/прочим.

## Повторяемое обновление

1. Локально `uv sync`, pytest, web check/build/E2E. Не переносить `var`, `.env`, `.git`, ключи, node_modules, тестовые документы пользователей и AppleDouble `._*`.
2. Упаковать apps/api, apps/web/dist, datasets/demo, deploy в новый release; зафиксировать SHA-256 архива/файлов как в deploy/release-manifest.json. Передача по существующему SSH с StrictHostKeyChecking=yes.
3. На сервере создать новый уникальный каталог `/opt/evidencerag/releases/<release>`. Существующие релизы не перезаписывать. Скопировать доверенный project-local uv либо использовать доступный Python venv. Выполнить `sh <release>/deploy/install-localhost.sh <release>`.
4. Installer проверяет порт при первом запуске, создаёт отдельного пользователя, окружение, FTS5, права, переключает symlink, включает только evidencerag и проверяет localhost health. При неудаче возвращает предыдущий собственный release. Не трогает VPN, SSH, DNS и firewall.
5. Выполнить scripts/vps_smoke.py на сервере; проверить сайт с внешнего клиента и сравнить scripts/infra_snapshot.py до/после.

## Общий proxy

Согласованное дополнение — deploy/Caddyfile.proposed-addition. `bind` совпадает с существующим публичным listener; без этого текущая конфигурация Caddy создаёт отдельный wildcard listener и возвращает пустой ответ на конкретном адресе. Этот случай фактически найден и исправлен внешним тестом. Существующие route-блоки сохранены байт-в-байт как префикс нового файла.

Проверка перед применением: hash действующего файла должен совпадать с просмотренным состоянием. Backup: `/opt/evidencerag/proxy-proposal/Caddyfile.before-publication` (root-only). Candidate: `Caddyfile.candidate` там же; `docker exec -i ma-alice-https caddy validate --config /dev/stdin --adapter caddyfile` до применения. Затем graceful `caddy reload`, без restart контейнера.

Caddyfile bind-mounted отдельным файлом, поэтому при записи сохранялся inode. Нельзя просто atomic-rename host-файл и ожидать, что контейнер увидит новый inode. Запись выполнялась полностью до reload; при отказе предусматривалось восстановление оригинала.

## Откат

Фактически проверен откат приложения с 003 на 002 и возврат 003: оба health check успешны. Переключать symlink атомарно через временную ссылку, затем `systemctl restart evidencerag.service`; чужие службы не перезапускать. Схема БД между этими релизами одинакова; destructive migrations не было. Для будущей смены схемы нужна отдельная миграционная стратегия.

Откат proxy: сначала убедиться, что после нас никто не изменил Caddyfile; сравнить с сохранённым candidate. Проверить исходный backup через caddy validate. Сохранить текущий файл, записать backup в действующий файл с сохранением inode и выполнить graceful reload. Это уберёт публичный маршрут EvidenceRAG, сохранив исходные службы. Фактического переключения proxy обратно ради теста не делали; проверен синтаксис исходного/нового файла, а реальный rollback-test выполнен на приложении.

Удаление приложения не должно удалять Docker-сети/контейнеры или выполнять prune. Сначала выключить только evidencerag и удалить только согласованный собственный маршрут. Базу не включать в общие долгоживущие backup без политики приватности.

Dockerfile/Compose оставлены как альтернативные конфигурации, но не запускались и не проверялись Docker build: на локальном Mac CLI Docker отсутствует; на VPS выбран systemd, чтобы не менять Docker networking.

Новый hostname добавлен к собственному site-блоку EvidenceRAG; backup — /opt/evidencerag/proxy-proposal/Caddyfile.before-duckdns. Выполнены validate и graceful reload. Duck DNS token на VPS не копировался.
