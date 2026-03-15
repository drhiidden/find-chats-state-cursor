"""Cleanup utilities for removing empty or irrelevant folders."""
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass
from rich.console import Console

console = Console()


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    path: Path
    reason: str
    size_kb: float
    item_count: int
    deleted: bool = False


class TranscriptCleaner:
    """Clean up empty and irrelevant folders from transcript directories.
    
    Identifies:
    - Empty folders (no files at all)
    - MCP folders without actual transcripts
    - agent-tools folders without content
    - Folders with only hidden/system files
    - Temporary/cache folders
    """
    
    # Folders that are commonly empty or irrelevant
    EMPTY_FOLDER_PATTERNS = {
        'mcp',
        'agent-tools',
        '.DS_Store',
        'Thumbs.db',
        '__pycache__',
        '.pytest_cache',
        '.mypy_cache',
        '.ruff_cache',
    }
    
    # Folders that should be kept even if empty (system folders)
    PROTECTED_FOLDERS = {
        'agent-transcripts',
        '.git',
        '.cursor',
        'node_modules',
        '.venv',
        'venv',
        '.cursor-org-backups',
    }
    
    def __init__(self, root_dir: Path, dry_run: bool = True):
        """Initialize cleaner.
        
        Args:
            root_dir: Root directory to clean
            dry_run: If True, only report what would be deleted
        """
        self.root_dir = Path(root_dir)
        self.dry_run = dry_run
        self.results: List[CleanupResult] = []
    
    def is_empty_folder(self, folder: Path) -> bool:
        """Check if folder is empty (no files, only subfolders).
        
        A folder is considered empty if:
        - It has no files
        - All subfolders are also empty
        """
        if not folder.is_dir():
            return False
        
        try:
            items = list(folder.iterdir())
            
            # No items at all
            if not items:
                return True
            
            # Check if all items are directories and all are empty
            for item in items:
                if item.is_file():
                    # Has a file, not empty
                    return False
                elif item.is_dir():
                    # Has a non-empty subdirectory
                    if not self.is_empty_folder(item):
                        return False
            
            # All subdirectories are empty
            return True
        except PermissionError:
            return False
    
    def has_only_hidden_files(self, folder: Path) -> bool:
        """Check if folder only contains hidden/system files."""
        if not folder.is_dir():
            return False
        
        try:
            items = list(folder.rglob("*"))
            files = [item for item in items if item.is_file()]
            
            if not files:
                return False
            
            # Check if all files are hidden or in EMPTY_FOLDER_PATTERNS
            for file in files:
                if not file.name.startswith('.') and file.name not in self.EMPTY_FOLDER_PATTERNS:
                    return False
            
            return True
        except PermissionError:
            return False
    
    def is_irrelevant_folder(self, folder: Path) -> tuple[bool, str]:
        """Check if folder is irrelevant and should be cleaned.
        
        Returns:
            (is_irrelevant, reason)
        """
        name = folder.name.lower()
        
        # Protected folders should never be deleted
        if name in self.PROTECTED_FOLDERS:
            return False, ""
        
        # Check patterns
        if name in self.EMPTY_FOLDER_PATTERNS:
            return True, f"Matches empty pattern: {name}"
        
        # Empty folders
        if self.is_empty_folder(folder):
            return True, "Empty folder (no files)"
        
        # Only hidden files
        if self.has_only_hidden_files(folder):
            return True, "Only contains hidden/system files"
        
        return False, ""
    
    def get_folder_size(self, folder: Path) -> tuple[float, int]:
        """Get folder size in KB and item count.
        
        Returns:
            (size_kb, item_count)
        """
        try:
            total_size = 0
            item_count = 0
            
            for item in folder.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
                    item_count += 1
            
            return total_size / 1024, item_count
        except PermissionError:
            return 0.0, 0
    
    def scan_for_cleanup(self, max_depth: int = 3) -> List[CleanupResult]:
        """Scan directory tree for folders to clean up.
        
        Args:
            max_depth: Maximum depth to scan
            
        Returns:
            List of CleanupResult objects
        """
        results = []
        
        def scan_recursive(current_dir: Path, depth: int):
            if depth > max_depth:
                return
            
            try:
                for item in current_dir.iterdir():
                    if not item.is_dir():
                        continue
                    
                    # Skip protected folders entirely (don't even scan inside them)
                    if item.name.lower() in self.PROTECTED_FOLDERS:
                        continue
                    
                    # Check if irrelevant
                    is_irrelevant, reason = self.is_irrelevant_folder(item)
                    
                    if is_irrelevant:
                        size_kb, item_count = self.get_folder_size(item)
                        results.append(CleanupResult(
                            path=item,
                            reason=reason,
                            size_kb=size_kb,
                            item_count=item_count,
                            deleted=False
                        ))
                    else:
                        # Recurse into relevant folders
                        scan_recursive(item, depth + 1)
            
            except PermissionError:
                pass
        
        scan_recursive(self.root_dir, 0)
        return results
    
    def clean(self, max_depth: int = 3) -> List[CleanupResult]:
        """Perform cleanup operation.
        
        Args:
            max_depth: Maximum depth to scan
            
        Returns:
            List of CleanupResult objects
        """
        results = self.scan_for_cleanup(max_depth)
        
        if not self.dry_run:
            for result in results:
                try:
                    # Delete recursively
                    import shutil
                    shutil.rmtree(result.path)
                    result.deleted = True
                except Exception as e:
                    console.print(f"[red]Error deleting {result.path}: {e}[/red]")
        
        self.results = results
        return results
    
    def display_results(self):
        """Display cleanup results in a nice table."""
        from rich.table import Table
        
        if not self.results:
            console.print("[green]No folders to clean up![/green]")
            return
        
        table = Table(title="Cleanup Results" if self.dry_run else "Cleaned Up Folders")
        table.add_column("Path", style="yellow")
        table.add_column("Reason", style="dim")
        table.add_column("Size", style="cyan", justify="right")
        table.add_column("Items", style="magenta", justify="right")
        
        if not self.dry_run:
            table.add_column("Status", style="green")
        
        total_size = 0
        total_items = 0
        
        for result in self.results:
            rel_path = result.path.relative_to(self.root_dir) if result.path.is_relative_to(self.root_dir) else result.path
            
            row = [
                str(rel_path),
                result.reason,
                f"{result.size_kb:.1f} KB",
                str(result.item_count),
            ]
            
            if not self.dry_run:
                row.append("✓ Deleted" if result.deleted else "✗ Failed")
            
            table.add_row(*row)
            
            if result.deleted or self.dry_run:
                total_size += result.size_kb
                total_items += result.item_count
        
        console.print(table)
        
        # Summary
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Folders: {len(self.results)}")
        console.print(f"  Total size: {total_size:.1f} KB ({total_size/1024:.2f} MB)")
        console.print(f"  Total items: {total_items}")
        
        if self.dry_run:
            console.print(f"\n[yellow]DRY RUN - No changes made[/yellow]")
            console.print(f"[dim]Run with --apply to actually delete these folders[/dim]")
        else:
            deleted_count = sum(1 for r in self.results if r.deleted)
            console.print(f"\n[green]Successfully deleted {deleted_count}/{len(self.results)} folders[/green]")


def clean_all_projects(dry_run: bool = True, max_depth: int = 3, create_backup: bool = True) -> Dict[str, List[CleanupResult]]:
    """Clean all Cursor projects.
    
    Args:
        dry_run: If True, only report what would be deleted
        max_depth: Maximum depth to scan in each project
        create_backup: If True, create backups before deletion
        
    Returns:
        Dictionary mapping project names to their cleanup results
    """
    from .navigation import list_cursor_projects
    from .backup import BackupManager
    
    projects = list_cursor_projects()
    all_results = {}
    
    for proj in projects:
        if proj['transcript_count'] == 0:
            # Skip empty projects
            continue
        
        # Scan for folders to clean
        cleaner_scan = TranscriptCleaner(proj['transcripts_dir'], dry_run=True)
        folders_to_cleanup = cleaner_scan.scan_for_cleanup(max_depth=max_depth)
        
        if not folders_to_cleanup:
            continue
        
        # Create backup if needed
        if create_backup and not dry_run:
            backup_manager = BackupManager(proj['transcripts_dir'])
            backup_id = backup_manager.create_backup(
                items_to_backup=[r.path for r in folders_to_cleanup],
                operation_type='clean'
            )
            
            if backup_id is None:
                console.print(f"[yellow]Warning:[/yellow] Backup failed for {proj['name']}, skipping")
                continue
        
        # Perform cleanup
        cleaner = TranscriptCleaner(proj['transcripts_dir'], dry_run=dry_run)
        results = cleaner.clean(max_depth=max_depth)
        
        if results:
            all_results[proj['name']] = results
    
    return all_results
