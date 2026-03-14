"""Generic transcript collection and filtering.

Provides flexible, recursive transcript discovery without coupling
to specific folder structures (e.g., subagents).
"""
from pathlib import Path
from typing import List, Callable, Optional, Iterator
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class TranscriptFile:
    """Represents a discovered transcript file with context."""
    path: Path
    parent_dir: Path
    relative_path: Path
    depth: int
    is_nested: bool = False
    
    @property
    def name(self) -> str:
        return self.path.name
    
    @property
    def parent_name(self) -> str:
        return self.parent_dir.name


class FileFilter:
    """Strategy pattern for filtering files during collection."""
    
    @staticmethod
    def is_jsonl(path: Path) -> bool:
        """Check if file is a JSONL transcript."""
        return path.suffix.lower() == '.jsonl'
    
    @staticmethod
    def is_uuid_folder(path: Path) -> bool:
        """Check if folder name looks like a UUID."""
        if not path.is_dir():
            return False
        name = path.name
        # UUID format: 8-4-4-4-12 characters with dashes
        return len(name) == 36 and name.count('-') == 4
    
    @staticmethod
    def is_organized_folder(path: Path) -> bool:
        """Check if folder appears to be already organized."""
        if not path.is_dir():
            return False
        name = path.name
        # Organized format: YYYY-MM-DD_HHhMM_topic_uuid
        # Has dashes but NOT in UUID format
        return '-' in name and not FileFilter.is_uuid_folder(path)
    
    @staticmethod
    def should_skip_folder(path: Path) -> bool:
        """Check if folder should be skipped during traversal."""
        skip_names = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}
        return path.name in skip_names or path.name.startswith('.')


class TranscriptCollector:
    """Flexible, recursive transcript file collector.
    
    Discovers transcript files based on configurable criteria without
    being coupled to specific folder structures.
    
    Examples:
        # Collect all JSONL files recursively
        collector = TranscriptCollector(root_dir)
        transcripts = list(collector.collect_all())
        
        # Collect only from UUID folders
        transcripts = list(collector.collect_by_filter(
            folder_filter=FileFilter.is_uuid_folder
        ))
        
        # Collect with custom depth limit
        transcripts = list(collector.collect_all(max_depth=2))
    """
    
    def __init__(
        self,
        root_dir: Path,
        file_filter: Callable[[Path], bool] = FileFilter.is_jsonl,
        skip_filter: Callable[[Path], bool] = FileFilter.should_skip_folder
    ):
        """Initialize collector.
        
        Args:
            root_dir: Root directory to start collection
            file_filter: Function to determine if file should be collected
            skip_filter: Function to determine if folder should be skipped
        """
        self.root_dir = Path(root_dir)
        self.file_filter = file_filter
        self.skip_filter = skip_filter
    
    def collect_all(
        self,
        max_depth: Optional[int] = None,
        include_nested: bool = True
    ) -> Iterator[TranscriptFile]:
        """Collect all matching files recursively.
        
        Args:
            max_depth: Maximum depth to traverse (None = unlimited)
            include_nested: Include files in nested folders
            
        Yields:
            TranscriptFile objects for each matching file
        """
        yield from self._collect_recursive(
            self.root_dir,
            depth=0,
            max_depth=max_depth,
            include_nested=include_nested
        )
    
    def collect_by_filter(
        self,
        folder_filter: Callable[[Path], bool],
        max_depth: Optional[int] = None
    ) -> Iterator[TranscriptFile]:
        """Collect files only from folders matching a filter.
        
        Args:
            folder_filter: Function to determine if folder should be processed
            max_depth: Maximum depth to traverse
            
        Yields:
            TranscriptFile objects from matching folders
        """
        for folder in self._find_folders(self.root_dir, folder_filter, max_depth):
            for file in folder.iterdir():
                if file.is_file() and self.file_filter(file):
                    depth = len(file.relative_to(self.root_dir).parts) - 1
                    # A file is nested if it's more than 1 level deep
                    is_nested = depth > 1
                    
                    yield TranscriptFile(
                        path=file,
                        parent_dir=folder,
                        relative_path=file.relative_to(self.root_dir),
                        depth=depth,
                        is_nested=is_nested
                    )
    
    def collect_from_uuid_folders(self) -> Iterator[TranscriptFile]:
        """Collect transcripts only from UUID-named folders.
        
        This is a convenience method for the common case of finding
        unorganized transcripts.
        
        Yields:
            TranscriptFile objects from UUID folders
        """
        yield from self.collect_by_filter(
            folder_filter=FileFilter.is_uuid_folder
        )
    
    def _collect_recursive(
        self,
        current_dir: Path,
        depth: int,
        max_depth: Optional[int],
        include_nested: bool
    ) -> Iterator[TranscriptFile]:
        """Internal recursive collection implementation."""
        if max_depth is not None and depth > max_depth:
            return
        
        if not current_dir.is_dir():
            return
        
        try:
            for item in current_dir.iterdir():
                # Skip filtered folders
                if item.is_dir() and self.skip_filter(item):
                    continue
                
                # Collect matching files
                if item.is_file() and self.file_filter(item):
                    # A file is nested if its parent is not the root directory
                    # AND it's more than 1 level deep
                    is_nested = depth > 1
                    
                    # Skip nested files if not included
                    if not include_nested and is_nested:
                        continue
                    
                    yield TranscriptFile(
                        path=item,
                        parent_dir=item.parent,
                        relative_path=item.relative_to(self.root_dir),
                        depth=depth,
                        is_nested=is_nested
                    )
                
                # Recurse into subdirectories
                elif item.is_dir():
                    yield from self._collect_recursive(
                        item,
                        depth + 1,
                        max_depth,
                        include_nested
                    )
        
        except PermissionError as e:
            logger.warning(f"Permission denied accessing {current_dir}: {e}")
    
    def _find_folders(
        self,
        start_dir: Path,
        folder_filter: Callable[[Path], bool],
        max_depth: Optional[int]
    ) -> Iterator[Path]:
        """Find folders matching a filter."""
        yield from self._find_folders_recursive(
            start_dir,
            folder_filter,
            depth=0,
            max_depth=max_depth
        )
    
    def _find_folders_recursive(
        self,
        current_dir: Path,
        folder_filter: Callable[[Path], bool],
        depth: int,
        max_depth: Optional[int]
    ) -> Iterator[Path]:
        """Internal recursive folder finding."""
        if max_depth is not None and depth > max_depth:
            return
        
        if not current_dir.is_dir():
            return
        
        try:
            for item in current_dir.iterdir():
                if not item.is_dir():
                    continue
                
                if self.skip_filter(item):
                    continue
                
                # Yield if matches filter
                if folder_filter(item):
                    yield item
                
                # Recurse
                yield from self._find_folders_recursive(
                    item,
                    folder_filter,
                    depth + 1,
                    max_depth
                )
        
        except PermissionError as e:
            logger.warning(f"Permission denied accessing {current_dir}: {e}")


class TranscriptGroup:
    """Groups related transcripts (e.g., parent + subagents)."""
    
    def __init__(self, parent: TranscriptFile):
        self.parent = parent
        self.children: List[TranscriptFile] = []
    
    def add_child(self, child: TranscriptFile):
        """Add a child/nested transcript."""
        self.children.append(child)
    
    @property
    def all_transcripts(self) -> List[TranscriptFile]:
        """Get all transcripts (parent + children)."""
        return [self.parent] + self.children
    
    def __repr__(self):
        return f"TranscriptGroup(parent={self.parent.name}, children={len(self.children)})"


def group_transcripts_by_parent(
    transcripts: List[TranscriptFile]
) -> List[TranscriptGroup]:
    """Group transcripts by their parent directory.
    
    This allows processing related transcripts together (e.g., a main
    chat and its subagents) without coupling to specific folder names.
    
    Args:
        transcripts: List of discovered transcripts
        
    Returns:
        List of TranscriptGroup objects
    """
    groups = {}
    
    for transcript in transcripts:
        # Use the immediate parent directory as grouping key
        parent_key = transcript.parent_dir
        
        if parent_key not in groups:
            # First transcript in this directory becomes the parent
            groups[parent_key] = TranscriptGroup(transcript)
        else:
            # Additional transcripts are children
            groups[parent_key].add_child(transcript)
    
    return list(groups.values())
