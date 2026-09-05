"""Generic transcript organization with pluggable strategies.

Separates the concerns of finding transcripts, organizing them,
and handling different organization strategies.
"""
from pathlib import Path
from typing import Protocol, Optional, List
from dataclasses import dataclass
import logging

from .collector import TranscriptFile, TranscriptCollector, FileFilter
from .parser import TranscriptParser
from .models import TranscriptMetadata
from .renamer import rename_transcript_folder

logger = logging.getLogger(__name__)


@dataclass
class OrganizationResult:
    """Result of organizing a single transcript."""
    original_path: Path
    new_path: Optional[Path]
    success: bool
    error: Optional[str] = None
    metadata: Optional[TranscriptMetadata] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


class OrganizationStrategy(Protocol):
    """Strategy for how to organize transcripts.
    
    This protocol allows different organization behaviors without
    coupling to specific implementations.
    """
    
    def should_process(self, transcript: TranscriptFile) -> tuple[bool, Optional[str]]:
        """Determine if transcript should be processed.
        
        Returns:
            (should_process, skip_reason)
        """
        ...
    
    def organize(
        self,
        transcript: TranscriptFile,
        metadata: TranscriptMetadata,
        dry_run: bool
    ) -> Optional[Path]:
        """Organize the transcript.
        
        Returns:
            New path if successful, None otherwise
        """
        ...


class FolderRenameStrategy:
    """Strategy that renames the parent folder of transcripts.
    
    This is the default strategy used for main transcript folders.
    """
    
    def should_process(self, transcript: TranscriptFile) -> tuple[bool, Optional[str]]:
        """Only process transcripts in UUID-named folders."""
        if not FileFilter.is_uuid_folder(transcript.parent_dir):
            return False, f"Already organized: {transcript.parent_name}"
        return True, None
    
    def organize(
        self,
        transcript: TranscriptFile,
        metadata: TranscriptMetadata,
        dry_run: bool
    ) -> Optional[Path]:
        """Rename the parent folder."""
        try:
            new_path = rename_transcript_folder(
                transcript.parent_dir,
                metadata,
                dry_run=dry_run
            )
            return new_path
        except Exception as e:
            logger.error(f"Error renaming {transcript.parent_dir}: {e}")
            return None


class NestedFileRenameStrategy:
    """Strategy that renames individual transcript files.
    
    Useful for subagents or other nested transcripts where we don't
    want to rename the parent folder.
    """
    
    def should_process(self, transcript: TranscriptFile) -> tuple[bool, Optional[str]]:
        """Process nested files that haven't been organized."""
        # Check if file name is already organized
        name = transcript.path.stem  # filename without extension
        
        # If it's a UUID, needs organizing
        if len(name) == 36 and name.count('-') == 4:
            return True, None
        
        # If it has date prefix, already organized
        if name.startswith('20') and '_' in name:
            return False, f"Already organized: {transcript.name}"
        
        return True, None
    
    def organize(
        self,
        transcript: TranscriptFile,
        metadata: TranscriptMetadata,
        dry_run: bool
    ) -> Optional[Path]:
        """Rename the individual file."""
        try:
            # Generate new filename using same format as folders
            # Truncate topic if needed to avoid MAX_PATH issues
            dirname = metadata.suggested_dirname
            
            # If path would be too long, use shorter format
            new_name = f"{dirname}.jsonl"
            new_path = transcript.path.parent / new_name
            
            # Check path length (Windows MAX_PATH = 260)
            if len(str(new_path.absolute())) > 250:  # Leave some margin
                # Use shorter format: date_time_uuid.jsonl
                short_name = (
                    f"{metadata.start_time.strftime('%Y-%m-%d_%Hh%M')}_"
                    f"{metadata.uuid_short}.jsonl"
                )
                new_path = transcript.path.parent / short_name
                logger.warning(
                    f"Path too long, using short format: {transcript.path.name} -> {short_name}"
                )
            
            if not dry_run:
                transcript.path.rename(new_path)
            
            return new_path
        except Exception as e:
            logger.error(f"Error renaming {transcript.path}: {e}")
            return None


class TranscriptOrganizer:
    """Generic transcript organizer with pluggable strategies.
    
    Coordinates the process of collecting, parsing, and organizing
    transcripts without being coupled to specific folder structures.
    
    Examples:
        # Organize main transcripts (rename folders)
        organizer = TranscriptOrganizer(
            root_dir=path,
            strategy=FolderRenameStrategy()
        )
        results = organizer.organize_all(dry_run=True)
        
        # Organize nested files (rename individual files)
        organizer = TranscriptOrganizer(
            root_dir=path / "subagents",
            strategy=NestedFileRenameStrategy()
        )
        results = organizer.organize_all(dry_run=False)
    """
    
    def __init__(
        self,
        root_dir: Path,
        strategy: OrganizationStrategy,
        ide: Optional[str] = None,
        collector: Optional[TranscriptCollector] = None
    ):
        """Initialize organizer.
        
        Args:
            root_dir: Root directory to organize
            strategy: Organization strategy to use
            ide: IDE type for parsing (auto-detected if None)
            collector: Custom collector (creates default if None)
        """
        self.root_dir = Path(root_dir)
        self.strategy = strategy
        self.ide = ide
        self.collector = collector or TranscriptCollector(root_dir)
    
    def organize_all(
        self,
        dry_run: bool = True,
        max_depth: Optional[int] = None
    ) -> List[OrganizationResult]:
        """Organize all transcripts found by the collector.
        
        Args:
            dry_run: If True, only simulate changes
            max_depth: Maximum depth to traverse
            
        Returns:
            List of organization results
        """
        results = []
        
        # Collect all transcripts
        transcripts = list(self.collector.collect_all(max_depth=max_depth))
        
        for transcript in transcripts:
            result = self._organize_one(transcript, dry_run)
            results.append(result)
        
        return results
    
    def organize_by_filter(
        self,
        folder_filter,
        dry_run: bool = True
    ) -> List[OrganizationResult]:
        """Organize transcripts from folders matching a filter.
        
        Args:
            folder_filter: Function to filter folders
            dry_run: If True, only simulate changes
            
        Returns:
            List of organization results
        """
        results = []
        
        transcripts = list(self.collector.collect_by_filter(folder_filter))
        
        for transcript in transcripts:
            result = self._organize_one(transcript, dry_run)
            results.append(result)
        
        return results
    
    def _organize_one(
        self,
        transcript: TranscriptFile,
        dry_run: bool
    ) -> OrganizationResult:
        """Organize a single transcript."""
        # Check if should process
        should_process, skip_reason = self.strategy.should_process(transcript)
        
        if not should_process:
            return OrganizationResult(
                original_path=transcript.path,
                new_path=None,
                success=True,
                skipped=True,
                skip_reason=skip_reason
            )
        
        # Parse metadata
        try:
            parser = TranscriptParser(transcript.path, ide=self.ide)
            metadata = parser.parse()
        except Exception as e:
            return OrganizationResult(
                original_path=transcript.path,
                new_path=None,
                success=False,
                error=f"Parse error: {e}"
            )
        
        # Organize using strategy
        new_path = self.strategy.organize(transcript, metadata, dry_run)
        
        if new_path:
            return OrganizationResult(
                original_path=transcript.path,
                new_path=new_path,
                success=True,
                metadata=metadata
            )
        else:
            return OrganizationResult(
                original_path=transcript.path,
                new_path=None,
                success=False,
                error="Organization failed"
            )


def organize_recursively(
    root_dir: Path,
    dry_run: bool = True,
    ide: Optional[str] = None,
    organize_nested: bool = True
) -> dict:
    """High-level function to organize transcripts recursively.
    
    This is a convenience function that handles both main transcripts
    and nested transcripts (like subagents) using appropriate strategies.
    
    Args:
        root_dir: Root directory to organize
        dry_run: If True, only simulate changes
        ide: IDE type (auto-detected if None)
        organize_nested: If True, also organize nested transcripts
        
    Returns:
        Dictionary with results for main and nested transcripts
    """
    results = {
        'main': [],
        'nested': [],
        'summary': {
            'total_main': 0,
            'organized_main': 0,
            'total_nested': 0,
            'organized_nested': 0
        }
    }
    
    # Organize main transcripts (folders)
    main_organizer = TranscriptOrganizer(
        root_dir=root_dir,
        strategy=FolderRenameStrategy(),
        ide=ide
    )
    
    main_results = main_organizer.organize_all(dry_run=dry_run, max_depth=1)
    results['main'] = main_results
    results['summary']['total_main'] = len(main_results)
    results['summary']['organized_main'] = sum(
        1 for r in main_results if r.success and not r.skipped
    )
    
    # Organize nested transcripts (individual files)
    if organize_nested:
        collector = TranscriptCollector(root_dir)
        nested_transcripts = [
            t for t in collector.collect_all(max_depth=3)
            if t.is_nested  # Only nested files
        ]
        
        if nested_transcripts:
            nested_organizer = TranscriptOrganizer(
                root_dir=root_dir,
                strategy=NestedFileRenameStrategy(),
                ide=ide,
                collector=collector
            )
            
            nested_results = []
            for transcript in nested_transcripts:
                result = nested_organizer._organize_one(transcript, dry_run)
                nested_results.append(result)
            
            results['nested'] = nested_results
            results['summary']['total_nested'] = len(nested_results)
            results['summary']['organized_nested'] = sum(
                1 for r in nested_results if r.success and not r.skipped
            )
    
    return results
