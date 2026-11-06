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
        return self.add_many(ws, [(filename, raw, parsed, title, family, version, date, metadata)])[0]

    def add_many(self, ws, items):
        from .retrieval import normalized
        items = list(items)
        if not items:
            return []
        idents = [secrets.token_hex(12) for _ in items]
        with self.connect() as db:
            # Quotas are checked inside the write transaction, including demo imports.
            db.execute('BEGIN IMMEDIATE')
            count, size = db.execute('SELECT count(*),coalesce(sum(length(original)),0) FROM documents WHERE workspace=?', (ws,)).fetchone()
            total = db.execute('SELECT coalesce(sum(length(original)),0) FROM documents').fetchone()[0]
            added_size = sum(len(item[1]) for item in items)
            if count + len(items) > 20 or size + added_size > 40_000_000 or total + added_size > 400_000_000:
                raise ValueError('Лимит хранилища: 20 документов / 40 МБ на пространство')
            for ident, (filename, raw, parsed, title, family, version, date, metadata) in zip(idents, items):
                db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                           (ident, ws, title, filename, family, version, date, parsed['status'], hashlib.sha256(raw).hexdigest(), raw, json.dumps(metadata or {}, ensure_ascii=False)))
                for p in parsed['parts']:
                    db.execute('INSERT INTO chunks(document,text,locator,page,offset,indexed) VALUES(?,?,?,?,?,?)',
                               (ident, p['text'], p['locator'], p['page'], p.get('offset', 0), normalized(p['text'])))
        self.rebuild_revision_links(ws)
        return idents

    def update_metadata(self, ws, ident, title, family, version, date, metadata):
        with self.connect() as db:
            changed = db.execute('''UPDATE documents SET title=?,family=?,version=?,date=?,metadata=?
                WHERE workspace=? AND id=?''', (title, family, version, date,
                json.dumps(metadata or {}, ensure_ascii=False), ws, ident)).rowcount
        if changed:
            self.rebuild_revision_links(ws)
        return changed

    def rebuild_revision_links(self, ws):
        """Rebuild only explicit links; equal scores remain visibly ambiguous."""
        from .retrieval import terms
        marker = re.compile(r'поправ|измен|перенес|изложить|дополнить|утратил\s+силу|вместо|заменить|считать\s+равн', re.I)
        clause_re = re.compile(r'(?:пункт(?:а|е|ом)?|п\.)\s*(\d+(?:\.\d+)*)', re.I)
        target_date_re = re.compile(r'(?:редакци\w*|издани\w*)\s+от\s+(\d{1,2}\s+[а-яё]+\s+\d{4}|\d{4}-\d{2}-\d{2})', re.I)
        target_year_re = re.compile(r'(?:регламент\w*|положени\w*|редакци\w*)\s+(?:от\s+)?(20\d{2})(?:\s+года)?', re.I)
        months = {'января':1,'февраля':2,'марта':3,'апреля':4,'мая':5,'июня':6,'июля':7,'августа':8,'сентября':9,'октября':10,'ноября':11,'декабря':12}

        def dates(text):
            found = set(re.findall(r'\b\d{4}-\d{2}-\d{2}\b', text))
            for day, name, year in re.findall(r'\b(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})', text.casefold()):
                try:
                    from datetime import date as _date
                    found.add(_date(int(year), months[name], int(day)).isoformat())
                except ValueError:
                    pass
            return found

        def old_values(text):
            values = []
            for match in re.finditer(r'\bвместо\s+(.{1,80}?)(?=\s+(?:необходимо|нужно|следует|предоставлять|представлять|комплект|материалы|принимается|устанавливается|должен|должно)\b|[,;.]|$)', text, re.I | re.S):
                value = ' '.join(match.group(1).casefold().split()).strip(' «»"\'')
                if value:
                    values.append(value)
            return values

        def normalize(text):
            normalized_dates = dates(text)
            return normalized_dates or {' '.join(re.findall(r'[a-zа-яё0-9]+', text.casefold()))}

        with self.connect() as db:
            documents = [dict(row) for row in db.execute(
                'SELECT id,title,family,version,date,metadata FROM documents WHERE workspace=? ORDER BY date,id', (ws,))]
            texts = {doc['id']: '\n'.join(row[0] for row in db.execute(
                'SELECT text FROM chunks WHERE document=? ORDER BY id', (doc['id'],))) for doc in documents}
            db.execute('DELETE FROM revision_links WHERE workspace=?', (ws,))
            links = []
            for amendment in documents:
                text = texts[amendment['id']]
                folded = text.casefold()
                amendment_meta = json.loads(amendment.get('metadata') or '{}')
                explicit_id = amendment_meta.get('amends_document_id')
                if not marker.search(folded) and not explicit_id:
                    continue
                if explicit_id and any(item['id'] == explicit_id for item in documents if item['id'] != amendment['id']):
                    links.append((ws, amendment['id'], explicit_id, 'explicit_metadata_target', 'amends_document_id'))
                    continue
                target_dates = dates(target_date_re.search(text).group(1)) if target_date_re.search(text) else set()
                target_year_match = target_year_re.search(text)
                target_year = target_year_match.group(1) if target_year_match else None
                clauses = set(clause_re.findall(text))
                old_refs = [value for value in old_values(text)]
                candidates = []
                quoted_targets = [a or b for a, b in re.findall(r'«([^»]+)»|"([^"]+)"', text)]
                for target in documents:
                    if amendment['id'] == target['id']:
                        continue
                    if amendment['family'] and amendment['family'] == target['family']:
                        candidates.append((target, 1, 'same_family', amendment['family']))
                        continue
                    title = target['title'].strip()
                    exact_target_title = bool(len(title) >= 8 and title.casefold() in folded)
                    if quoted_targets and not any(value.casefold() in title.casefold() for value in quoted_targets):
                        continue
                    if exact_target_title:
                        candidates.append((target, 4, 'explicit_title', title))
                        continue
                    if marker.search((title + ' ' + texts[target['id']]).casefold()):
                        # A generic year/clause reference points at a full edition,
                        # not at another amendment. An amendment can be targeted
                        # only by an explicit title or trusted metadata relation.
                        continue
                    has_explicit_date = bool(target_dates and target['date'] in target_dates)
                    target_matches_year = bool(target_year and (str(target.get('version') or '') == target_year or str(target.get('date') or '').startswith(target_year)))
                    title_kind_matches = bool(re.search(r'регламент|положени|правил', target['title'], re.I)
                                              and re.search(r'регламент|положени|правил', text, re.I))
                    source_text = texts[target['id']].casefold()
                    source_dates = dates(source_text)
                    def old_appears(source):
                        source_folded = source.casefold()
                        source_dates = dates(source_folded)
                        return any(bool(normalize(old) & source_dates) or
                                   any(token and token in source_folded for token in normalize(old))
                                   for old in old_refs)
                    old_match = old_appears(source_text)
                    chain_match = any(
                        target['id'] == linked_target and linked_amendment != amendment['id'] and
                        old_appears(texts.get(linked_amendment, ''))
                        for _, linked_amendment, linked_target, _, _ in links)
                    old_match = old_match or chain_match
                    has_clause = bool(clauses)
                    if has_explicit_date and has_clause and old_match:
                        candidates.append((target, 5, 'explicit_edition_and_clause_and_old_value',
                                           f'{", ".join(sorted(target_dates))}; clauses={",".join(sorted(clauses))}; old={";".join(old_refs)}'))
                    elif target_matches_year and title_kind_matches and has_clause and old_match:
                        relation = 'explicit_amendment_chain' if chain_match and not old_appears(source_text) else 'explicit_edition_and_clause_and_old_value'
                        candidates.append((target, 3, relation,
                                           f'{target_year}; clauses={",".join(sorted(clauses))}; old={";".join(old_refs)}'))
                if not candidates:
                    # Keep the narrow date + replaced-value compatibility path.
                    for target in documents:
                        if amendment['id'] == target['id']:
                            continue
                        if target_dates and target['date'] in target_dates and old_refs and any(
                            bool(normalize(old) & dates(texts[target['id']].casefold())) or
                            any(token and token in texts[target['id']].casefold() for token in normalize(old))
                            for old in old_refs):
                            candidates.append((target, 5, 'legacy_unique_edition_and_value',
                                               f'{target["date"]}; {";".join(old_refs)}'))
                if candidates:
                    highest = max(score for _, score, _, _ in candidates)
                    best = [(target, relation, proof) for target, score, relation, proof in candidates if score == highest]
                    relation = best[0][1] if len(best) == 1 else 'ambiguous_target'
                    proof = best[0][2] if len(best) == 1 else '; '.join(sorted({item[2] for item in best}))
                    links.extend((ws, amendment['id'], target['id'], relation, proof) for target, _, _ in best)
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
