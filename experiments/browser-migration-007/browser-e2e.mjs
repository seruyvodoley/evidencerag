import { spawn } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../../apps/web/node_modules/playwright/index.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '../..');
const vite = resolve(root, 'apps/web/node_modules/vite/bin/vite.js');
const server = spawn(process.execPath, [vite, resolve(here, 'browser'), '--host', '127.0.0.1', '--port', '4179', '--strictPort'], {
  cwd: root,
  stdio: ['ignore', 'pipe', 'pipe'],
});
let serverOutput = '';
server.stdout.on('data', (chunk) => { serverOutput += chunk.toString(); });
server.stderr.on('data', (chunk) => { serverOutput += chunk.toString(); });

let browser;
try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch('http://127.0.0.1:4179/');
      if (response.ok) { ready = true; break; }
    } catch {}
    await delay(100);
  }
  if (!ready) throw new Error(`Vite did not start:\n${serverOutput}`);

  browser = await chromium.launch({ headless: true, executablePath: chromium.executablePath() });
  const page = await browser.newPage();
  const errors = [];
  const requests = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('request', (request) => requests.push(request.url()));
  await page.goto('http://127.0.0.1:4179/');
  await page.waitForFunction(() => window.auditResult, null, { timeout: 30_000 });
  const result = await page.evaluate(() => window.auditResult);
  const externalRequests = requests.filter((url) => new URL(url).origin !== 'http://127.0.0.1:4179');
  if (result.error || errors.length || externalRequests.length || !result.persistedAcrossWorkerRestart || result.rowsAfterDelete !== 0) {
    throw new Error(JSON.stringify({ result, errors, externalRequests }, null, 2));
  }
  process.stdout.write(`${JSON.stringify({ result, pageErrors: errors, networkRequests: requests, externalRequests }, null, 2)}\n`);
} finally {
  await browser?.close();
  server.kill('SIGTERM');
}
