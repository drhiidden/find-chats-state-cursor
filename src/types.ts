export interface WorkspaceState {
    path: string;
    hash: string;
}

export interface MigrationSummary {
    filesCopied: string[];
    filesSkipped: string[];
    foldersCopied: string[];
    chatsMigrated: number;
    cursorDiskKVMigrated: number;
    cursorDiskKVOverwritten: number;
    itemTableMigrated: number;
    itemTableOverwritten: number;
}

export interface SQLiteTable {
    name: string;
    sql?: string;
}

export interface SQLiteRow {
    [key: string]: any;
}

export interface KVRow {
    key: string;
    value: string;
} 