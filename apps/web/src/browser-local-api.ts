import { getWorkspaceToken, requestPersistentStorage, setWorkspaceToken } from './browser-vault';
import catalogSource from '../../../datasets/demo/catalog.json?raw';

type LocalResult = { ok: boolean; status: number; payload: any };
type Pending = { resolve: (value: LocalResult) => void; reject: (error: Error) => void; progress?: (message: string) => void };

let worker: Worker | undefined;
let nextId = 1;
const pending = new Map<number, Pending>();

function getWorker(): Worker {
  if (!worker) {
    worker = new Worker(new URL('./local-engine.worker.ts', import.meta.url), { type: 'module', name: 'evidencerag-local-engine' });
    worker.onmessage = ({ data }) => {
      const item = pending.get(data.id);
      if (!item) return;
      if (data.op === 'runtime') return;
      if (data.op === 'progress') {
        item.progress?.(data.message);
        return;
      }
      if (data.op === 'result') {
        pending.delete(data.id);
        const result = { ok: data.status >= 200 && data.status < 300, status: data.status, payload: data.payload };
        if (data.token) void setWorkspaceToken(data.token).then(() => item.resolve(result), item.reject);
        else item.resolve(result);
      }
    };
    worker.onerror = () => {
      for (const item of pending.values()) item.reject(new Error('Локальный Worker завершился с ошибкой'));
      pending.clear();
      worker?.terminate();
      worker = undefined;
    };
  }
  return worker;
}

async function normalizeRequest(options: RequestInit): Promise<any> {
  if (options.body instanceof FormData) {
    const values: Record<string, any> = {};
    for (const [key, value] of options.body.entries()) {
      if (value instanceof File) {
        const bytes = new Uint8Array(await value.arrayBuffer());
        let binary = '';
        for (let offset = 0; offset < bytes.length; offset += 0x8000) binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
        values.filename = value.name;
        values.file_b64 = btoa(binary);
      } else values[key] = String(value);
    }
    return values;
  }
  if (typeof options.body === 'string') {
    try { return JSON.parse(options.body); } catch { return {}; }
  }
  return {};
}

function requestWorker(method: string, path: string, request: any, token: string | null, progress?: (message: string) => void): Promise<LocalResult> {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      pending.delete(id);
      worker?.terminate();
      worker = undefined;
      reject(new Error('Локальная обработка превысила допустимое время. Повторите с меньшим файлом.'));
    }, 180_000);
    pending.set(id, {
      progress: (message) => { progress?.(message); },
      resolve: (value) => { clearTimeout(timeout); resolve(value); },
      reject: (error) => { clearTimeout(timeout); reject(error); },
    });
    getWorker().postMessage({ id, op: 'api', method, path, request, token });
  });
}

export async function localApi(path: string, options: RequestInit = {}, progress?: (message: string) => void): Promise<LocalResult> {
  const method = (options.method || 'GET').toUpperCase();
  if (method === 'GET' && path === '/demos') {
    const catalog = JSON.parse(catalogSource);
    return { ok: true, status: 200, payload: catalog.map((item: any) => ({ id: item.id, name: item.name, description: item.description, questions: item.questions, count: item.documents.length })) };
  }
  if (method === 'POST' && path === '/workspaces') await requestPersistentStorage();
  const token = await getWorkspaceToken();
  if (method === 'GET' && path === '/session' && !token) return { ok: false, status: 401, payload: { detail: 'Локального пространства пока нет' } };
  const request = await normalizeRequest(options);
  const result = await requestWorker(method, path, request, token, progress);
  if (method === 'POST' && path === '/workspace/import' && result.ok && result.payload?.token) {
    await setWorkspaceToken(result.payload.token);
    const finalized = await requestWorker('POST', '/workspace/import/finalize', { old_token: token }, result.payload.token, progress);
    if (!finalized.ok) throw new Error(finalized.payload?.detail || 'Импорт подготовлен, но завершить замену пространства не удалось. Перезагрузите страницу и проверьте документы.');
  }
  if (method === 'DELETE' && path === '/workspace' && result.ok) await setWorkspaceToken(null);
  return result;
}

export async function downloadLocalOriginal(path: string): Promise<{ filename: string; blob: Blob }> {
  const result = await localApi(path);
  if (!result.ok) throw new Error(result.payload?.detail || 'Не удалось получить оригинал');
  const binary = atob(result.payload.data_b64);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  return { filename: result.payload.filename, blob: new Blob([bytes], { type: 'application/octet-stream' }) };
}
