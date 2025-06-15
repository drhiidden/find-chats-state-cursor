import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import * as sqlite3 from 'sqlite3';
import { MigrationSummary, KVRow, SQLiteTable, SQLiteRow, WorkspaceState } from './types';
import { isSQLiteFile } from './utils';

export async function migrateSQLiteChats(srcDb: string, dstDb: string, summary: MigrationSummary): Promise<void> {
    return new Promise((resolve, reject) => {
        const srcConn = new sqlite3.Database(srcDb);
        const dstConn = new sqlite3.Database(dstDb);

        srcConn.serialize(() => {
            // Activar foreign keys y modo WAL
            dstConn.run("PRAGMA foreign_keys = ON");
            dstConn.run("PRAGMA journal_mode = WAL");

            // Buscar tablas relacionadas con chat
            srcConn.all<SQLiteTable>("SELECT name FROM sqlite_master WHERE type='table'", (err, tables) => {
                if (err) {
                    reject(err);
                    return;
                }

                const chatTables = tables
                    .map(t => t.name)
                    .filter(name => name.toLowerCase().includes('chat') || name.toLowerCase().includes('message'));

                if (chatTables.length === 0) {
                    resolve();
                    return;
                }

                let completedTables = 0;
                chatTables.forEach(table => {
                    // Verificar si la tabla existe en el destino
                    dstConn.get<SQLiteTable>(`SELECT name FROM sqlite_master WHERE type='table' AND name=?`, [table], (err, row) => {
                        if (err) {
                            reject(err);
                            return;
                        }

                        if (!row) {
                            // Crear la tabla en el destino
                            srcConn.get<SQLiteTable>(`SELECT sql FROM sqlite_master WHERE type='table' AND name=?`, [table], (err, row) => {
                                if (err) {
                                    reject(err);
                                    return;
                                }

                                if (row?.sql) {
                                    dstConn.run(row.sql, err => {
                                        if (err) {
                                            reject(err);
                                            return;
                                        }

                                        migrateTableData(table);
                                    });
                                }
                            });
                        } else {
                            migrateTableData(table);
                        }
                    });
                });

                function migrateTableData(table: string) {
                    srcConn.all<SQLiteRow>(`SELECT * FROM ${table}`, (err, rows) => {
                        if (err) {
                            reject(err);
                            return;
                        }

                        if (rows.length === 0) {
                            completedTables++;
                            if (completedTables === chatTables.length) {
                                resolve();
                            }
                            return;
                        }

                        // Insertar datos en lotes
                        const batchSize = 100;
                        for (let i = 0; i < rows.length; i += batchSize) {
                            const batch = rows.slice(i, i + batchSize);
                            const columns = Object.keys(rows[0]);
                            const placeholders = batch.map(() => '(' + Array(columns.length).fill('?').join(',') + ')').join(',');
                            const values = batch.flatMap(row => columns.map(col => row[col]));

                            dstConn.run(`INSERT OR IGNORE INTO ${table} (${columns.join(',')}) VALUES ${placeholders}`, values, err => {
                                if (err) {
                                    reject(err);
                                    return;
                                }

                                summary.chatsMigrated += batch.length;
                            });
                        }

                        completedTables++;
                        if (completedTables === chatTables.length) {
                            resolve();
                        }
                    });
                }
            });
        });
    });
}

export async function migrateKVTable(srcDb: string, dstDb: string, tableName: string, summary: MigrationSummary, interestingKeys: string[]): Promise<void> {
    return new Promise((resolve, reject) => {
        const srcConn = new sqlite3.Database(srcDb);
        const dstConn = new sqlite3.Database(dstDb);

        srcConn.all<KVRow>(`SELECT key, value FROM ${tableName}`, (err, rows) => {
            if (err) {
                reject(err);
                return;
            }

            let migrated = 0;
            let overwritten = 0;

            const processRow = (index: number) => {
                if (index >= rows.length) {
                    if (tableName === 'cursorDiskKV') {
                        summary.cursorDiskKVMigrated = migrated;
                        summary.cursorDiskKVOverwritten = overwritten;
                    } else if (tableName === 'itemTable') {
                        summary.itemTableMigrated = migrated;
                        summary.itemTableOverwritten = overwritten;
                    }
                    resolve();
                    return;
                }

                const row = rows[index];
                if (interestingKeys.some(key => row.key.startsWith(key))) {
                    dstConn.get<KVRow>(`SELECT value FROM ${tableName} WHERE key = ?`, [row.key], (err, existing) => {
                        if (err) {
                            reject(err);
                            return;
                        }

                        if (!existing) {
                            dstConn.run(`INSERT INTO ${tableName} (key, value) VALUES (?, ?)`, [row.key, row.value], err => {
                                if (err) {
                                    reject(err);
                                    return;
                                }
                                migrated++;
                                processRow(index + 1);
                            });
                        } else if (existing.value !== row.value) {
                            dstConn.run(`UPDATE ${tableName} SET value = ? WHERE key = ?`, [row.value, row.key], err => {
                                if (err) {
                                    reject(err);
                                    return;
                                }
                                overwritten++;
                                processRow(index + 1);
                            });
                        } else {
                            processRow(index + 1);
                        }
                    });
                } else {
                    processRow(index + 1);
                }
            };

            processRow(0);
        });
    });
}

export async function migrateWorkspace(sourceWorkspace: WorkspaceState, targetWorkspacePath: string): Promise<MigrationSummary> {
    const summary: MigrationSummary = {
        filesCopied: [],
        filesSkipped: [],
        foldersCopied: [],
        chatsMigrated: 0,
        cursorDiskKVMigrated: 0,
        cursorDiskKVOverwritten: 0,
        itemTableMigrated: 0,
        itemTableOverwritten: 0
    };

    const sourcePath = path.join(process.env.APPDATA!, 'Cursor', 'User', 'workspaceStorage', sourceWorkspace.hash);
    const targetStoragePath = path.join(process.env.APPDATA!, 'Cursor', 'User', 'workspaceStorage');

    // Buscar el hash del workspace destino
    const targetHash = crypto.createHash('md5')
        .update('file:///' + targetWorkspacePath.replace(/\\/g, '/').toLowerCase())
        .digest('hex');

    const targetWorkspaceStoragePath = path.join(targetStoragePath, targetHash);

    // Migrar archivos y carpetas
    async function migrateDirectory(src: string, dst: string) {
        const entries = await fs.promises.readdir(src, { withFileTypes: true });

        for (const entry of entries) {
            const srcPath = path.join(src, entry.name);
            const dstPath = path.join(dst, entry.name);

            if (entry.isDirectory()) {
                if (!fs.existsSync(dstPath)) {
                    await fs.promises.mkdir(dstPath, { recursive: true });
                    summary.foldersCopied.push(entry.name);
                }
                await migrateDirectory(srcPath, dstPath);
            } else {
                if (!fs.existsSync(dstPath)) {
                    await fs.promises.copyFile(srcPath, dstPath);
                    summary.filesCopied.push(entry.name);
                } else {
                    summary.filesSkipped.push(entry.name);
                }
            }
        }
    }

    await migrateDirectory(sourcePath, targetWorkspaceStoragePath);

    // Migrar base de datos SQLite si existe
    const srcDb = path.join(sourcePath, 'state.vscdb');
    const dstDb = path.join(targetWorkspaceStoragePath, 'state.vscdb');

    if (await isSQLiteFile(srcDb) && await isSQLiteFile(dstDb)) {
        await migrateSQLiteChats(srcDb, dstDb, summary);
        await migrateKVTable(srcDb, dstDb, 'cursorDiskKV', summary, ['aiService.', 'composer.', 'anysphere.']);
        await migrateKVTable(srcDb, dstDb, 'itemTable', summary, [
            'aiService.prompts',
            'aiService.generations',
            'scm.history',
            'cursorAuth/workspaceOpenedDate'
        ]);
    }

    return summary;
} 