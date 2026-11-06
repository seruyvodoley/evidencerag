import { Unzip, UnzipInflate, UnzipPassThrough } from 'fflate';

const MAX_ARCHIVE = 25_000_000;
const MAX_FILES = 20;
const MAX_ENTRY = 10_000_000;
const MAX_TOTAL = 25_000_000;
const SUPPORTED = new Set(['.pdf', '.docx', '.txt', '.md']);

function inspectDirectory(data: Uint8Array): string[] {
  if (data.length < 22 || data.length > MAX_ARCHIVE) throw new Error('ZIP пустой или превышает 25 МБ.');
  const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
  const from = Math.max(0, data.length - 65_557);
  let eocd = -1;
  for (let i = data.length - 22; i >= from; i--) if (view.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
  if (eocd < 0 || view.getUint16(eocd + 4, true) !== 0 || view.getUint16(eocd + 6, true) !== 0) throw new Error('ZIP-архив повреждён или использует неподдерживаемое разбиение.');
  const count = view.getUint16(eocd + 10, true), size = view.getUint32(eocd + 12, true), offset = view.getUint32(eocd + 16, true);
  if (count > 100 || count === 0xffff || size === 0xffffffff || offset === 0xffffffff || offset + size > eocd) throw new Error('В архиве слишком много файлов или используется ZIP64.');
  const paths: string[] = [];
  let cursor = offset, files = 0, total = 0;
  const decoder = new TextDecoder('utf-8', { fatal: true });
  for (let i = 0; i < count; i++) {
    if (view.getUint32(cursor, true) !== 0x02014b50) throw new Error('Центральный каталог ZIP повреждён.');
    const madeBy = view.getUint16(cursor + 4, true), flags = view.getUint16(cursor + 8, true), method = view.getUint16(cursor + 10, true);
    const compressed = view.getUint32(cursor + 20, true), original = view.getUint32(cursor + 24, true);
    const nameLength = view.getUint16(cursor + 28, true), extraLength = view.getUint16(cursor + 30, true), commentLength = view.getUint16(cursor + 32, true);
    const external = view.getUint32(cursor + 38, true);
    if (cursor + 46 + nameLength + extraLength + commentLength > offset + size || flags & 1 || ![0, 8].includes(method) || compressed === 0xffffffff || original === 0xffffffff) throw new Error('В архиве есть зашифрованный или неподдерживаемый элемент.');
    const name = decoder.decode(data.subarray(cursor + 46, cursor + 46 + nameLength));
    if (name.includes('\0') || name.startsWith('/') || /^[a-z]:/i.test(name) || name.includes('\\') || name.split('/').includes('..')) throw new Error('В архиве обнаружен небезопасный путь.');
    const unix = (madeBy >>> 8) === 3, mode = external >>> 16;
    if (unix && (mode & 0xf000) === 0xa000) throw new Error('Символические ссылки в ZIP не поддерживаются.');
    if (!name.endsWith('/')) {
      files++;
      const suffix = name.slice(name.lastIndexOf('.')).toLowerCase();
      if (!SUPPORTED.has(suffix)) throw new Error(`Неподдерживаемый файл в ZIP: ${name.slice(-80)}`);
      if (original > MAX_ENTRY || compressed > MAX_ARCHIVE || (original > 0 && compressed === 0)) throw new Error('Размер файла в архиве превышает допустимый предел.');
      if (suffix === '.zip') throw new Error('Вложенные ZIP-архивы не поддерживаются.');
      total += original;
      if (total > MAX_TOTAL || files > MAX_FILES) throw new Error('Архив превышает лимит 20 файлов или 25 МБ распакованных данных.');
      paths.push(name);
    }
    cursor += 46 + nameLength + extraLength + commentLength;
  }
  if (cursor !== offset + size || !paths.length) throw new Error('В ZIP нет поддерживаемых документов.');
  return paths;
}

export async function extractDocumentZip(file: File): Promise<File[]> {
  if (file.size > MAX_ARCHIVE) throw new Error('ZIP-архив должен быть не больше 25 МБ.');
  const bytes = new Uint8Array(await file.arrayBuffer());
  const expected = inspectDirectory(bytes);
  return new Promise((resolve, reject) => {
    const results: File[] = [];
    const chunks = new Map<string, Uint8Array[]>();
    let emitted = 0, error: Error | null = null;
    const unzip = new Unzip((entry) => {
      if (entry.name.endsWith('/')) return;
      entry.ondata = (err, chunk, final) => {
        if (err) { error = new Error('Не удалось безопасно распаковать ZIP.'); return; }
        const list = chunks.get(entry.name) || [];
        list.push(chunk); chunks.set(entry.name, list);
        emitted += chunk.length;
        if (emitted > MAX_TOTAL || list.reduce((n, part) => n + part.length, 0) > MAX_ENTRY) { error = new Error('Фактический распакованный размер превысил лимит.'); void entry.terminate(); return; }
        if (final) {
          const size = list.reduce((n, part) => n + part.length, 0);
          if (entry.originalSize !== undefined && size !== entry.originalSize) { error = new Error('Размер распакованного файла не совпадает с каталогом ZIP.'); return; }
          const filename = entry.name.split('/').pop() || 'document';
          results.push(new File(list.map((part) => new Uint8Array(part).buffer as ArrayBuffer), filename, { type: 'application/octet-stream' }));
          chunks.delete(entry.name);
        }
      };
      entry.start();
    });
    unzip.register(UnzipInflate); unzip.register(UnzipPassThrough);
    try {
      for (let offset = 0; offset < bytes.length; offset += 65_536) unzip.push(bytes.subarray(offset, offset + 65_536), offset + 65_536 >= bytes.length);
      queueMicrotask(() => {
        if (error) reject(error);
        else if (results.length !== expected.length) reject(new Error('Не все файлы архива удалось распаковать.'));
        else resolve(results);
      });
    } catch { reject(error || new Error('ZIP-архив повреждён.')); }
  });
}
