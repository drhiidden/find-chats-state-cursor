"""Backup and restore functionality for cursor-org operations.

Provides automatic backup before destructive operations (clean, organize)
and restore capabilities to undo changes.
"""
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import shutil
import tempfile
import logging
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class BackupMetadata:
    """Metadata for a backup operation."""
    backup_id: str
    timestamp: datetime
    operation_type: str
    source_path: Path
    item_count: int
    total_size_kb: float
    items: List[Dict[str, str]]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'backup_id': self.backup_id,
            'timestamp': self.timestamp.isoformat(),
            'operation_type': self.operation_type,
            'source_path': str(self.source_path),
            'item_count': self.item_count,
            'total_size_kb': self.total_size_kb,
            'items': self.items
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BackupMetadata':
        """Create from dictionary."""
        return cls(
            backup_id=data['backup_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            operation_type=data['operation_type'],
            source_path=Path(data['source_path']),
            item_count=data['item_count'],
            total_size_kb=data['total_size_kb'],
            items=data['items']
        )


@dataclass
class RestoreResult:
    """Result of a restore operation."""
    success: bool
    restored_count: int
    failed_count: int
    errors: List[str]


class BackupManager:
    """Manages backups for cursor-org operations.
    
    Creates timestamped backups before destructive operations and provides
    restore capabilities for undo functionality.
    
    Backup Structure:
        .cursor-org-backups/
            YYYY-MM-DD_HHhMMhSS_operation/
                backup.json          # Metadata
                data/                # Backed up files/folders
                    ...
    
    Examples:
        # Create backup before operation
        manager = BackupManager(target_dir)
        backup_id = manager.create_backup(
            items_to_backup=[folder1, folder2],
            operation_type='clean'
        )
        
        # List available backups
        backups = manager.list_backups()
        
        # Restore a backup
        result = manager.restore_backup(backup_id)
    """
    
    BACKUP_DIR_NAME = '.cursor-org-backups'
    METADATA_FILE = 'backup.json'
    DATA_DIR = 'data'
    
    def __init__(self, work_dir: Path, max_backups: int = 10):
        """Initialize backup manager.
        
        Args:
            work_dir: Working directory where backups will be stored
            max_backups: Maximum number of backups to keep (older ones deleted)
        """
        self.work_dir = Path(work_dir)
        self.backup_root = self.work_dir / self.BACKUP_DIR_NAME
        self.max_backups = max_backups
    
    def _generate_backup_id(self, operation_type: str) -> str:
        """Generate unique backup ID with timestamp."""
        timestamp = datetime.now().strftime('%Y-%m-%d_%Hh%Mh%S-%f')[:24]
        return f"{timestamp}_{operation_type}"
    
    def _get_backup_dir(self, backup_id: str) -> Path:
        """Get backup directory path."""
        return self.backup_root / backup_id
    
    def _get_data_dir(self, backup_id: str) -> Path:
        """Get backup data directory path."""
        return self._get_backup_dir(backup_id) / self.DATA_DIR
    
    def _get_metadata_path(self, backup_id: str) -> Path:
        """Get metadata file path."""
        return self._get_backup_dir(backup_id) / self.METADATA_FILE
    
    def _calculate_size(self, path: Path) -> float:
        """Calculate size in KB for a file or directory."""
        if not path.exists():
            return 0.0
        
        if path.is_file():
            return path.stat().st_size / 1024
        
        total_size = 0
        try:
            for item in path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
        except PermissionError:
            logger.warning(f"Permission denied calculating size: {path}")
        
        return total_size / 1024
    
    def _check_disk_space(self, required_kb: float) -> bool:
        """Check if enough disk space is available.
        
        Args:
            required_kb: Required space in KB
            
        Returns:
            True if enough space available
        """
        try:
            import shutil as sh
            usage = sh.disk_usage(self.work_dir)
            available_kb = usage.free / 1024
            
            # Require 1.5x space (safety margin)
            return available_kb > (required_kb * 1.5)
        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")
            return True
    
    def _copy_item(self, src: Path, dst: Path) -> None:
        """Copy a file or directory preserving metadata.
        
        Args:
            src: Source path
            dst: Destination path
        """
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        elif src.is_dir():
            # Check if directory has content
            has_content = any(src.iterdir())
            
            if has_content:
                # Use copytree for directories with content
                shutil.copytree(
                    src, dst,
                    symlinks=False,
                    copy_function=shutil.copy2,
                    dirs_exist_ok=True
                )
            else:
                # Just create empty directory for empty folders
                dst.mkdir(parents=True, exist_ok=True)
    
    def create_backup(
        self,
        items_to_backup: List[Path],
        operation_type: str
    ) -> Optional[str]:
        """Create a backup of specified items.
        
        Args:
            items_to_backup: List of files/folders to backup
            operation_type: Type of operation ('clean', 'organize', etc.)
            
        Returns:
            Backup ID if successful, None otherwise
        """
        if not items_to_backup:
            logger.info("No items to backup")
            return None
        
        # Generate backup ID
        backup_id = self._generate_backup_id(operation_type)
        backup_dir = self._get_backup_dir(backup_id)
        data_dir = self._get_data_dir(backup_id)
        
        try:
            # Calculate total size
            console.print(f"[dim]Calculating backup size...[/dim]")
            total_size_kb = sum(self._calculate_size(item) for item in items_to_backup)
            
            # Check disk space
            if not self._check_disk_space(total_size_kb):
                console.print(
                    f"[red]Error:[/red] Insufficient disk space for backup "
                    f"(required: {total_size_kb:.1f} KB / {total_size_kb/1024:.2f} MB)"
                )
                return None
            
            # Create backup directories
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy items
            console.print(f"[dim]Creating backup: {backup_id}[/dim]")
            items_metadata = []
            
            for item in items_to_backup:
                if not item.exists():
                    logger.warning(f"Item does not exist, skipping: {item}")
                    continue
                
                try:
                    # Determine relative path from work_dir
                    try:
                        rel_path = item.relative_to(self.work_dir)
                    except ValueError:
                        rel_path = Path(item.name)
                    
                    dst_path = data_dir / rel_path
                    
                    # Copy with metadata preservation
                    self._copy_item(item, dst_path)
                    
                    items_metadata.append({
                        'original_path': str(item),
                        'relative_path': str(rel_path),
                        'item_type': 'dir' if item.is_dir() else 'file',
                        'size_kb': self._calculate_size(item)
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to backup {item}: {e}")
                    raise
            
            # Create metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                timestamp=datetime.now(),
                operation_type=operation_type,
                source_path=self.work_dir,
                item_count=len(items_metadata),
                total_size_kb=total_size_kb,
                items=items_metadata
            )
            
            # Save metadata
            metadata_path = self._get_metadata_path(backup_id)
            with metadata_path.open('w', encoding='utf-8') as f:
                json.dump(metadata.to_dict(), f, indent=2)
            
            console.print(
                f"[green]OK[/green] Backup created successfully: "
                f"{backup_id} ({total_size_kb:.1f} KB, {len(items_metadata)} items)"
            )
            
            # Cleanup old backups
            self.cleanup_old_backups()
            
            return backup_id
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            console.print(f"[red]Error creating backup:[/red] {e}")
            
            # Cleanup failed backup
            if backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)
            
            return None
    
    def list_backups(self) -> List[BackupMetadata]:
        """List all available backups.
        
        Returns:
            List of BackupMetadata sorted by timestamp (newest first)
        """
        if not self.backup_root.exists():
            return []
        
        backups = []
        
        for backup_dir in self.backup_root.iterdir():
            if not backup_dir.is_dir():
                continue
            
            metadata_path = backup_dir / self.METADATA_FILE
            if not metadata_path.exists():
                continue
            
            try:
                with metadata_path.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    metadata = BackupMetadata.from_dict(data)
                    backups.append(metadata)
            except Exception as e:
                logger.warning(f"Could not load backup metadata from {backup_dir}: {e}")
        
        # Sort by timestamp, newest first
        backups.sort(key=lambda b: b.timestamp, reverse=True)
        
        return backups
    
    def get_backup(self, backup_id: str) -> Optional[BackupMetadata]:
        """Get metadata for a specific backup.
        
        Args:
            backup_id: Backup ID or index (1-based)
            
        Returns:
            BackupMetadata if found, None otherwise
        """
        # Try as direct ID first
        metadata_path = self._get_metadata_path(backup_id)
        if metadata_path.exists():
            try:
                with metadata_path.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    return BackupMetadata.from_dict(data)
            except Exception as e:
                logger.error(f"Could not load backup {backup_id}: {e}")
                return None
        
        # Try as index
        try:
            index = int(backup_id) - 1
            backups = self.list_backups()
            if 0 <= index < len(backups):
                return backups[index]
        except ValueError:
            pass
        
        return None
    
    def restore_backup(
        self,
        backup_id: str,
        confirm: bool = False
    ) -> RestoreResult:
        """Restore a backup.
        
        Args:
            backup_id: Backup ID or index to restore
            confirm: If True, skip confirmation prompt
            
        Returns:
            RestoreResult with operation details
        """
        # Get backup metadata
        metadata = self.get_backup(backup_id)
        if not metadata:
            console.print(f"[red]Error:[/red] Backup not found: {backup_id}")
            return RestoreResult(
                success=False,
                restored_count=0,
                failed_count=0,
                errors=[f"Backup not found: {backup_id}"]
            )
        
        # Confirm restoration
        if not confirm:
            console.print(f"\n[bold yellow]WARNING:[/bold yellow] This will restore {metadata.item_count} items")
            console.print(f"[dim]Backup: {metadata.backup_id}[/dim]")
            console.print(f"[dim]Operation: {metadata.operation_type}[/dim]")
            console.print(f"[dim]Timestamp: {metadata.timestamp.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
            
            response = console.input("\n[bold]Continue? [y/N]:[/bold] ")
            if response.lower() != 'y':
                console.print("[dim]Restore cancelled[/dim]")
                return RestoreResult(
                    success=False,
                    restored_count=0,
                    failed_count=0,
                    errors=["Cancelled by user"]
                )
        
        # Perform restoration
        data_dir = self._get_data_dir(metadata.backup_id)
        
        if not data_dir.exists():
            console.print(f"[red]Error:[/red] Backup data not found")
            return RestoreResult(
                success=False,
                restored_count=0,
                failed_count=0,
                errors=["Backup data directory not found"]
            )
        
        console.print(f"[dim]Restoring backup: {metadata.backup_id}...[/dim]")
        
        restored_count = 0
        failed_count = 0
        errors = []
        
        for item_meta in metadata.items:
            original_path = Path(item_meta['original_path'])
            rel_path = Path(item_meta['relative_path'])
            backup_item = data_dir / rel_path
            
            if not backup_item.exists():
                logger.warning(f"Backup item not found: {backup_item}")
                failed_count += 1
                errors.append(f"Backup item not found: {rel_path}")
                continue
            
            try:
                # Delete existing item if present
                if original_path.exists():
                    if original_path.is_dir():
                        shutil.rmtree(original_path)
                    else:
                        original_path.unlink()
                
                # Restore from backup
                self._copy_item(backup_item, original_path)
                restored_count += 1
                
            except Exception as e:
                logger.error(f"Failed to restore {original_path}: {e}")
                failed_count += 1
                errors.append(f"{original_path}: {e}")
        
        success = failed_count == 0
        
        if success:
            console.print(
                f"[green]OK[/green] Restore completed successfully: "
                f"{restored_count} items restored"
            )
        else:
            console.print(
                f"[yellow]WARNING[/yellow] Restore completed with errors: "
                f"{restored_count} restored, {failed_count} failed"
            )
            for error in errors[:5]:
                console.print(f"  [red]-[/red] {error}")
            if len(errors) > 5:
                console.print(f"  [dim]... and {len(errors) - 5} more errors[/dim]")
        
        return RestoreResult(
            success=success,
            restored_count=restored_count,
            failed_count=failed_count,
            errors=errors
        )
    
    def cleanup_old_backups(self) -> int:
        """Remove old backups beyond max_backups limit.
        
        Returns:
            Number of backups removed
        """
        backups = self.list_backups()
        
        if len(backups) <= self.max_backups:
            return 0
        
        # Remove oldest backups
        backups_to_remove = backups[self.max_backups:]
        removed_count = 0
        
        for backup in backups_to_remove:
            backup_dir = self._get_backup_dir(backup.backup_id)
            try:
                shutil.rmtree(backup_dir)
                removed_count += 1
                logger.info(f"Removed old backup: {backup.backup_id}")
            except Exception as e:
                logger.error(f"Failed to remove backup {backup.backup_id}: {e}")
        
        if removed_count > 0:
            console.print(
                f"[dim]Cleaned up {removed_count} old backup(s)[/dim]"
            )
        
        return removed_count
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete a specific backup.
        
        Args:
            backup_id: Backup ID to delete
            
        Returns:
            True if deleted successfully
        """
        metadata = self.get_backup(backup_id)
        if not metadata:
            console.print(f"[red]Error:[/red] Backup not found: {backup_id}")
            return False
        
        backup_dir = self._get_backup_dir(metadata.backup_id)
        
        try:
            shutil.rmtree(backup_dir)
            console.print(f"[green]OK[/green] Backup deleted: {metadata.backup_id}")
            return True
        except Exception as e:
            console.print(f"[red]Error deleting backup:[/red] {e}")
            return False


def display_backups_table(backups: List[BackupMetadata]) -> None:
    """Display backups in a formatted table.
    
    Args:
        backups: List of backup metadata
    """
    if not backups:
        console.print("[yellow]No backups found[/yellow]")
        return
    
    table = Table(title="Available Backups")
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Backup ID", style="yellow")
    table.add_column("Operation", style="magenta")
    table.add_column("Timestamp", style="green")
    table.add_column("Items", style="blue", justify="right")
    table.add_column("Size", style="dim", justify="right")
    
    for idx, backup in enumerate(backups, 1):
        table.add_row(
            str(idx),
            backup.backup_id,
            backup.operation_type,
            backup.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            str(backup.item_count),
            f"{backup.total_size_kb:.1f} KB"
        )
    
    console.print(table)
    console.print(f"\n[dim]Use 'cursor-org undo <#>' to restore a backup[/dim]")
