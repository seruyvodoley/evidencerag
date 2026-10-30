import { spawnSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import { resolve, dirname, delimiter } from 'node:path';
import { fileURLToPath } from 'node:url';
import sqlite3InitModule from '@sqlite.org/sqlite-wasm';
import { loadPyodide } from 'pyodide';

console.log = (...values) => process.stderr.write(`${values.join(' ')}\n`);

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '../..');
const python = process.env.PYTHON ?? resolve(root, '.venv/bin/python');
const sqlite3 = await sqlite3InitModule();
const db = new sqlite3.oo1.DB(':memory:');
let progressCallback = null;
const decodeBlob = (value) => {
  if (value && typeof value === 'object' && typeof value.$blob === 'string') {
    const binary = atob(value.$blob);
    return Uint8Array.from(binary, (character) => character.charCodeAt(0));
  }
  if (Array.isArray(value)) return value.map(decodeBlob);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, decodeBlob(item)]));
  }
  return value;
};
const encodeBlob = (value) => {
  if (value instanceof Uint8Array) {
    let binary = '';
    for (let offset = 0; offset < value.length; offset += 0x8000) {
      binary += String.fromCharCode(...value.subarray(offset, offset + 0x8000));
    }
    return { $blob: btoa(binary) };
  }
  return value;
};
const browserSqliteExec = (sql, paramsJson = '[]') => {
  const rows = [];
  try {
    db.exec({ sql, bind: decodeBlob(JSON.parse(paramsJson)), rowMode: 'object', resultRows: rows });
    const stats = [];
    db.exec({
      sql: 'SELECT changes() AS rowcount, last_insert_rowid() AS lastrowid',
      rowMode: 'object',
      resultRows: stats,
    });
    const command = sql.trimStart().split(/\s+/, 1)[0]?.toUpperCase();
    const dml = ['INSERT', 'UPDATE', 'DELETE', 'REPLACE'].includes(command);
    return JSON.stringify({
      rows: rows.map((row) => Object.fromEntries(Object.entries(row).map(([key, value]) => [key, encodeBlob(value)]))),
      rowcount: dml ? stats[0]?.rowcount ?? -1 : -1,
      lastrowid: stats[0]?.lastrowid ?? null,
    });
  } catch (error) {
    return JSON.stringify({ error: error.message || String(error) });
  }
};
const browserSqliteSetProgressHandler = (callback, steps) => {
  sqlite3.capi.sqlite3_progress_handler(db.pointer, 0, null, 0);
  progressCallback = callback || null;
  if (progressCallback) sqlite3.capi.sqlite3_progress_handler(db.pointer, steps, () => progressCallback(), 0);
};
const native = spawnSync(python, [resolve(here, 'probe.py')], {
  cwd: root,
  env: {
    ...process.env,
    PYTHONPATH: [resolve(root, 'apps/api'), root, process.env.PYTHONPATH].filter(Boolean).join(delimiter),
  },
  encoding: 'utf8',
  maxBuffer: 10 * 1024 * 1024,
});
if (native.status !== 0) {
  process.stderr.write(native.stderr || 'Native Python parity probe failed.\n');
  process.exit(native.status ?? 1);
}

const pyodide = await loadPyodide();
pyodide.setStdout({ batched: (line) => process.stderr.write(`${line}\n`) });
await pyodide.loadPackage('micropip');
await pyodide.runPythonAsync(`
import micropip
await micropip.install([
    'pymorphy3==2.0.6',
    'pymorphy3-dicts-ru==2.4.417150.4580142',
    'dawg2-python',
    'pypdf==6.21.4',
    'python-docx==1.2.0',
    'defusedxml',
])
`);

pyodide.FS.mkdirTree('/work/evidencerag');
pyodide.FS.mkdirTree('/work/fixtures');
pyodide.FS.writeFile('/work/sqlite_bridge.py', await readFile(resolve(root, 'apps/web/src/local-sqlite-bridge.py')));
for (const filename of ['__init__.py', 'parser.py', 'retrieval.py', 'store.py', 'research_rag.py']) {
  pyodide.FS.writeFile(
    `/work/evidencerag/${filename}`,
    await readFile(resolve(root, 'apps/api/evidencerag', filename), 'utf8'),
  );
}
for (const filename of ['table-heading.docx', 'two-page.pdf', 'scanned.pdf']) {
  pyodide.FS.writeFile(
    `/work/fixtures/${filename}`,
    await readFile(resolve(here, 'fixtures', filename)),
  );
}
pyodide.FS.writeFile('/work/probe.py', await readFile(resolve(here, 'probe.py')));
pyodide.runPython("import sys; sys.path.insert(0, '/work')");
globalThis.browser_sqlite_exec = browserSqliteExec;
globalThis.browser_sqlite_set_progress_handler = browserSqliteSetProgressHandler;
pyodide.runPython(`import sqlite_bridge; sqlite_bridge.install('${sqlite3.version.libVersion}')`);

const actual = JSON.parse(pyodide.runPython(`
import importlib, json
module = importlib.import_module('probe')
json.dumps(module.probe(), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
`).toString());
const expected = JSON.parse(native.stdout);
const storeStatus = JSON.parse(pyodide.runPython(`
import importlib, json
module = importlib.import_module('probe')
json.dumps(module.store_probe(), ensure_ascii=False, sort_keys=True)
`).toString());

const nativeSqliteVersion = expected.sqlite_version;
const pyodideSqliteVersion = actual.sqlite_version;
delete expected.sqlite_version;
delete actual.sqlite_version;
let maximumScoreDelta = 0;
function equivalent(left, right, path = '') {
  if (typeof left === 'number' && typeof right === 'number' && path.endsWith('.score')) {
    const delta = Math.abs(left - right);
    maximumScoreDelta = Math.max(maximumScoreDelta, delta);
    return delta <= 1e-18;
  }
  if (left === right) return true;
  if (Array.isArray(left) && Array.isArray(right)) {
    return left.length === right.length && left.every((value, index) => equivalent(value, right[index], `${path}[${index}]`));
  }
  if (left && right && typeof left === 'object' && typeof right === 'object') {
    const leftKeys = Object.keys(left).sort();
    const rightKeys = Object.keys(right).sort();
    return leftKeys.length === rightKeys.length
      && leftKeys.every((key, index) => key === rightKeys[index] && equivalent(left[key], right[key], `${path}.${key}`));
  }
  return false;
}
const parity = equivalent(expected, actual);
process.stdout.write(`${JSON.stringify({
  pyodide: pyodide.version,
  sqlite_wasm: sqlite3.version.libVersion,
  sqlite_versions: { native: nativeSqliteVersion, pyodide: pyodideSqliteVersion },
  parser_morphology_controller_parity: parity,
  bm25_absolute_score_tolerance: 1e-18,
  bm25_maximum_absolute_delta: maximumScoreDelta,
  sqlite_fts5_store: storeStatus,
  probe: actual,
}, null, 2)}\n`);
if (!parity) process.exitCode = 1;
