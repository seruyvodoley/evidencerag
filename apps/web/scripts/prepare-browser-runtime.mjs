import { createHash } from 'node:crypto';
import { mkdir, readFile, readdir, rm, writeFile, copyFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const pyodideRoot = resolve(root, 'node_modules/pyodide');
const outputRoot = resolve(root, 'public/vendor');
const runtimeRoot = resolve(outputRoot, 'pyodide');
const wheelRoot = resolve(outputRoot, 'wheels');
const localWheelRoot = resolve(root, 'vendor/wheels');
const pyodideFiles = ['pyodide.mjs', 'pyodide.asm.mjs', 'pyodide.asm.wasm', 'python_stdlib.zip', 'pyodide-lock.json', 'micropip-0.11.1-py3-none-any.whl'];

await rm(outputRoot, { recursive: true, force: true });
await mkdir(runtimeRoot, { recursive: true });
await mkdir(wheelRoot, { recursive: true });
for (const name of pyodideFiles) await copyFile(resolve(pyodideRoot, name), resolve(runtimeRoot, name));

const wasmName = 'pyodide.asm.wasm';
const wasmPath = resolve(runtimeRoot, wasmName);
const wasmBytes = await readFile(wasmPath);
const wasmPartSize = 1024 * 1024;
const wasmParts = [];
for (let offset = 0, index = 0; offset < wasmBytes.length; offset += wasmPartSize, index += 1) {
  const filename = `${wasmName}.part-${String(index).padStart(2, '0')}`;
  const bytes = wasmBytes.subarray(offset, Math.min(offset + wasmPartSize, wasmBytes.length));
  await writeFile(resolve(runtimeRoot, filename), bytes);
  wasmParts.push({
    file: filename,
    size_bytes: bytes.length,
    sha256: createHash('sha256').update(bytes).digest('hex'),
  });
}
await rm(wasmPath);
await writeFile(resolve(runtimeRoot, `${wasmName}.parts.json`), JSON.stringify({
  total_size_bytes: wasmBytes.length,
  parts: wasmParts,
}, null, 2) + '\n');

const wheelNames = (await readdir(localWheelRoot)).filter((name) => name.endsWith('.whl')).sort();
if (wheelNames.length !== 10) throw new Error(`Expected 10 pinned wheels, found ${wheelNames.length}`);
const manifest = [];
for (const name of wheelNames) {
  const source = resolve(localWheelRoot, name);
  await copyFile(source, resolve(wheelRoot, name));
  const bytes = await readFile(source);
  manifest.push({ file: name, sha256: createHash('sha256').update(bytes).digest('hex'), bytes: bytes.length });
}
const lock = JSON.parse(await readFile(resolve(pyodideRoot, 'pyodide-lock.json'), 'utf8'));
if (lock.info.python !== '3.14.2' || lock.info.abi_version !== '2026_0') throw new Error('Unexpected Pyodide lock metadata');
await writeFile(resolve(outputRoot, 'browser-runtime-lock.json'), JSON.stringify({
  pyodide: '314.0.7',
  sqliteWasm: '3.54.1',
  pyodideWasm: { total_size_bytes: wasmBytes.length, parts: wasmParts },
  pythonWheels: manifest,
}, null, 2) + '\n');
process.stdout.write(`Prepared Pyodide runtime and ${manifest.length} pinned wheels in ${outputRoot}\n`);
