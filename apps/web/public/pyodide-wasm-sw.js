const WASM_PATH = /\/vendor\/pyodide\/pyodide\.asm\.wasm$/;

self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method === 'GET' && url.origin === self.location.origin && WASM_PATH.test(url.pathname)) {
    event.respondWith(assembleWasm().catch(() => new Response('WebAssembly could not be assembled', { status: 502 })));
  }
});

async function assembleWasm() {
  const baseUrl = new URL('./', self.location.href);
  const manifestUrl = new URL('vendor/pyodide/pyodide.asm.wasm.parts.json', baseUrl);
  const manifestResponse = await fetch(manifestUrl);
  if (!manifestResponse.ok) return new Response('WebAssembly manifest is unavailable', { status: 502 });
  const manifest = await manifestResponse.json();
  const total = manifest?.total_size_bytes;
  const parts = manifest?.parts;
  if (!Number.isSafeInteger(total) || total < 1 || total > 64_000_000 || !Array.isArray(parts) || parts.length < 1 || parts.length > 64) {
    return new Response('WebAssembly manifest is invalid', { status: 502 });
  }

  const chunks = await Promise.all(parts.map(async (part, index) => {
    const filename = `pyodide.asm.wasm.part-${String(index).padStart(2, '0')}.wasm`;
    if (part?.file !== filename || !Number.isSafeInteger(part.size_bytes) || part.size_bytes < 1 || typeof part.sha256 !== 'string') {
      throw new Error('WebAssembly manifest contains an invalid part');
    }
    const response = await fetch(new URL(`vendor/pyodide/${filename}`, baseUrl));
    if (!response.ok) throw new Error(`WebAssembly part returned HTTP ${response.status}`);
    const bytes = new Uint8Array(await response.arrayBuffer());
    if (bytes.length !== part.size_bytes) throw new Error('WebAssembly part is incomplete');
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    const hash = Array.from(new Uint8Array(digest), (value) => value.toString(16).padStart(2, '0')).join('');
    if (hash !== part.sha256) throw new Error('WebAssembly part checksum mismatch');
    return bytes;
  }));
  if (chunks.reduce((sum, chunk) => sum + chunk.length, 0) !== total) {
    return new Response('WebAssembly size does not match manifest', { status: 502 });
  }

  const wasm = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    wasm.set(chunk, offset);
    offset += chunk.length;
  }
  return new Response(wasm, {
    status: 200,
    headers: { 'Content-Type': 'application/wasm', 'Cache-Control': 'no-store' },
  });
}
