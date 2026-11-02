from contextlib import contextmanager
import hashlib
import json
import re
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
CREATE TABLE IF NOT EXISTS revision_links(
 workspace TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
 amendment_document TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 target_document TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 relation TEXT NOT NULL, proof TEXT NOT NULL,
 PRIMARY KEY(workspace, amendment_document, target_document));
CREATE INDEX IF NOT EXISTS revision_link_target ON revision_links(workspace,target_document);
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

    def family_document_ids(self, ws, family):
        if not family:
            return []
        with self.connect() as db:
            return [row[0] for row in db.execute(
                'SELECT id FROM documents WHERE workspace=? AND family=?', (ws, family))]

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
        self.rebuild_revision_links(ws)
        return ident

    def rebuild_revision_links(self, ws):
        """Index only explicit revision relationships within one workspace.

        Equal metadata families link full editions. Cross-family amendments require
        an exact target-title reference plus an operative amendment clause. A narrow
        legacy rule also supports Stage 009 fixtures when an exact edition date and
        replaced old value identify exactly one target edition.
        """
        from .retrieval import terms
        marker = re.compile(r'поправ|измен|изложить|дополнить|утратил\s+силу|вместо|заменить', re.I)
        legacy = re.compile(r'в\s+редакции\s+от\s+(\d{1,2})\s+([а-яё]+)\s+(\d{4}).{0,240}?вместо\s+([^.,;]{1,60}).{0,100}?(?:устанавлива|заменя|изменя)', re.I | re.S)
        month = {'января':1,'февраля':2,'марта':3,'апреля':4,'мая':5,'июня':6,'июля':7,'августа':8,'сентября':9,'октября':10,'ноября':11,'декабря':12}
        with self.connect() as db:
            documents = [dict(row) for row in db.execute(
                'SELECT id,title,family,version,date FROM documents WHERE workspace=?', (ws,))]
            texts = {doc['id']: '\n'.join(row[0] for row in db.execute(
                'SELECT text FROM chunks WHERE document=? ORDER BY id', (doc['id'],))) for doc in documents}
            db.execute('DELETE FROM revision_links WHERE workspace=?', (ws,))
            links = []
            for amendment in documents:
                for target in documents:
                    if amendment['id'] == target['id']:
                        continue
                    if amendment['family'] and amendment['family'] == target['family']:
                        links.append((ws, amendment['id'], target['id'], 'same_family', amendment['family']))
                        continue
                    text = texts[amendment['id']]
                    folded = text.casefold()
                    title = target['title'].strip()
                    if len(title) >= 8 and title.casefold() in folded and marker.search(text):
                        links.append((ws, amendment['id'], target['id'], 'explicit_title', title))
                        continue
                    match = legacy.search(text)
                    if not match:
                        continue
                    day, month_name, year, old_value = match.groups()
                    if month_name.casefold() not in month:
                        continue
                    try:
                        from datetime import date as _date
                        edition_date = _date(int(year), month[month_name.casefold()], int(day)).isoformat()
                    except ValueError:
                        continue
                    exact_date_targets = [item for item in documents if item['id'] != amendment['id']
                                          and item['date'] == edition_date
                                          and (item['family'] == target['family'] or set(terms(item['title'])) & set(terms(target['title'])))]
                    # A date alone never creates a relationship: the explicit old-value
                    # clause must also occur in the unique target edition.
                    old = ' '.join(old_value.casefold().split())
                    if len(exact_date_targets) == 1 and old and old in texts[exact_date_targets[0]['id']].casefold():
                        links.append((ws, amendment['id'], exact_date_targets[0]['id'],
                                      'legacy_unique_edition_and_value', f'{edition_date}; {old}'))
            for link in links:
                db.execute('INSERT OR IGNORE INTO revision_links VALUES(?,?,?,?,?)', link)
            return len(links)

    def revision_snapshot(self, ws, seed_document_ids, max_chunks=50, deadline=None):
        """Return workspace-scoped linked editions without as-of/top-k prefiltering."""
        seeds = set(seed_document_ids)
        if not seeds:
            return {'hits': [], 'complete': True, 'document_count': 0, 'link_count': 0}
        with self.connect() as db:
            db.execute('PRAGMA busy_timeout=50')
            if deadline is not None:
                db.set_progress_handler(lambda: int(time.perf_counter() >= deadline), 1000)
            placeholders = ','.join('?' for _ in seeds)
            rows = db.execute(f'''SELECT DISTINCT d.id,d.title,d.family,d.version,d.date,d.digest,
              c.id AS chunk_id,c.text,c.locator,c.page,c.offset,
              COALESCE(a.relation,b.relation,'seed') AS revision_relation,
              COALESCE(a.proof,b.proof,'') AS revision_proof
              FROM documents seed
              JOIN documents d ON d.workspace=seed.workspace
              LEFT JOIN revision_links a ON a.workspace=d.workspace AND a.amendment_document=d.id AND a.target_document=seed.id
              LEFT JOIN revision_links b ON b.workspace=d.workspace AND b.amendment_document=seed.id AND b.target_document=d.id
              JOIN chunks c ON c.document=d.id
              WHERE seed.workspace=? AND seed.id IN ({placeholders})
                AND (d.id=seed.id OR d.family=seed.family OR a.target_document IS NOT NULL OR b.target_document IS NOT NULL)
              ORDER BY d.date,d.id,c.id''', [ws, *sorted(seeds)]).fetchall()
            total = len(rows)
            selected = rows[:max_chunks]
            hits = []
            for row in selected:
                item = dict(row)
                item['document'] = item.pop('id')
                item['id'] = item.pop('chunk_id')
                hits.append(item)
            doc_count = len({row['id'] for row in rows})
            linked_count = sum(1 for row in rows if row['revision_relation'] != 'seed')
            return {'hits': hits, 'complete': total <= max_chunks,
                    'document_count': doc_count, 'link_count': linked_count,
                    'chunk_count': total}

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
        args.append(limit)
        with self.connect() as db:
            db.execute('PRAGMA busy_timeout=50')
            if deadline is not None:
                db.set_progress_handler(lambda: int(time.perf_counter() >= deadline), 1000)
            return [dict(r) for r in db.execute(f'''SELECT c.id,c.document,c.text,c.locator,c.page,c.offset,
            d.title,d.family,d.version,d.date,d.digest,d.metadata,bm25(search) AS score
            FROM search JOIN chunks c ON c.id=search.rowid JOIN documents d ON d.id=c.document
            WHERE search MATCH ? AND {' AND '.join(filters)} ORDER BY score,c.id LIMIT ?''', args)]
