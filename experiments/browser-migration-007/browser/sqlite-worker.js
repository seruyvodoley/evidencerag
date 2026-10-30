import sqlite3InitModule from '@sqlite.org/sqlite-wasm';

self.onmessage = async ({ data }) => {
  const { id, op } = data;
  try {
    if (op === 'init') {
      const sqlite3 = await sqlite3InitModule();
      const pool = await sqlite3.installOpfsSAHPoolVfs({
        name: `erag_audit_${id}`,
        directory: `/.${id}`,
        initialCapacity: 6,
      });
      const db = new pool.OpfsSAHPoolDb(`/${id}.sqlite3`);
      db.exec('CREATE VIRTUAL TABLE IF NOT EXISTS audit_fts USING fts5(text)');
      db.exec("INSERT INTO audit_fts(audit_fts, rank) VALUES('secure-delete', 1)");
      self.auditState = { sqlite3, pool, db };
      self.postMessage({ op, sqliteVersion: sqlite3.version.libVersion, secureDelete: true });
      return;
    }

    const { db, pool } = self.auditState || {};
    if (!db) throw new Error('SQLite worker is not initialized');
    if (op === 'seed') {
      db.exec('DELETE FROM audit_fts');
      db.exec("INSERT INTO audit_fts(text) VALUES('privacy_marker_007')");
      self.postMessage({ op });
    } else if (op === 'read') {
      const resultRows = [];
      db.exec({
        sql: "SELECT count(*) AS count FROM audit_fts WHERE audit_fts MATCH 'privacy_marker_007'",
        rowMode: 'object',
        resultRows,
      });
      self.postMessage({ op, count: resultRows[0].count });
    } else if (op === 'delete') {
      db.exec("DELETE FROM audit_fts WHERE audit_fts MATCH 'privacy_marker_007'");
      const resultRows = [];
      db.exec({
        sql: "SELECT count(*) AS count FROM audit_fts WHERE audit_fts MATCH 'privacy_marker_007'",
        rowMode: 'object',
        resultRows,
      });
      self.postMessage({ op, count: resultRows[0].count });
    } else if (op === 'cleanup') {
      db.close();
      await pool.removeVfs();
      self.postMessage({ op });
    } else {
      throw new Error(`Unknown operation: ${op}`);
    }
  } catch (error) {
    self.postMessage({ op, error: error.message || String(error) });
  }
};
