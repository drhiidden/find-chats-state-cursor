"""Parser registry and factory for multi-IDE support.

Usage:
    from cursor_org.parsers import get_parser, auto_detect_ide
    
    # Auto-detect IDE from path
    ide_name = auto_detect_ide(Path("~/.cursor/projects/abc/agent-transcripts/uuid/uuid.jsonl"))
    parser = get_parser("cursor", file_path)
    metadata = parser.parse()
"""
from pathlib import Path
from typing import Optional, Dict, Type

from .base import BaseTranscriptParser, IDE_CONFIGS, FileStats
from .cursor_parser import CursorParser

# Registry of available parsers
PARSERS: Dict[str, Type[BaseTranscriptParser]] = {
    "cursor": CursorParser,
    # Future parsers:
    # "claude": ClaudeParser,
    # "continue": ContinueParser,
    # "cline": ClineParser,
}


def get_parser(ide: str, file_path: Path) -> BaseTranscriptParser:
    """Get parser instance for specified IDE.
    
    Args:
        ide: IDE name ("cursor", "claude", "continue", etc.)
        file_path: Path to transcript file
        
    Returns:
        BaseTranscriptParser instance
        
    Raises:
        ValueError: If IDE not supported
    """
    parser_class = PARSERS.get(ide.lower())
    if not parser_class:
        supported = ", ".join(PARSERS.keys())
        raise ValueError(
            f"Unsupported IDE: {ide}. Supported IDEs: {supported}"
        )
    
    return parser_class(file_path)


def auto_detect_ide(path: Path) -> Optional[str]:
    """Auto-detect IDE from file path.
    
    Args:
        path: Path to transcript file or folder
        
    Returns:
        str: IDE name if detected, None otherwise
    """
    return BaseTranscriptParser.detect_ide_from_path(path)


def list_supported_ides() -> Dict[str, str]:
    """Get dict of supported IDEs with descriptions.
    
    Returns:
        Dict mapping IDE name to description
    """
    result = {}
    for ide_name, parser_class in PARSERS.items():
        config = IDE_CONFIGS.get(ide_name)
        if config:
            result[ide_name] = config.description
        else:
            result[ide_name] = f"{ide_name} (no description)"
    
    return result


def get_ide_config(ide: str):
    """Get configuration for specified IDE.
    
    Args:
        ide: IDE name
        
    Returns:
        IDEConfig or None if not found
    """
    return IDE_CONFIGS.get(ide.lower())


__all__ = [
    "BaseTranscriptParser",
    "CursorParser",
    "FileStats",
    "get_parser",
    "auto_detect_ide",
    "list_supported_ides",
    "get_ide_config",
    "PARSERS",
    "IDE_CONFIGS",
]
