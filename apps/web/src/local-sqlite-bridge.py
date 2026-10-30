"""SQLite DB-API compatibility surface backed by SQLite WASM in this Worker."""
from __future__ import annotations

import base64
import json
import sys
import types

from js import browser_sqlite_exec, browser_sqlite_set_progress_handler
from pyodide.ffi import create_proxy


class OperationalError(Exception):
    pass


class IntegrityError(Exception):
    pass


class Row(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)

    def __iter__(self):
        return iter(self.values())


def _encode(value):
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"$blob": base64.b64encode(bytes(value)).decode("ascii")}
    raise TypeError(f"Unsupported SQLite parameter: {type(value).__name__}")


def _decode(value):
    if isinstance(value, dict) and set(value) == {"$blob"}:
        return base64.b64decode(value["$blob"])
    if isinstance(value, dict):
        return {key: _decode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_decode(item) for item in value]
    return value


def _call(sql: str, params=()) -> dict:
    payload = json.dumps(params, ensure_ascii=False, default=_encode, separators=(",", ":"))
    try:
        result = browser_sqlite_exec(sql, payload)
        response = json.loads(str(result))
    except Exception as error:
        raise OperationalError(str(error)) from error
    if "error" in response:
        raise OperationalError(response["error"])
    return response


class Cursor:
    def __init__(self, response: dict, row_factory):
        self._rows = response.get("rows", [])
        self._row_factory = row_factory
        self.rowcount = response.get("rowcount", -1)
        self.lastrowid = response.get("lastrowid")

    def _row(self, item):
        item = _decode(item)
        return self._row_factory(item) if self._row_factory else tuple(item.values())

    def fetchone(self):
        if not self._rows:
            return None
        return self._row(self._rows.pop(0))

    def fetchall(self):
        rows, self._rows = self._rows, []
        return [self._row(item) for item in rows]

    def __iter__(self):
        while row := self.fetchone():
            yield row


class Connection:
    """Each wrapper shares the single Worker-owned OPFS database handle."""

    def __init__(self, path, **_kwargs):
        self.path = str(path)
        self.row_factory = None
        self.in_transaction = False
        self.closed = False
        self._progress_handler = None
        self._progress_proxy = None

    def execute(self, sql, params=()):
        if self.closed:
            raise OperationalError("Connection is closed")
        command = sql.lstrip().split(None, 1)[0].upper() if sql.strip() else ""
        if command in {"INSERT", "UPDATE", "DELETE", "REPLACE"} and not self.in_transaction:
            _call("BEGIN")
            self.in_transaction = True
        response = _call(sql, params)
        if command == "BEGIN":
            self.in_transaction = True
        elif command in {"COMMIT", "END", "ROLLBACK"}:
            self.in_transaction = False
        return Cursor(response, self.row_factory)

    def executescript(self, sql):
        if self.in_transaction:
            self.commit()
        return Cursor(_call(sql), self.row_factory)

    def commit(self):
        if self.in_transaction:
            _call("COMMIT")
            self.in_transaction = False

    def rollback(self):
        if self.in_transaction:
            _call("ROLLBACK")
            self.in_transaction = False

    def set_progress_handler(self, callback, steps):
        if self._progress_proxy is not None:
            browser_sqlite_set_progress_handler(None, 0)
            self._progress_proxy.destroy()
            self._progress_proxy = None
        self._progress_handler = callback
        if callback is not None:
            self._progress_proxy = create_proxy(callback)
        browser_sqlite_set_progress_handler(self._progress_proxy, steps if callback else 0)

    def close(self):
        if self.in_transaction:
            self.rollback()
        if self._progress_handler is not None:
            self.set_progress_handler(None, 0)
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, _exc, _tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False


def connect(path, **kwargs):
    return Connection(path, **kwargs)


def install(sqlite_version: str):
    module = types.ModuleType("sqlite3")
    module.connect = connect
    module.Row = Row
    module.OperationalError = OperationalError
    module.IntegrityError = IntegrityError
    module.sqlite_version = sqlite_version
    sys.modules["sqlite3"] = module
