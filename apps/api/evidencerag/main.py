import asyncio
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import date as Date
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .parser import parse
from .retrieval import retrieve
from .store import EvidenceStore

ROOT = Path(__file__).resolve().parents[3]
DATA = Path(os.getenv('DATA_DIR', str(ROOT / 'var')))
DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
STORE = EvidenceStore(DATA / 'evidence.sqlite3')
CATALOG = json.loads((ROOT / 'datasets/demo/catalog.json').read_text())
SECURE = os.getenv('COOKIE_SECURE', 'false') == 'true'
PARSER_GATE = threading.BoundedSemaphore(1)


@asynccontextmanager
async def lifespan(app):
    STORE.cleanup()
    async def clean():
        while True:
            await asyncio.sleep(60)
            await asyncio.to_thread(STORE.cleanup)
    worker = asyncio.create_task(clean())
    yield
    worker.cancel()
    try:
        await worker
    except asyncio.CancelledError:
        pass


app = FastAPI(title='Основание / EvidenceRAG', version='0.1.0', lifespan=lifespan, docs_url=None, redoc_url=None)


class Guard:
    """Count bytes while streaming; apply origin checks before multipart parsing."""
    def __init__(self, app):
        self.app = app
        self.rates = defaultdict(deque)
        self.lock = threading.Lock()

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope.get('headers', []))
        async def reject(status, message):
            body = json.dumps({'detail':message}, ensure_ascii=False).encode()
            await send({'type':'http.response.start','status':status,'headers':[(b'content-type',b'application/json; charset=utf-8')]})
            await send({'type':'http.response.body','body':body})
        if scope['method'] not in {'GET','HEAD','OPTIONS'}:
            origin = headers.get(b'origin', b'').decode()
            host = headers.get(b'host', b'').decode()
            if headers.get(b'sec-fetch-site') == b'cross-site' or (origin and urlsplit(origin).netloc != host):
                return await reject(403, 'Запрос с другого сайта запрещён')
            ip = str(scope.get('client', ('unknown',))[0])
            # Store hashed addresses in memory for one minute, never in logs.
            key = hashlib.sha256(ip.encode()).hexdigest()
            now = time.monotonic()
            with self.lock:
                for old in list(self.rates):
                    while self.rates[old] and self.rates[old][0] < now - 60:
                        self.rates[old].popleft()
                    if not self.rates[old]:
                        del self.rates[old]
                bucket = self.rates[key]
                over = len(bucket) >= 90 or sum(map(len, self.rates.values())) >= 1000
                if not over:
                    bucket.append(now)
            if over:
                return await reject(429, 'Слишком много запросов. Подождите минуту')
        # Bounded complete body before calling downstream prevents parser allocation over limit.
        if scope['method'] in {'POST','PUT','PATCH'}:
            body = bytearray()
            while True:
                event = await receive()
                if event['type'] == 'http.disconnect':
                    return
                body.extend(event.get('body', b''))
                if len(body) > 10_100_000:
                    return await reject(413, 'Размер запроса превышает 10 МБ')
                if not event.get('more_body', False):
                    break
            delivered = False
            original_receive = receive
            async def bounded_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {'type':'http.request','body':bytes(body),'more_body':False}
                return await original_receive()
            receive = bounded_receive
        async def secure_send(message):
            if message['type'] == 'http.response.start':
                message.setdefault('headers', []).extend([
                    (b'x-content-type-options', b'nosniff'), (b'referrer-policy', b'no-referrer'),
                    (b'cache-control', b'no-store'),
                    (b'content-security-policy', b"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"),
                    (b'permissions-policy', b'camera=(), microphone=(), geolocation=()')])
            await send(message)
        try:
            await self.app(scope, receive, secure_send)
        except Exception:
            # No document-bearing exceptions or request bodies in application logs.
            await reject(500, "Ошибка обработки. Повторите запрос или используйте другой файл")


app.add_middleware(Guard)


def workspace(request):
    key = STORE.workspace(request.cookies.get('evidence_session'))
    if not key:
        raise HTTPException(401, 'Рабочее пространство истекло. Создайте новое')
    return key


def valid_date(value):
    if value:
        try:
            Date.fromisoformat(value)
        except ValueError:
            raise HTTPException(422, 'Дата должна иметь формат ГГГГ-ММ-ДД')
    return value


@app.get('/api/health')
def health():
    return {'status':'ok','mode':'lexical','llm_public':False,'algorithm':'lexical-controller-v1'}


@app.post('/api/workspaces')
def create_workspace(response: Response):
    try:
        token = STORE.create_workspace()
    except ValueError as e:
        raise HTTPException(503, str(e))
    response.set_cookie('evidence_session', token, httponly=True, secure=SECURE, samesite='strict', max_age=86400, path='/')
    return {'expires_in':86400,'mode':'lexical'}


@app.get('/api/session')
def session(request: Request):
    ws = workspace(request)
    with STORE.connect() as db:
        expires = db.execute('SELECT expires FROM workspaces WHERE id=?', (ws,)).fetchone()[0]
    return {'expires_at':expires,'mode':'lexical','documents':STORE.documents(ws)}


@app.delete('/api/workspace')
def delete_workspace(request: Request, response: Response):
    ws = workspace(request)
    with STORE.connect() as db:
        db.execute('DELETE FROM workspaces WHERE id=?', (ws,))
    response.delete_cookie('evidence_session', path='/')
    return {'deleted':True}


@app.get('/api/demos')
def demos():
    return [{'id': c['id'], 'name': c['name'], 'description': c['description'], 'questions':c['questions'], 'count':len(c['documents'])} for c in CATALOG]


def import_demo(store, ws, corpus_id):
    corpus = next((c for c in CATALOG if c['id'] == corpus_id), None)
    if not corpus:
        raise HTTPException(404, 'Демонстрационный набор не найден')
    existing = {(d['family'], d['version']) for d in store.documents(ws)}
    added = []
    for doc in corpus['documents']:
        if (doc['family'], doc['version']) in existing:
            continue
        raw = (ROOT/'datasets/demo'/doc['filename']).read_bytes()
        added.append(store.add(ws, doc['filename'], raw, parse(raw, '.md'), doc['title'], doc['family'], doc['version'], doc['date'], {'demo':True, 'formal_rules':doc.get('formal_rules',[])}))
    return added


@app.post('/api/demos/{corpus_id}/import')
def demo_import(corpus_id: str, request: Request):
    try:
        return {'added':import_demo(STORE, workspace(request), corpus_id)}
    except ValueError as e:
        raise HTTPException(413, str(e))


@app.get('/api/documents')
def documents(request: Request):
    return STORE.documents(workspace(request))


@app.post('/api/documents')
def upload(request: Request, file: UploadFile = File(...), title: str = Form('', max_length=160),
           family: str = Form('', max_length=100), version: str = Form('', max_length=40), date: str = Form('', max_length=10)):
    ws = workspace(request)
    filename = Path((file.filename or 'document').replace('\\','/')).name[:160]
    suffix = Path(filename).suffix.lower()
    if suffix not in {'.pdf','.docx','.txt','.md'}:
        raise HTTPException(415, 'Поддерживаются PDF, DOCX, TXT и Markdown')
    valid_date(date)
    raw = file.file.read(10_000_001)
    if not raw or len(raw) > 10_000_000:
        raise HTTPException(413, 'Нужен непустой файл не более 10 МБ')
    if not PARSER_GATE.acquire(blocking=False):
        raise HTTPException(429, 'Сейчас обрабатывается другой файл. Повторите через несколько секунд')
    try:
        with tempfile.TemporaryDirectory(prefix='evidence-') as tmp:
            path = Path(tmp)/'upload'
            path.write_bytes(raw)
            try:
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('parser.py')), str(path), suffix], capture_output=True, timeout=15, check=False)
                parsed = json.loads(result.stdout)
                if result.returncode or 'error' in parsed:
                    raise ValueError('Невозможно прочитать файл: проверьте формат, пароль и ограничения')
            except (subprocess.TimeoutExpired, json.JSONDecodeError):
                raise ValueError('Обработка прервана: файл слишком сложный или повреждён')
        # Conservative filename metadata only; all inferred values remain editable on upload.
        inferred = re.search(r'(?:v|версия[-_ ]?)(\d+(?:\.\d+)*)', filename, re.I)
        ident = STORE.add(ws, filename, raw, parsed, title.strip() or filename,
                          family.strip() or (title.strip() or Path(filename).stem),
                          version.strip() or (inferred.group(1) if inferred else ''), date)
        return STORE.document(ws, ident)
    except ValueError as e:
        raise HTTPException(422, str(e))
    finally:
        PARSER_GATE.release()


@app.get('/api/documents/{ident}')
def document(ident: str, request: Request):
    doc = STORE.document(workspace(request), ident)
    if not doc:
        raise HTTPException(404, 'Документ не найден')
    return doc


@app.get('/api/documents/{ident}/original')
def original(ident: str, request: Request):
    doc = STORE.document(workspace(request), ident, original=True)
    if not doc:
        raise HTTPException(404, 'Документ не найден')
    # All untrusted originals are downloads; no active HTML or embedded PDF scripts.
    return Response(doc['original'], media_type='application/octet-stream', headers={'Content-Disposition':'attachment; filename="document' + Path(doc['filename']).suffix.lower() + '"'})


@app.delete('/api/documents/{ident}')
def delete(ident: str, request: Request):
    if not STORE.delete(workspace(request), ident):
        raise HTTPException(404, 'Документ не найден')
    return {'deleted':True}


class Search(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=2,max_length=1000)
    strategy: str = 'versioned'
    family: str | None = Field(default=None,max_length=100)
    version: str | None = Field(default=None,max_length=40)
    as_of: str | None = None
    max_iterations: int = Field(default=3,ge=1,le=5)
    max_chunks: int = Field(default=20,ge=1,le=50)


@app.post('/api/search')
def search(body: Search, request: Request):
    if body.as_of:
        valid_date(body.as_of)
    try:
        return retrieve(STORE, workspace(request), **body.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e))


class Compare(BaseModel):
    left: str = Field(max_length=50)
    right: str = Field(max_length=50)


@app.post('/api/compare')
def compare(body: Compare, request: Request):
    ws = workspace(request)
    left, right = STORE.document(ws, body.left), STORE.document(ws, body.right)
    if not left or not right:
        raise HTTPException(404, 'Оба документа должны принадлежать вашему пространству')
    a = '\n\n'.join(c['text'] for c in left['chunks']).splitlines()
    b = '\n\n'.join(c['text'] for c in right['chunks']).splitlines()
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    changes = [{'kind':tag, 'old':a[i:j], 'new':b[k:l]} for tag,i,j,k,l in matcher.get_opcodes() if tag != 'equal']
    from .retrieval import conflicts
    hits = [{**c, 'family':d['family'], 'document':d['id'], 'version':d['version']} for d in [left,right] for c in d['chunks']]
    signals = conflicts(hits)
    return {'left':left['title'], 'right':right['title'], 'changes':changes, 'conflicts':signals,
            'affected_questions':[f'Какое значение поля «{c["field"]}» применимо к нужной дате и редакции?' for c in signals],
            'limitation':'Текстовые изменения и различия полей. Смысловые противоречия автоматически не доказаны.'}


WEB = ROOT/'apps/web/dist'
if WEB.exists():
    @app.get('/documents', include_in_schema=False)
    @app.get('/compare', include_in_schema=False)
    @app.get('/method', include_in_schema=False)
    def web_page():
        return FileResponse(WEB/'index.html')

    app.mount('/', StaticFiles(directory=WEB, html=True), name='web')
