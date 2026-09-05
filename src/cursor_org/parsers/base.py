"""Base parser interface for IDE-agnostic transcript parsing.

All IDE-specific parsers should inherit from BaseTranscriptParser.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..models import TranscriptMetadata
from ..constants import (
    IDE_DEFAULT_PATHS, IDE_DESCRIPTIONS, IDE_PATH_PATTERNS
)


@dataclass(frozen=True, slots=True)
class FileStats:
    """Filesystem statistics for a transcript file.
    
    Attributes:
        created: File creation timestamp
        modified: File modification timestamp
    """
    created: datetime
    modified: datetime


class IDEConfig:
    """Configuration for a specific IDE's transcript format."""
    
    def __init__(
        self,
        name: str,
        default_paths: List[str],
        format: str = "jsonl",
        description: str = "",
    ):
        self.name = name
        self.default_paths = default_paths
        self.format = format
        self.description = description


# IDE configurations (loaded from constants)
IDE_CONFIGS = {
    ide_name: IDEConfig(
        name=ide_name.title(),
        default_paths=IDE_DEFAULT_PATHS[ide_name],
        format="jsonl",
        description=IDE_DESCRIPTIONS[ide_name],
    )
    for ide_name in IDE_DEFAULT_PATHS.keys()
}


class BaseTranscriptParser(ABC):
    """Abstract base class for transcript parsers.
    
    Each IDE-specific parser should:
    1. Inherit from this class
    2. Implement parse() method
    3. Register in PARSERS dict in __init__.py
    """
    
    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Transcript file not found: {self.file_path}")
    
    @abstractmethod
    def parse(self) -> TranscriptMetadata:
        """Parse the transcript file and return AITS-compliant metadata.
        
        Returns:
            TranscriptMetadata: Parsed metadata with AITS v1.0 fields
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_ide_name(cls) -> str:
        """Return the IDE name this parser supports.
        
        Returns:
            str: IDE name (e.g., "cursor", "claude", "continue")
        """
        pass
    
    @classmethod
    def get_default_paths(cls) -> List[Path]:
        """Return default transcript storage paths for this IDE.
        
        Returns:
            List[Path]: List of possible transcript locations
        """
        ide_name = cls.get_ide_name()
        config = IDE_CONFIGS.get(ide_name)
        if not config:
            return []
        
        paths = []
        for path_str in config.default_paths:
            # Expand ~ and environment variables
            expanded = Path(path_str).expanduser()
            # Handle wildcards like {project}
            if "{project}" in str(expanded):
                # Return parent directory for scanning
                parent = Path(str(expanded).split("{project}")[0])
                if parent.exists():
                    paths.append(parent)
            else:
                if expanded.exists():
                    paths.append(expanded)
        
        return paths
    
    @classmethod
    def detect_ide_from_path(cls, path: Path) -> Optional[str]:
        """Auto-detect IDE type from file path.
        
        Args:
            path: Path to transcript file or folder
            
        Returns:
            str: IDE name if detected, None otherwise
        """
        path_str = str(path).lower()
        
        # Check against configured patterns
        for ide_name, patterns in IDE_PATH_PATTERNS.items():
            if any(pattern in path_str for pattern in patterns):
                return ide_name
        
        return None
    
    def _get_fs_stats(self) -> FileStats:
        """Get filesystem timestamps (creation, modification).
        
        Returns:
            FileStats object with creation and modification timestamps
        """
        from datetime import timezone
        stat = self.file_path.stat()
        return FileStats(
            created=datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        )
