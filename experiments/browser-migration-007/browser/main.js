const workerUrl = new URL('./sqlite-worker.js', import.meta.url);
const status = document.querySelector('#status');
const run = async () => {
  const id = `codex-audit-${crypto.randomUUID().replaceAll('-', '')}`;
  const startWorker = () => new Worker(workerUrl, { type: 'module' });
  const request = (worker, op) => new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`${op} timed out`)), 15_000);
    worker.onmessage = ({ data }) => {
      clearTimeout(timer);
      if (data.error) reject(new Error(data.error));
      else resolve(data);
    };
    worker.postMessage({ id, op });
  });

  let worker = startWorker();
  try {
    const ready = await request(worker, 'init');
    await request(worker, 'seed');
    worker.terminate();

    worker = startWorker();
    await request(worker, 'init');
    const reopened = await request(worker, 'read');
    const deleted = await request(worker, 'delete');
    const cleared = await request(worker, 'read');
    if (reopened.count !== 1 || deleted.count !== 0 || cleared.count !== 0) {
      throw new Error('OPFS persistence or deletion check failed');
    }
    status.textContent = JSON.stringify({
      sqliteVersion: ready.sqliteVersion,
      secureDelete: ready.secureDelete,
      persistedAcrossWorkerRestart: reopened.count === 1,
      rowsAfterDelete: cleared.count,
    });
    window.auditResult = JSON.parse(status.textContent);
  } catch (error) {
    status.textContent = JSON.stringify({ error: error.message });
    window.auditResult = { error: error.message };
  } finally {
    try { await request(worker, 'cleanup'); } catch {}
    worker.terminate();
  }
};
void run();
