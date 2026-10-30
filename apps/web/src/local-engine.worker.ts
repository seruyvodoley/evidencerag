import sqlite3InitModule from '@sqlite.org/sqlite-wasm';
import parserSource from '../../api/evidencerag/parser.py?raw';
import retrievalSource from '../../api/evidencerag/retrieval.py?raw';
import storeSource from '../../api/evidencerag/store.py?raw';
import researchSource from '../../api/evidencerag/research_rag.py?raw';
import sqliteBridgeSource from './local-sqlite-bridge.py?raw';
import browserApiSource from './local-api.py?raw';
import catalogSource from '../../../datasets/demo/catalog.json?raw';
const demoModules = import.meta.glob('../../../datasets/demo/*.md', { query: '?raw', import: 'default', eager: true });
import { getWorkspaceToken } from './browser-vault';

const BASE_URL = import.meta.env.BASE_URL;
const encoder = new TextEncoder();
let initialization: Promise<void> | undefined;
let pyodide: any;
let sqlite3: any;
let database: any;
let progressCallback: any = null;
let operationInFlight = false;

function postProgress(id: number, message: string) {
  self.postMessage({ id, op: 'progress', message });
}

function decodeBlob(value: any): any {
  if (value && typeof value === 'object' && typeof value.$blob === 'string') {
    const binary = atob(value.$blob);
    return Uint8Array.from(binary, (character) => character.charCodeAt(0));
  }
  if (Array.isArray(value)) return value.map(decodeBlob);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, decodeBlob(item)]));
  return value;
}

function encodeBlob(value: any): any {
  if (value instanceof Uint8Array) {
    let binary = '';
    for (let offset = 0; offset < value.length; offset += 0x8000) binary += String.fromCharCode(...value.subarray(offset, offset + 0x8000));
    return { $blob: btoa(binary) };
  }
  return value;
}

function sqliteExec(sql: string, paramsJson = '[]'): string {
  if (!database) return JSON.stringify({ error: 'SQLite is not initialized' });
  const rows: Record<string, unknown>[] = [];
  try {
    database.exec({ sql, bind: decodeBlob(JSON.parse(paramsJson)), rowMode: 'object', resultRows: rows });
    const stats: Record<string, number>[] = [];
    database.exec({ sql: 'SELECT changes() AS rowcount, last_insert_rowid() AS lastrowid', rowMode: 'object', resultRows: stats });
    const command = sql.trimStart().split(/\s+/, 1)[0]?.toUpperCase();
    const dml = ['INSERT', 'UPDATE', 'DELETE', 'REPLACE'].includes(command || '');
    return JSON.stringify({ rows: rows.map((row) => Object.fromEntries(Object.entries(row).map(([key, value]) => [key, encodeBlob(value)]))), rowcount: dml ? stats[0]?.rowcount ?? -1 : -1, lastrowid: stats[0]?.lastrowid ?? null });
  } catch (error) {
    return JSON.stringify({ error: error instanceof Error ? error.message : String(error) });
  }
}

function setProgressHandler(callback: any, steps: number) {
  if (database) sqlite3.capi.sqlite3_progress_handler(database.pointer, 0, null, 0);
  if (progressCallback?.destroy) progressCallback.destroy();
  progressCallback = callback || null;
  if (database) sqlite3.capi.sqlite3_progress_handler(database.pointer, steps, progressCallback ? () => progressCallback() : null, 0);
}

function sourceFiles(): Record<string, string> {
  const files: Record<string, string> = {};
  for (const [path, value] of Object.entries(demoModules)) {
    const filename = path.split('/').pop();
    if (filename && typeof value === 'string') files[filename] = value;
  }
  return files;
}

async function initialize(id: number) {
  if (initialization) return initialization;
  initialization = (async () => {
    postProgress(id, 'Загружаем локальное ядро обработки…');
    const pyodideUrl = new URL(`${BASE_URL}vendor/pyodide/pyodide.mjs`, self.location.origin).href;
    const pyodideModule = await import(/* @vite-ignore */ pyodideUrl);
    pyodide = await pyodideModule.loadPyodide({ indexURL: new URL(`${BASE_URL}vendor/pyodide/`, self.location.origin).href });
    await pyodide.loadPackage('micropip');
    postProgress(id, 'Подключаем зафиксированные библиотеки PDF, DOCX и русского языка…');
    const wheelDirectory = new URL(`${BASE_URL}vendor/wheels/`, self.location.origin);
    const wheels = [
      'dawg2_python-0.9.0-py3-none-any.whl',
      'defusedxml-0.7.1-py2.py3-none-any.whl',
      'lxml-6.1.3-cp314-cp314-pyemscripten_2026_0_wasm32.whl',
      'pymorphy3-2.0.6-py3-none-any.whl',
      'pymorphy3_dicts_ru-2.4.417150.4580142-py2.py3-none-any.whl',
      'pypdf-6.21.4-py3-none-any.whl',
      'python_docx-1.2.0-py3-none-any.whl',
      'pyparsing-3.3.2-py3-none-any.whl',
      'setuptools-82.0.1-py3-none-any.whl',
      'typing_extensions-4.15.0-py3-none-any.whl',
    ].map((file) => new URL(file, wheelDirectory).href);
    await pyodide.runPythonAsync(`import micropip\nawait micropip.install(${JSON.stringify(wheels)}, deps=False)`);

    postProgress(id, 'Открываем защищённый локальный индекс…');
    sqlite3 = await sqlite3InitModule();
    const pool = await sqlite3.installOpfsSAHPoolVfs({ name: 'evidencerag_v1', directory: '/evidencerag', initialCapacity: 16 });
    database = new pool.OpfsSAHPoolDb('/evidence.sqlite3');
    self.postMessage({ id, op: 'runtime', sqliteVersion: sqlite3.version.libVersion, pyodideVersion: pyodide.version, persistent: true });

    (self as any).browser_sqlite_exec = sqliteExec;
    (self as any).browser_sqlite_set_progress_handler = setProgressHandler;
    pyodide.FS.mkdirTree('/work/evidencerag');
    pyodide.FS.writeFile('/work/sqlite_bridge.py', encoder.encode(sqliteBridgeSource));
    pyodide.FS.writeFile('/work/local_api.py', encoder.encode(browserApiSource));
    pyodide.FS.writeFile('/work/evidencerag/__init__.py', new Uint8Array());
    pyodide.FS.writeFile('/work/evidencerag/parser.py', encoder.encode(parserSource));
    pyodide.FS.writeFile('/work/evidencerag/retrieval.py', encoder.encode(retrievalSource));
    pyodide.FS.writeFile('/work/evidencerag/store.py', encoder.encode(storeSource));
    pyodide.FS.writeFile('/work/evidencerag/research_rag.py', encoder.encode(researchSource));
    pyodide.runPython("import sys; sys.path.insert(0, '/work')");
    pyodide.runPython(`import sqlite_bridge; sqlite_bridge.install('${sqlite3.version.libVersion}')`);
    const files = JSON.stringify(sourceFiles());
    pyodide.runPython(`import local_api; local_api.configure(${JSON.stringify(catalogSource)}, ${JSON.stringify(files)})`);
    // Force schema creation only after Pyodide is connected to this persistent DB.
    pyodide.runPython('local_api.STORE');
  })();
  try {
    await initialization;
  } catch (error) {
    initialization = undefined;
    throw error;
  }
}

async function handleMessage(event: MessageEvent) {
  const { id, op, method, path, request, token } = event.data;
  if (op !== 'api') return;
  if (operationInFlight) {
    self.postMessage({ id, op: 'result', status: 429, payload: { detail: 'Дождитесь завершения текущей операции' } });
    return;
  }
  operationInFlight = true;
  try {
    await initialize(id);
    const resultJson = pyodide.runPython(`local_api.handle(${JSON.stringify(method)}, ${JSON.stringify(path)}, ${JSON.stringify(JSON.stringify(request || {}))}, ${JSON.stringify(token || '')})`);
    const result = JSON.parse(resultJson.toString());
    if (result.payload?.debug) {
      if (import.meta.env.DEV) result.payload.detail = result.payload.debug;
      delete result.payload.debug;
    }
    self.postMessage({ id, op: 'result', ...result, ...(result.status === 200 && ['/workspaces', '/workspace/import'].includes(path) ? { token: result.payload.token } : {}) });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const detail = message.toLowerCase().includes('quota') || message.toLowerCase().includes('full')
      ? 'В браузере закончилось свободное место. Удалите документы или освободите место и повторите.'
      : import.meta.env.DEV ? message : 'Локальное ядро не смогло завершить обработку. Повторите или выберите другой файл.';
    self.postMessage({ id, op: 'result', status: 500, payload: { detail } });
  } finally {
    operationInFlight = false;
  }
}

self.addEventListener('message', (event: MessageEvent) => { void handleMessage(event); });
