const DATABASE = 'evidencerag-browser-v1';
const STORE = 'settings';
let database: Promise<IDBDatabase> | undefined;

function openDatabase(): Promise<IDBDatabase> {
  if (!database) {
    database = new Promise((resolve, reject) => {
      const request = indexedDB.open(DATABASE, 1);
      request.onupgradeneeded = () => request.result.createObjectStore(STORE);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error('Не удалось открыть локальные настройки'));
    });
  }
  return database;
}

export async function getWorkspaceToken(): Promise<string | null> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const request = db.transaction(STORE, 'readonly').objectStore(STORE).get('workspace-token');
    request.onsuccess = () => resolve(typeof request.result === 'string' ? request.result : null);
    request.onerror = () => reject(request.error || new Error('Не удалось прочитать локальное пространство'));
  });
}

export async function setWorkspaceToken(token: string | null): Promise<void> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE, 'readwrite');
    const store = transaction.objectStore(STORE);
    if (token) store.put(token, 'workspace-token');
    else store.delete('workspace-token');
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error || new Error('Не удалось сохранить локальное пространство'));
    transaction.onabort = () => reject(transaction.error || new Error('Сохранение локального пространства отменено'));
  });
}
