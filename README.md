# Cursor Workspace Manager

Este plugin para Cursor permite migrar la configuración y el historial de chats entre diferentes workspaces.

## Características

- Migración automática de la configuración del workspace
- Migración del historial de chats de IA
- Migración de configuraciones específicas de Cursor
- Interfaz gráfica para seleccionar el workspace de origen

## Uso

1. Abre el workspace de destino en Cursor
2. Presiona `Ctrl+Shift+P` (o `Cmd+Shift+P` en macOS)
3. Escribe **“Cursor Workspace Manager: Migrar Workspace”** y selecciona el comando
4. Selecciona el workspace de origen de la lista
5. Espera a que se complete la migración

## Requisitos

- Cursor IDE
- Node.js 14 o superior

## Desarrollo

Si deseas compilar o modificar la extensión localmente:

```bash
# Instalar dependencias
npm install

# Compilar TypeScript → JavaScript en la carpeta `out/`
npm run compile

# Iniciar una ventana de desarrollo de extensiones (F5 en VS Code)
# En la nueva ventana abre el proyecto de destino y ejecuta el comando
```

Para generar un archivo `.vsix` listo para distribuir:

```bash
npm install -g @vscode/vsce
vsce package
```

Esto creará `cursor-workspace-manager-x.y.z.vsix` que puedes instalar siguiendo la sección de Instalación.

## Instalación

1. Descarga el archivo .vsix del plugin
2. En Cursor, ve a la pestaña de extensiones
3. Haz clic en los tres puntos (...) y selecciona "Instalar desde VSIX"
4. Selecciona el archivo .vsix descargado

## Notas

- El plugin requiere que Cursor esté cerrado durante la migración
- Se recomienda hacer una copia de seguridad antes de realizar la migración
- La migración puede tardar varios minutos dependiendo del tamaño del workspace

## Problemas conocidos

- La migración puede fallar si hay archivos bloqueados por Cursor
- Algunas configuraciones específicas pueden no migrarse correctamente

## Contribuir

Las contribuciones son bienvenidas. Por favor, abre un issue para reportar problemas o sugerir mejoras. 