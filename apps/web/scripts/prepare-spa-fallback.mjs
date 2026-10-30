import { copyFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const outputName = process.argv[2] || 'dist';
const output = resolve(dirname(fileURLToPath(import.meta.url)), '..', outputName);
await copyFile(resolve(output, 'index.html'), resolve(output, '404.html'));
process.stdout.write('Prepared a static 404.html SPA fallback.\n');
