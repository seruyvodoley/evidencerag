import { copyFile, readFile, writeFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const outputName = process.argv[2] || 'dist';
const output = resolve(dirname(fileURLToPath(import.meta.url)), '..', outputName);
const indexPath = resolve(output, 'index.html');
const indexHtml = await readFile(indexPath, 'utf8');
const pagesBasePath = process.env.VITE_PAGES_BASE_PATH;
if (pagesBasePath) {
  if (!/^\/[a-zA-Z0-9_-]+\/$/.test(pagesBasePath)) throw new Error('VITE_PAGES_BASE_PATH must be a single project prefix such as /evidencerag/');
  await writeFile(indexPath, indexHtml.replace('<head>', `<head><base href="${pagesBasePath}">`));
}
await copyFile(indexPath, resolve(output, '404.html'));
process.stdout.write('Prepared a static 404.html SPA fallback.\n');
