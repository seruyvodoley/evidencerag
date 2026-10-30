import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(fileURLToPath(new URL('../../apps/web/dist-browser/', import.meta.url)));
const prefix = '/evidencerag/';
const port = Number(process.env.PORT || 5176);
const mime = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.wasm': 'application/wasm', '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.ico': 'image/vnd.microsoft.icon', '.whl': 'application/octet-stream', '.zip': 'application/zip',
};

const server = createServer(async (request, response) => {
  const pathname = decodeURIComponent(new URL(request.url || '/', 'http://localhost').pathname);
  if (!pathname.startsWith(prefix)) {
    response.writeHead(404).end('Not found');
    return;
  }
  const relative = pathname.slice(prefix.length) || 'index.html';
  const target = resolve(root, relative);
  if (target !== root && !target.startsWith(`${root}${sep}`)) {
    response.writeHead(400).end('Bad path');
    return;
  }
  try {
    const metadata = await stat(target);
    if (!metadata.isFile()) throw new Error('Not a file');
    const body = await readFile(target);
    const extension = relative.slice(relative.lastIndexOf('.')).toLowerCase();
    response.writeHead(200, { 'Content-Type': mime[extension] || 'application/octet-stream', 'Cache-Control': 'no-cache' }).end(body);
  } catch {
    if (relative.includes('.')) {
      response.writeHead(404).end('Not found');
      return;
    }
    const fallback = await readFile(resolve(root, '404.html'));
    response.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-cache' }).end(fallback);
  }
});

server.listen(port, '127.0.0.1', () => process.stdout.write(`Static mount preview: http://127.0.0.1:${port}${prefix}\n`));
process.on('SIGTERM', () => server.close(() => process.exit(0)));
