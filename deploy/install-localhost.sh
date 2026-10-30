#!/bin/sh
# Run on the audited VPS after uploading a release; only this project's service is changed.
set -eu
RELEASE=${1:?absolute release directory required}
case "$RELEASE" in /opt/evidencerag/releases/[a-zA-Z0-9-]*) ;; *) exit 2;; esac
[ -f "$RELEASE/deploy/evidencerag.service" ]
if [ ! -L /opt/evidencerag/current ]; then
    if ss -Hlnt | awk '{print $4}' | grep -q ':8077$'; then
        echo 'Port 8077 is occupied; refusing to continue' >&2
        exit 1
    fi
fi
if ! id evidencerag >/dev/null 2>&1; then
    useradd --system --home /nonexistent --shell /usr/sbin/nologin evidencerag
fi
if [ -x "$RELEASE/.tools/uv" ]; then
    "$RELEASE/.tools/uv" venv --clear --python /usr/bin/python3 "$RELEASE/.venv"
    "$RELEASE/.tools/uv" pip install --python "$RELEASE/.venv/bin/python" --no-cache -q -r "$RELEASE/deploy/requirements.txt"
else
    python3 -m venv "$RELEASE/.venv"
    "$RELEASE/.venv/bin/pip" install --disable-pip-version-check --no-cache-dir -q -r "$RELEASE/deploy/requirements.txt"
fi
# Validate FTS5 secure-delete support before replacing the current release.
PYTHONPATH="$RELEASE/apps/api" "$RELEASE/.venv/bin/python" -c 'import tempfile; from evidencerag.store import EvidenceStore; d=tempfile.TemporaryDirectory(); EvidenceStore(d.name+"/check.db")'
chown -R root:root "$RELEASE"
chmod -R a+rX,go-w "$RELEASE"
PREVIOUS=$(readlink /opt/evidencerag/current || true)
if [ -f /etc/systemd/system/evidencerag.service ]; then
    grep -q 'Description=EvidenceRAG document evidence workbench' /etc/systemd/system/evidencerag.service
    cp /etc/systemd/system/evidencerag.service "$RELEASE/previous-evidencerag.service"
fi
install -m 0644 "$RELEASE/deploy/evidencerag.service" /etc/systemd/system/evidencerag.service
ln -s "$RELEASE" /opt/evidencerag/current.new
mv -Tf /opt/evidencerag/current.new /opt/evidencerag/current
systemctl daemon-reload
systemctl enable evidencerag.service
systemctl restart evidencerag.service
for attempt in 1 2 3 4 5 6 7 8 9 10; do
    if curl -fsS --max-time 2 http://127.0.0.1:8077/api/health; then
        echo
        printf 'Isolated release running: %s\n' "$RELEASE"
        exit 0
    fi
    sleep 1
done
if [ -n "$PREVIOUS" ]; then
    ln -s "$PREVIOUS" /opt/evidencerag/current.rollback
    mv -Tf /opt/evidencerag/current.rollback /opt/evidencerag/current
    systemctl restart evidencerag.service
else
    systemctl stop evidencerag.service
fi
echo 'Health check failed; own-service rollback applied' >&2
exit 1
