import * as fs from 'fs';
import * as path from 'path';
import { WorkspaceState } from './types';

// Devuelve el último segmento (nombre de carpeta) en minúsculas
export function getFolderName(folderPath: string): string {
    return path.basename(folderPath.replace(/\\/g, '/')).toLowerCase();
}

// Filtra workspaces potenciales de origen basándose en la similitud del nombre de carpeta
export function filterPossibleSources(workspaces: WorkspaceState[], targetWorkspacePath: string): WorkspaceState[] {
    const targetName = getFolderName(targetWorkspacePath);

    return workspaces.filter(ws => {
        const wsName = getFolderName(ws.path);
        // Excluir el mismo workspace (misma ruta)
        if (path.resolve(ws.path) === path.resolve(targetWorkspacePath)) {
            return false;
        }
        // Coincidencia exacta o inclusión mutua del nombre
        return wsName === targetName || wsName.includes(targetName) || targetName.includes(wsName);
    });
}

export async function findWorkspaces(storageDir: string): Promise<WorkspaceState[]> {
    const workspaces: WorkspaceState[] = [];
    const entries = await fs.promises.readdir(storageDir);

    for (const entry of entries) {
        const workspacePath = path.join(storageDir, entry);
        const stats = await fs.promises.stat(workspacePath);

        if (stats.isDirectory()) {
            const workspaceJsonPath = path.join(workspacePath, 'workspace.json');
            try {
                const content = await fs.promises.readFile(workspaceJsonPath, 'utf-8');
                const workspaceData = JSON.parse(content);
                if (workspaceData.folder) {
                    workspaces.push({
                        path: workspaceData.folder,
                        hash: entry
                    });
                }
            } catch {
                // silently ignore
            }
        }
    }

    return workspaces;
}

export async function isSQLiteFile(filePath: string): Promise<boolean> {
    try {
        const buffer = Buffer.alloc(16);
        const fd = await fs.promises.open(filePath, 'r');
        await fd.read(buffer, 0, 16, 0);
        await fd.close();
        return buffer.toString().startsWith('SQLite format');
    } catch {
        return false;
    }
} 