"""Tests for backup and restore functionality."""
import tempfile
from pathlib import Path
import pytest
import json
import time

from cursor_org.backup import (
    BackupManager, BackupMetadata, RestoreResult,
    display_backups_table
)


@pytest.fixture
def test_workspace():
    """Create a temporary workspace with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create test folders with content
        folder1 = root / "folder1"
        folder1.mkdir()
        (folder1 / "file1.txt").write_text("Content 1")
        (folder1 / "file2.txt").write_text("Content 2")
        
        folder2 = root / "folder2"
        folder2.mkdir()
        (folder2 / "data.json").write_text('{"test": "data"}')
        
        # Create nested structure
        nested = root / "nested" / "deep"
        nested.mkdir(parents=True)
        (nested / "nested_file.txt").write_text("Nested content")
        
        yield root


@pytest.fixture
def backup_manager(test_workspace):
    """Create a backup manager for testing."""
    return BackupManager(test_workspace, max_backups=5)


def test_backup_manager_init(test_workspace):
    """Test backup manager initialization."""
    manager = BackupManager(test_workspace, max_backups=10)
    
    assert manager.work_dir == test_workspace
    assert manager.max_backups == 10
    assert manager.backup_root == test_workspace / '.cursor-org-backups'


def test_generate_backup_id(backup_manager):
    """Test backup ID generation."""
    backup_id = backup_manager._generate_backup_id('organize')
    
    assert 'organize' in backup_id
    assert '_' in backup_id
    assert len(backup_id) > 10


def test_create_backup_empty_list(backup_manager):
    """Test creating backup with empty list."""
    backup_id = backup_manager.create_backup([], 'test')
    
    assert backup_id is None


def test_create_backup_success(backup_manager, test_workspace):
    """Test successful backup creation."""
    items = [
        test_workspace / "folder1",
        test_workspace / "folder2"
    ]
    
    backup_id = backup_manager.create_backup(items, 'organize')
    
    assert backup_id is not None
    assert 'organize' in backup_id
    
    # Check backup directory created
    backup_dir = backup_manager._get_backup_dir(backup_id)
    assert backup_dir.exists()
    
    # Check metadata file exists
    metadata_path = backup_manager._get_metadata_path(backup_id)
    assert metadata_path.exists()
    
    # Check data copied
    data_dir = backup_manager._get_data_dir(backup_id)
    assert data_dir.exists()
    assert (data_dir / "folder1").exists()
    assert (data_dir / "folder1" / "file1.txt").exists()
    assert (data_dir / "folder2").exists()


def test_create_backup_preserves_content(backup_manager, test_workspace):
    """Test that backup preserves file content."""
    items = [test_workspace / "folder1"]
    
    backup_id = backup_manager.create_backup(items, 'test')
    
    data_dir = backup_manager._get_data_dir(backup_id)
    backed_up_file = data_dir / "folder1" / "file1.txt"
    
    assert backed_up_file.exists()
    assert backed_up_file.read_text() == "Content 1"


def test_create_backup_nested_structure(backup_manager, test_workspace):
    """Test backup of nested folder structure."""
    items = [test_workspace / "nested"]
    
    backup_id = backup_manager.create_backup(items, 'test')
    
    data_dir = backup_manager._get_data_dir(backup_id)
    nested_file = data_dir / "nested" / "deep" / "nested_file.txt"
    
    assert nested_file.exists()
    assert nested_file.read_text() == "Nested content"


def test_list_backups_empty(backup_manager):
    """Test listing backups when none exist."""
    backups = backup_manager.list_backups()
    
    assert backups == []


def test_list_backups_multiple(backup_manager, test_workspace):
    """Test listing multiple backups."""
    items = [test_workspace / "folder1"]
    
    # Create multiple backups
    backup_id1 = backup_manager.create_backup(items, 'organize')
    time.sleep(0.1)
    backup_id2 = backup_manager.create_backup(items, 'clean')
    time.sleep(0.1)
    backup_id3 = backup_manager.create_backup(items, 'organize')
    
    backups = backup_manager.list_backups()
    
    assert len(backups) == 3
    
    # Should be sorted newest first
    assert backups[0].backup_id == backup_id3
    assert backups[1].backup_id == backup_id2
    assert backups[2].backup_id == backup_id1


def test_get_backup_by_id(backup_manager, test_workspace):
    """Test retrieving backup by ID."""
    items = [test_workspace / "folder1"]
    backup_id = backup_manager.create_backup(items, 'test')
    
    metadata = backup_manager.get_backup(backup_id)
    
    assert metadata is not None
    assert metadata.backup_id == backup_id
    assert metadata.operation_type == 'test'
    assert metadata.item_count == 1


def test_get_backup_by_index(backup_manager, test_workspace):
    """Test retrieving backup by index."""
    items = [test_workspace / "folder1"]
    
    backup_id1 = backup_manager.create_backup(items, 'first')
    time.sleep(0.1)
    backup_id2 = backup_manager.create_backup(items, 'second')
    
    # Get by index (1-based)
    metadata = backup_manager.get_backup('1')
    assert metadata is not None
    assert metadata.backup_id == backup_id2
    
    metadata = backup_manager.get_backup('2')
    assert metadata is not None
    assert metadata.backup_id == backup_id1


def test_get_backup_not_found(backup_manager):
    """Test retrieving non-existent backup."""
    metadata = backup_manager.get_backup('nonexistent')
    
    assert metadata is None


def test_restore_backup_success(backup_manager, test_workspace):
    """Test successful backup restoration."""
    items = [test_workspace / "folder1"]
    
    # Create backup
    backup_id = backup_manager.create_backup(items, 'test')
    
    # Delete original folder
    import shutil
    shutil.rmtree(test_workspace / "folder1")
    assert not (test_workspace / "folder1").exists()
    
    # Restore
    result = backup_manager.restore_backup(backup_id, confirm=True)
    
    assert result.success
    assert result.restored_count == 1
    assert result.failed_count == 0
    
    # Check folder restored
    assert (test_workspace / "folder1").exists()
    assert (test_workspace / "folder1" / "file1.txt").exists()
    assert (test_workspace / "folder1" / "file1.txt").read_text() == "Content 1"


def test_restore_backup_overwrites_existing(backup_manager, test_workspace):
    """Test that restore overwrites existing files."""
    items = [test_workspace / "folder1"]
    
    # Create backup
    backup_id = backup_manager.create_backup(items, 'test')
    
    # Modify original file
    (test_workspace / "folder1" / "file1.txt").write_text("Modified content")
    
    # Restore
    result = backup_manager.restore_backup(backup_id, confirm=True)
    
    assert result.success
    
    # Check content restored to original
    assert (test_workspace / "folder1" / "file1.txt").read_text() == "Content 1"


def test_restore_backup_not_found(backup_manager):
    """Test restoring non-existent backup."""
    result = backup_manager.restore_backup('nonexistent', confirm=True)
    
    assert not result.success
    assert result.restored_count == 0
    assert len(result.errors) > 0


def test_cleanup_old_backups(backup_manager, test_workspace):
    """Test automatic cleanup of old backups."""
    items = [test_workspace / "folder1"]
    
    # Set max_backups to 3
    backup_manager.max_backups = 3
    
    # Create 5 backups
    backup_ids = []
    for i in range(5):
        backup_id = backup_manager.create_backup(items, f'test_{i}')
        backup_ids.append(backup_id)
        time.sleep(0.1)
    
    # Should only have 3 backups (newest ones)
    backups = backup_manager.list_backups()
    assert len(backups) <= 3
    
    # Oldest backups should be deleted
    assert not backup_manager._get_backup_dir(backup_ids[0]).exists()
    assert not backup_manager._get_backup_dir(backup_ids[1]).exists()
    
    # Newest backups should exist
    assert backup_manager._get_backup_dir(backup_ids[3]).exists()
    assert backup_manager._get_backup_dir(backup_ids[4]).exists()


def test_delete_backup(backup_manager, test_workspace):
    """Test manual backup deletion."""
    items = [test_workspace / "folder1"]
    backup_id = backup_manager.create_backup(items, 'test')
    
    # Verify exists
    assert backup_manager._get_backup_dir(backup_id).exists()
    
    # Delete
    success = backup_manager.delete_backup(backup_id)
    
    assert success
    assert not backup_manager._get_backup_dir(backup_id).exists()


def test_delete_backup_not_found(backup_manager):
    """Test deleting non-existent backup."""
    success = backup_manager.delete_backup('nonexistent')
    
    assert not success


def test_calculate_size(backup_manager, test_workspace):
    """Test size calculation."""
    folder = test_workspace / "folder1"
    
    size_kb = backup_manager._calculate_size(folder)
    
    assert size_kb > 0


def test_backup_metadata_serialization():
    """Test BackupMetadata to/from dict."""
    from datetime import datetime
    
    metadata = BackupMetadata(
        backup_id='test_id',
        timestamp=datetime.now(),
        operation_type='organize',
        source_path=Path('/test/path'),
        item_count=5,
        total_size_kb=1024.5,
        items=[
            {'path': '/test/file1', 'size': 100},
            {'path': '/test/file2', 'size': 200}
        ]
    )
    
    # Serialize
    data = metadata.to_dict()
    
    assert data['backup_id'] == 'test_id'
    assert data['operation_type'] == 'organize'
    assert data['item_count'] == 5
    
    # Deserialize
    restored = BackupMetadata.from_dict(data)
    
    assert restored.backup_id == metadata.backup_id
    assert restored.operation_type == metadata.operation_type
    assert restored.item_count == metadata.item_count


def test_backup_with_single_file(backup_manager, test_workspace):
    """Test backup of a single file."""
    single_file = test_workspace / "single.txt"
    single_file.write_text("Single file content")
    
    backup_id = backup_manager.create_backup([single_file], 'test')
    
    assert backup_id is not None
    
    data_dir = backup_manager._get_data_dir(backup_id)
    assert (data_dir / "single.txt").exists()
    assert (data_dir / "single.txt").read_text() == "Single file content"


def test_restore_multiple_items(backup_manager, test_workspace):
    """Test restoring backup with multiple items."""
    items = [
        test_workspace / "folder1",
        test_workspace / "folder2"
    ]
    
    backup_id = backup_manager.create_backup(items, 'test')
    
    # Delete both folders
    import shutil
    shutil.rmtree(test_workspace / "folder1")
    shutil.rmtree(test_workspace / "folder2")
    
    # Restore
    result = backup_manager.restore_backup(backup_id, confirm=True)
    
    assert result.success
    assert result.restored_count == 2
    
    # Check both restored
    assert (test_workspace / "folder1").exists()
    assert (test_workspace / "folder2").exists()


def test_backup_large_file(backup_manager, test_workspace):
    """Test backup of larger file."""
    large_file = test_workspace / "large.bin"
    
    # Create 1MB file
    large_content = b"x" * (1024 * 1024)
    large_file.write_bytes(large_content)
    
    backup_id = backup_manager.create_backup([large_file], 'test')
    
    assert backup_id is not None
    
    # Verify content preserved
    data_dir = backup_manager._get_data_dir(backup_id)
    backed_up = data_dir / "large.bin"
    
    assert backed_up.exists()
    assert backed_up.stat().st_size == len(large_content)


def test_backup_metadata_in_json(backup_manager, test_workspace):
    """Test that metadata is properly saved as JSON."""
    items = [test_workspace / "folder1"]
    backup_id = backup_manager.create_backup(items, 'organize')
    
    metadata_path = backup_manager._get_metadata_path(backup_id)
    
    # Read and parse JSON
    with metadata_path.open('r') as f:
        data = json.load(f)
    
    assert data['backup_id'] == backup_id
    assert data['operation_type'] == 'organize'
    assert data['item_count'] == 1
    assert 'timestamp' in data
    assert 'items' in data


def test_display_backups_table_empty(capsys):
    """Test displaying empty backups table."""
    display_backups_table([])
    
    captured = capsys.readouterr()
    assert "No backups found" in captured.out or "yellow" in captured.out


def test_concurrent_backups(backup_manager, test_workspace):
    """Test creating multiple backups rapidly."""
    items = [test_workspace / "folder1"]
    
    backup_ids = []
    for i in range(3):
        backup_id = backup_manager.create_backup(items, f'test_{i}')
        backup_ids.append(backup_id)
        time.sleep(0.01)
    
    # All should succeed
    assert all(bid is not None for bid in backup_ids)
    
    # All should be unique
    assert len(set(backup_ids)) == 3


def test_restore_result_dataclass():
    """Test RestoreResult dataclass."""
    result = RestoreResult(
        success=True,
        restored_count=5,
        failed_count=0,
        errors=[]
    )
    
    assert result.success
    assert result.restored_count == 5
    assert result.failed_count == 0
    assert result.errors == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
