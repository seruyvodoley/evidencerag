#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export PYTHONPATH=apps/api
exec .venv/bin/uvicorn evidencerag.main:app --host 127.0.0.1 --port "${PORT:-8000}" --workers 1 --no-access-log --limit-concurrency 16
