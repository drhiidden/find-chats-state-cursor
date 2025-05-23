#!/usr/bin/env python3
"""
Script para migrar los estados (incluyendo historial de chats de IA)
de un proyecto en Cursor que ha sido renombrado o movido de carpeta.
Copia el directorio de estado correspondiente al hash antiguo al nuevo.
Ahora busca el estado correcto leyendo todos los workspace.json y comparando la ruta real.
"""

import os
import hashlib
import shutil
import sys
import json
import urllib.parse
import subprocess
import sqlite3

def cursor_abierto():
    """
    Detecta si Cursor IDE está abierto (Windows, macOS, Linux).
    """
    try:
        if os.name == 'nt':
            tasks = subprocess.check_output(['tasklist'], encoding='utf-8').lower()
            return 'cursor.exe' in tasks
        else:
            # macOS/Linux: buscar procesos con 'cursor' en el nombre
            ps = subprocess.check_output(['ps', 'aux'], encoding='utf-8').lower()
            return 'cursor' in ps
    except Exception:
        return False

def uri_a_ruta_local(uri):
    """
    Convierte una URI tipo file:///c%3A/Users/... a una ruta local de Windows.
    """
    if uri.startswith("file:///"):
        path = uri[8:]  # quitar 'file:///'
        path = urllib.parse.unquote(path)
        if os.name == 'nt':
            # Windows: primera letra es la unidad
            if path[1:3] == ':/':
                path = path[0].upper() + path[1:]
            path = path.replace('/', '\\')
        else:
            path = '/' + path
        return path
    return uri

def ruta_a_hash(ruta):
    """
    Convierte una ruta de carpeta en el hash MD5 que usa Cursor/VSCode.
    """
    uri = "file:///" + ruta.replace("\\", "/").lower()
    return hashlib.md5(uri.encode('utf-8')).hexdigest()

def es_sqlite(path):
    try:
        with open(path, 'rb') as f:
            header = f.read(16)
        return header.startswith(b'SQLite format')
    except Exception:
        return False

def migrar_chats_sqlite(src_db, dst_db, resumen):
    try:
        with sqlite3.connect(src_db) as src_conn, sqlite3.connect(dst_db) as dst_conn:
            src_cursor = src_conn.cursor()
            dst_cursor = dst_conn.cursor()
            
            # Activar foreign keys y modo WAL para mejor rendimiento
            dst_cursor.execute("PRAGMA foreign_keys = ON")
            dst_cursor.execute("PRAGMA journal_mode = WAL")
            
            # Buscar tablas relacionadas con chat
            src_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tablas = [row[0] for row in src_cursor.fetchall()]
            print(f"[SQLite] Tablas encontradas en {src_db}: {tablas}")
            
            chat_tablas = [t for t in tablas if 'chat' in t.lower() or 'message' in t.lower()]
            print(f"[SQLite] Tablas candidatas para migrar chats: {chat_tablas}")
            
            if not chat_tablas:
                print(f"ℹ️  No se encontraron tablas de chat en {src_db}.")
                return
                
            for tabla in chat_tablas:
                try:
                    # Verificar si la tabla existe en el destino
                    dst_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,))
                    if not dst_cursor.fetchone():
                        print(f"⚠️  La tabla {tabla} no existe en la base de datos de destino. Creándola...")
                        # Obtener la estructura de la tabla del origen
                        src_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tabla,))
                        create_table_sql = src_cursor.fetchone()[0]
                        dst_cursor.execute(create_table_sql)
                    
                    # Obtener columnas y sus tipos
                    src_cursor.execute(f"PRAGMA table_info({tabla})")
                    columnas_origen = {row[1]: row[2] for row in src_cursor.fetchall()}
                    
                    dst_cursor.execute(f"PRAGMA table_info({tabla})")
                    columnas_destino = {row[1]: row[2] for row in dst_cursor.fetchall()}
                    
                    # Verificar que las estructuras coincidan
                    if columnas_origen != columnas_destino:
                        print(f"⚠️  La estructura de la tabla {tabla} no coincide entre origen y destino")
                        continue
                    
                    # Extraer todos los registros
                    src_cursor.execute(f"SELECT * FROM {tabla}")
                    registros = src_cursor.fetchall()
                    print(f"[SQLite] Tabla '{tabla}' registros encontrados: {len(registros)}")
                    
                    if not registros:
                        continue
                    
                    # Insertar solo los que no existan en el destino (por id si existe)
                    if 'id' in columnas_origen:
                        ids = [r[list(columnas_origen.keys()).index('id')] for r in registros]
                        placeholders = ','.join('?' for _ in ids)
                        dst_cursor.execute(f"SELECT id FROM {tabla} WHERE id IN ({placeholders})", ids)
                        existentes = set(row[0] for row in dst_cursor.fetchall())
                        nuevos = [r for r in registros if r[list(columnas_origen.keys()).index('id')] not in existentes]
                        print(f"[SQLite] Tabla '{tabla}' registros nuevos a migrar: {len(nuevos)}")
                    else:
                        nuevos = registros
                        print(f"[SQLite] Tabla '{tabla}' no tiene columna 'id', migrando todos los registros.")
                    
                    if nuevos:
                        # Construir la consulta de inserción
                        columnas = list(columnas_origen.keys())
                        placeholders = ','.join(['?' for _ in columnas])
                        q = f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES ({placeholders})"
                        
                        # Insertar en lotes para mejor rendimiento
                        lote_size = 100
                        for i in range(0, len(nuevos), lote_size):
                            lote = nuevos[i:i + lote_size]
                            dst_cursor.executemany(q, lote)
                            dst_conn.commit()  # Commit después de cada lote
                        
                        resumen['chats_migrados'] += len(nuevos)
                        print(f"[SQLite] Tabla '{tabla}' registros migrados: {len(nuevos)}")
                    else:
                        print(f"[SQLite] Tabla '{tabla}' no hay registros nuevos para migrar.")
                        
                except Exception as e:
                    print(f"❌ Error procesando tabla {tabla}: {e}")
                    continue
            
            # Commit final
            dst_conn.commit()
            print(f"✅ Migrados {resumen['chats_migrados']} registros de chat de {src_db} a {dst_db}.")
            
    except Exception as e:
        print(f"❌ Error migrando chats de SQLite: {e}")
        raise  # Re-lanzar la excepción para que el código superior pueda manejarla

def migrar_tabla_kv(src_db, dst_db, nombre_tabla, resumen, claves_interes=None):
    """
    Función genérica para migrar claves y valores de una tabla KV.
    Si la clave existe y el valor es diferente, sobrescribe el valor en el destino.
    Solo muestra en el log las claves nuevas o sobrescritas.
    """
    try:
        with sqlite3.connect(src_db) as src_conn, sqlite3.connect(dst_db) as dst_conn:
            src_cursor = src_conn.cursor()
            dst_cursor = dst_conn.cursor()
            # Leer todas las claves del origen
            src_cursor.execute(f"SELECT key, value FROM {nombre_tabla}")
            src_kv = src_cursor.fetchall()
            # Leer todas las claves y valores del destino
            dst_cursor.execute(f"SELECT key, value FROM {nombre_tabla}")
            dst_kv = dict(dst_cursor.fetchall())
            migradas = 0
            sobrescritas = 0
            for k, v in src_kv:
                if k in claves_interes:
                    if k not in dst_kv:
                        dst_cursor.execute(f"INSERT INTO {nombre_tabla} (key, value) VALUES (?, ?)", (k, v))
                        migradas += 1
                        print(f"[{nombre_tabla}] Migrada clave nueva: {k}")
                    else:
                        if dst_kv[k] != v:
                            dst_cursor.execute(f"UPDATE {nombre_tabla} SET value = ? WHERE key = ?", (v, k))
                            sobrescritas += 1
                            print(f"[{nombre_tabla}] Clave sobrescrita (valor diferente): {k}")
            dst_conn.commit()
            resumen[f'claves_{nombre_tabla.lower()}_migradas'] = migradas
            resumen[f'claves_{nombre_tabla.lower()}_sobrescritas'] = sobrescritas
            print(f"✅ Migradas {migradas} claves nuevas y sobrescritas {sobrescritas} claves de {nombre_tabla} de {src_db} a {dst_db}.")
    except Exception as e:
        print(f"❌ Error migrando claves de {nombre_tabla}: {e}")

def migrar_cursorDiskKV(src_db, dst_db, resumen, claves_interes=None):
    if claves_interes is None:
        claves_interes = ['aiService.', 'composer.', 'anysphere.']
    migrar_tabla_kv(src_db, dst_db, 'cursorDiskKV', resumen, claves_interes)

def migrar_itemTable(src_db, dst_db, resumen, claves_interes=None):
    if claves_interes is None:
        claves_interes = [
            'aiService.prompts',
            'aiService.generations',
            'scm.history',
            'cursorAuth/workspaceOpenedDate'
        ]
    migrar_tabla_kv(src_db, dst_db, 'itemTable', resumen, claves_interes)

def fusionar_estados(origen, destino, resumen):
    for item in os.listdir(origen):
        src_item = os.path.join(origen, item)
        dst_item = os.path.join(destino, item)
        if os.path.isdir(src_item):
            if not os.path.exists(dst_item):
                shutil.copytree(src_item, dst_item)
                resumen['carpetas_copiadas'].append(item)
            else:
                fusionar_estados(src_item, dst_item, resumen)
        else:
            if not os.path.exists(dst_item):
                shutil.copy2(src_item, dst_item)
                resumen['archivos_copiados'].append(item)
            else:
                resumen['archivos_omitidos'].append(item)
    # Migrar chats si ambos tienen state.vscdb y son SQLite
    src_db = os.path.join(origen, 'state.vscdb')
    dst_db = os.path.join(destino, 'state.vscdb')
    if os.path.isfile(src_db) and os.path.isfile(dst_db):
        if es_sqlite(src_db) and es_sqlite(dst_db):
            migrar_chats_sqlite(src_db, dst_db, resumen)
            migrar_cursorDiskKV(src_db, dst_db, resumen)
            migrar_itemTable(src_db, dst_db, resumen)

def main():
    if cursor_abierto():
        print("❌ Cursor IDE está abierto. Por favor, ciérralo antes de ejecutar este script.")
        sys.exit(1)
    if len(sys.argv) != 3:
        print("Uso: python main.py <ruta_antigua> <ruta_nueva>")
        sys.exit(1)

    old_path = os.path.abspath(sys.argv[1])
    new_path = os.path.abspath(sys.argv[2])

    # Localizar workspaceStorage
    appdata = os.getenv('APPDATA')
    if not appdata:
        print("No se encontró APPDATA.")
        sys.exit(1)
    storage_dir = os.path.join(appdata, "Cursor", "User", "workspaceStorage")

    # Buscar todos los estados antiguos y nuevos
    print("Buscando los estados correspondientes a las rutas proporcionadas...")
    old_states = []
    new_states = []
    for carpeta in os.listdir(storage_dir):
        carpeta_path = os.path.join(storage_dir, carpeta)
        if not os.path.isdir(carpeta_path):
            continue
        ws_json = os.path.join(carpeta_path, "workspace.json")
        if not os.path.isfile(ws_json):
            continue
        try:
            with open(ws_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            folder_uri = data.get('folder')
            if not folder_uri:
                continue
            ruta_real = os.path.abspath(uri_a_ruta_local(folder_uri))
            if os.path.normcase(ruta_real) == os.path.normcase(old_path):
                old_states.append(carpeta_path)
            if os.path.normcase(ruta_real) == os.path.normcase(new_path):
                new_states.append(carpeta_path)
        except Exception as e:
            print(f"⚠️  Error leyendo {ws_json}: {e}")
            continue
    if not old_states:
        print("No se encontró ningún estado que corresponda a la ruta antigua proporcionada.")
        sys.exit(1)
    if not new_states:
        print("No se encontró ningún estado para la ruta nueva. Abre el proyecto en Cursor y vuelve a ejecutar el script.")
        sys.exit(1)

    print(f"Se encontraron {len(old_states)} estado(s) antiguo(s) y {len(new_states)} estado(s) nuevo(s).")
    resumen_global = {
        'archivos_copiados': [],
        'archivos_omitidos': [],
        'carpetas_copiadas': [],
        'chats_migrados': 0,
        'claves_cursordiskkv_migradas': 0,
        'claves_cursordiskkv_sobrescritas': 0,
        'claves_itemtable_migradas': 0,
        'claves_itemtable_sobrescritas': 0
    }
    for old_state in old_states:
        for new_state in new_states:
            print(f"\nFusionando estado de\n  {old_state}\nen\n  {new_state}\n")
            resumen = {
                'archivos_copiados': [],
                'archivos_omitidos': [],
                'carpetas_copiadas': [],
                'chats_migrados': 0,
                'claves_cursordiskkv_migradas': 0,
                'claves_cursordiskkv_sobrescritas': 0,
                'claves_itemtable_migradas': 0,
                'claves_itemtable_sobrescritas': 0
            }
            fusionar_estados(old_state, new_state, resumen)
            # Acumular en el resumen global
            resumen_global['archivos_copiados'] += resumen['archivos_copiados']
            resumen_global['archivos_omitidos'] += resumen['archivos_omitidos']
            resumen_global['carpetas_copiadas'] += resumen['carpetas_copiadas']
            resumen_global['chats_migrados'] += resumen['chats_migrados']
            resumen_global['claves_cursordiskkv_migradas'] += resumen['claves_cursordiskkv_migradas']
            resumen_global['claves_cursordiskkv_sobrescritas'] += resumen['claves_cursordiskkv_sobrescritas']
            resumen_global['claves_itemtable_migradas'] += resumen['claves_itemtable_migradas']
            resumen_global['claves_itemtable_sobrescritas'] += resumen['claves_itemtable_sobrescritas']

    print("\nResumen global de la fusión:")
    print(f"Archivos copiados: {resumen_global['archivos_copiados']}")
    print(f"Carpetas copiadas: {resumen_global['carpetas_copiadas']}")
    print(f"Archivos omitidos (ya existían): {resumen_global['archivos_omitidos']}")
    print(f"Chats migrados (SQLite): {resumen_global['chats_migrados']}")
    print(f"Claves cursorDiskKV migradas: {resumen_global['claves_cursordiskkv_migradas']}")
    print(f"Claves cursorDiskKV sobrescritas: {resumen_global['claves_cursordiskkv_sobrescritas']}")
    print(f"Claves itemTable migradas: {resumen_global['claves_itemtable_migradas']}")
    print(f"Claves itemTable sobrescritas: {resumen_global['claves_itemtable_sobrescritas']}")
    print("\n¡Listo! Ahora puedes abrir el proyecto con el nuevo nombre y deberías ver los chats y configuraciones migradas si existían.")

if __name__ == "__main__":
    main()
