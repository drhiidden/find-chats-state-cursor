# Cursor Transcript Organizer

**Idiomas:** [English](../README.md) · Español

![visitas](https://komarev.com/ghpvc/?username=drhiidden&repo=find-chats-state-cursor&label=visitas&color=0e75b6)
<div align="center">

**CLI agnóstico del IDE** (`cursor-org`) — organiza, busca y analiza transcripciones de asistentes de código. Convierte carpetas UUID en nombres legibles con metadatos.

</div>

## Problema

Los IDEs guardan chats en carpetas con UUID ilegibles. Recuperar una conversación antigua implica abrirlas una a una.

## Solución

Renombrado inteligente (fecha, tema, UUID corto), resúmenes Markdown, búsqueda, exportación y modo dry-run por defecto.

## Instalación

```bash
pip install cursor-transcript-organizer
cursor-org --help
```

Desde código:

```bash
git clone https://github.com/drhiidden/find-chats-state-cursor.git
cd find-chats-state-cursor
pip install -e ".[dev]"
```

## Caso de uso (español)

Historia completa con MCP/Blender: [docs/README-CASO-USO-REAL.md](docs/README-CASO-USO-REAL.md)

## Privacidad

Todo es **local**. No se suben transcripciones a la nube. Ver [docs/PRIVACY.md](docs/PRIVACY.md).

## Documentación

| Archivo | Contenido |
|---------|-----------|
| [docs/SEARCH_EXAMPLES.md](docs/SEARCH_EXAMPLES.md) | Ejemplos de búsqueda |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribuir |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Problemas frecuentes |
| [CHANGELOG.md](../CHANGELOG.md) | Cambios por versión |

## Licencia

MIT — ver [LICENSE](LICENSE).
