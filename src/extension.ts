import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { findWorkspaces, filterPossibleSources } from './utils';
import { migrateWorkspace } from './migrate';
import { WorkspaceState } from './types';

export function activate(context: vscode.ExtensionContext) {
    let disposable = vscode.commands.registerCommand('cursor-workspace-manager.migrateWorkspace', async () => {
        try {
            // Obtener la ruta actual del workspace
            const currentWorkspace = vscode.workspace.workspaceFolders?.[0];
            if (!currentWorkspace) {
                vscode.window.showErrorMessage('No hay un workspace abierto');
                return;
            }

            // Obtener la ruta del workspaceStorage
            const appData = process.env.APPDATA;
            if (!appData) {
                vscode.window.showErrorMessage('No se pudo encontrar la carpeta APPDATA');
                return;
            }

            const storageDir = path.join(appData, 'Cursor', 'User', 'workspaceStorage');
            if (!fs.existsSync(storageDir)) {
                vscode.window.showErrorMessage('No se encontró la carpeta workspaceStorage de Cursor');
                return;
            }

            // Buscar todos los workspaces
            const workspaces = await findWorkspaces(storageDir);
            
            // Filtrar workspaces que parezcan relacionados con el proyecto abierto
            const suggestedWorkspaces = filterPossibleSources(workspaces, currentWorkspace.uri.fsPath);
            const suggestionHashes = new Set(suggestedWorkspaces.map(ws => ws.hash));
            const otherWorkspaces = workspaces.filter(ws => !suggestionHashes.has(ws.hash));

            type WSItem = vscode.QuickPickItem & { workspace?: WorkspaceState };

            const pickItems: WSItem[] = [];

            if (suggestedWorkspaces.length > 0) {
                pickItems.push({
                    label: 'Sugerencias',
                    kind: vscode.QuickPickItemKind.Separator
                });

                pickItems.push(...suggestedWorkspaces.map<WSItem>(ws => ({
                    label: path.basename(ws.path),
                    description: ws.path,
                    detail: `Hash: ${ws.hash}`,
                    workspace: ws
                })));
            }

            if (otherWorkspaces.length > 0) {
                if (pickItems.length > 0) {
                    pickItems.push({
                        label: 'Todos los workspaces',
                        kind: vscode.QuickPickItemKind.Separator
                    });
                }

                pickItems.push(...otherWorkspaces.map<WSItem>(ws => ({
                    label: path.basename(ws.path),
                    description: ws.path,
                    detail: `Hash: ${ws.hash}`,
                    workspace: ws
                })));
            }
            
            const sourceWorkspacePick = await vscode.window.showQuickPick<WSItem>(
                pickItems,
                {
                    placeHolder: 'Selecciona el workspace de origen para migrar'
                }
            );

            const sourceWorkspace = sourceWorkspacePick?.workspace;

            if (!sourceWorkspace) {
                return;
            }

            // Realizar la migración
            const summary = await migrateWorkspace(sourceWorkspace, currentWorkspace.uri.fsPath);
            
            // Mostrar resumen
            vscode.window.showInformationMessage(
                `Migración completada:\n` +
                `Archivos copiados: ${summary.filesCopied.length}\n` +
                `Carpetas copiadas: ${summary.foldersCopied.length}\n` +
                `Chats migrados: ${summary.chatsMigrated}\n` +
                `Claves cursorDiskKV migradas: ${summary.cursorDiskKVMigrated}\n` +
                `Claves itemTable migradas: ${summary.itemTableMigrated}`
            );

        } catch (error) {
            vscode.window.showErrorMessage(`Error durante la migración: ${error}`);
        }
    });

    context.subscriptions.push(disposable);
}

export function deactivate() {} 