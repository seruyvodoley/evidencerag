from contextlib import contextmanager
import hashlib
import json
import secrets
import sqlite3
import time
from pathlib import Path

SCHEMA = '''
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS workspaces(id TEXT PRIMARY KEY, expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS documents(
 id TEXT PRIMARY KEY, workspace TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
 title TEXT NOT NULL, filename TEXT NOT NULL, family TEXT NOT NULL, version TEXT NOT NULL,
 date TEXT NOT NULL, status TEXT NOT NULL, digest TEXT NOT NULL, original BLOB NOT NULL,
 metadata TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS chunks(
 id INTEGER PRIMARY KEY, document TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 text TEXT NOT NULL, locator TEXT NOT NULL, page INTEGER, offset INTEGER NOT NULL, indexed TEXT NOT NULL);
CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(indexed, content=chunks, content_rowid=id);
CREATE TRIGGER IF NOT EXISTS chunk_insert AFTER INSERT ON chunks BEGIN
 INSERT INTO search(rowid,indexed) VALUES(new.id,new.indexed); END;
CREATE TRIGGER IF NOT EXISTS chunk_delete AFTER DELETE ON chunks BEGIN
 INSERT INTO search(search,rowid,indexed) VALUES('delete',old.id,old.indexed); END;
CREATE INDEX IF NOT EXISTS document_workspace ON documents(workspace);
CREATE INDEX IF NOT EXISTS chunk_document ON chunks(document);
'''


class EvidenceStore:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(SCHEMA)
            # FTS5 secure-delete requires SQLite 3.42+. It clears replaced index entries.
            db.execute("INSERT INTO search(search,rank) VALUES('secure-delete',1)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA busy_timeout=10000')
        db.execute('PRAGMA secure_delete=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def cleanup(self):
        with self.connect() as db:
            db.execute('DELETE FROM workspaces WHERE expires < ?', (time.time(),))
            db.commit()
            db.execute('PRAGMA wal_checkpoint(TRUNCATE)')

    def create_workspace(self):
        token = secrets.token_urlsafe(32)
        key = hashlib.sha256(token.encode()).hexdigest()
        with self.connect() as db:
            if db.execute('SELECT count(*) FROM workspaces').fetchone()[0] >= 1000:
                raise ValueError('Сервис заполнен. Попробуйте позже')
            db.execute('INSERT INTO workspaces VALUES(?,?)', (key, time.time() + 86400))
        return token

    def workspace(self, token):
        if not token or len(token) > 100:
            return None
        key = hashlib.sha256(token.encode()).hexdigest()
        with self.connect() as db:
            row = db.execute('SELECT id FROM workspaces WHERE id=? AND expires>?', (key, time.time())).fetchone()
        return row['id'] if row else None

    def documents(self, ws):
        with self.connect() as db:
            return [dict(r) for r in db.execute('''SELECT d.id,title,filename,family,version,date,status,digest,metadata,
            (SELECT count(*) FROM chunks WHERE document=d.id) AS chunk_count
            FROM documents d WHERE workspace=? ORDER BY family,date,version''', (ws,))]

    def add(self, ws, filename, raw, parsed, title, family, version, date, metadata=None):
        from .retrieval import normalized
        ident = secrets.token_hex(12)
        with self.connect() as db:
            # Quotas are checked inside the write transaction, including demo imports.
            db.execute('BEGIN IMMEDIATE')
            count, size = db.execute('SELECT count(*),coalesce(sum(length(original)),0) FROM documents WHERE workspace=?', (ws,)).fetchone()
            total = db.execute('SELECT coalesce(sum(length(original)),0) FROM documents').fetchone()[0]
            if count >= 20 or size + len(raw) > 40_000_000 or total + len(raw) > 400_000_000:
                raise ValueError('Лимит хранилища: 20 документов / 40 МБ на пространство')
            db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (ident, ws, title, filename, family, version, date, parsed['status'], hashlib.sha256(raw).hexdigest(), raw, json.dumps(metadata or {}, ensure_ascii=False)))
            for p in parsed['parts']:
                db.execute('INSERT INTO chunks(document,text,locator,page,offset,indexed) VALUES(?,?,?,?,?,?)',
                           (ident, p['text'], p['locator'], p['page'], p.get('offset', 0), normalized(p['text'])))
        return ident

    def document(self, ws, ident, original=False):
        with self.connect() as db:
            fields = '*' if original else 'id,title,filename,family,version,date,status,digest,metadata'
            row = db.execute(f'SELECT {fields} FROM documents WHERE id=? AND workspace=?', (ident, ws)).fetchone()
            if not row:
                return None
            result = dict(row)
            result['chunks'] = [dict(c) for c in db.execute('SELECT id,text,locator,page,offset FROM chunks WHERE document=? ORDER BY id', (ident,))]
            return result

    def delete(self, ws, ident):
        with self.connect() as db:
            return db.execute('DELETE FROM documents WHERE workspace=? AND id=?', (ws, ident)).rowcount

    def search(self, ws, terms, limit=10, family=None, version=None, as_of=None, deadline=None):
        if not terms:
            return []
        expression = ' OR '.join('"' + t.replace('"', '') + '"' for t in terms)
        filters, args = ['d.workspace=?'], [expression, ws]
        for field, value in [('family', family), ('version', version)]:
            if value:
                filters.append(f'd.{field}=?')
                args.append(value)
        if as_of:
            # Unknown dates cannot establish applicability.
            filters.append("d.date!='' AND d.date<=?")
            args.append(as_of)
            filters.append("d.date=(SELECT max(d2.date) FROM documents d2 WHERE d2.workspace=d.workspace AND d2.family=d.family AND d2.date<=?)")
            args.append(as_of)
        args.append(limit)
        with self.connect() as db:
            db.execute('PRAGMA busy_timeout=50')
            if deadline is not None:
                db.set_progress_handler(lambda: int(time.perf_counter() >= deadline), 1000)
            return [dict(r) for r in db.execute(f'''SELECT c.id,c.document,c.text,c.locator,c.page,c.offset,
            d.title,d.family,d.version,d.date,d.metadata,bm25(search) AS score
            FROM search JOIN chunks c ON c.id=search.rowid JOIN documents d ON d.id=c.document
            WHERE search MATCH ? AND {' AND '.join(filters)} ORDER BY score,c.id LIMIT ?''', args)]
