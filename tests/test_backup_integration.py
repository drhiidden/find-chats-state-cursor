"""Integration tests for backup system with organize and clean commands."""
import tempfile
from pathlib import Path
import pytest
import shutil

from cursor_org.backup import BackupManager
from cursor_org.cleanup import TranscriptCleaner
from cursor_org.organizer import organize_recursively
from cursor_org.collector import TranscriptCollector


@pytest.fixture
def test_workspace_with_transcripts():
    """Create a test workspace with UUID folders and transcripts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create UUID folder with transcript
        uuid_folder = root / "b104cc43-a667-4487-9a6c-c5973777592a"
        uuid_folder.mkdir()
        
        transcript_content = """{"type":"user","content":"Test message 1","timestamp":"2026-03-14T10:00:00Z"}
{"type":"assistant","content":"Test response 1","timestamp":"2026-03-14T10:00:30Z"}
"""
        (uuid_folder / "chat.jsonl").write_text(transcript_content)
        
        # Create another UUID folder
        uuid_folder2 = root / "c205dd54-b778-5598-0b7d-d6084888603b"
        uuid_folder2.mkdir()
        (uuid_folder2 / "chat.jsonl").write_text(transcript_content)
        
        # Create empty folders to clean
        (root / "empty_folder").mkdir()
        (root / "mcp").mkdir()
        
        yield root


def test_organize_with_backup(test_workspace_with_transcripts):
    """Test that organize creates backup and can be undone."""
    root = test_workspace_with_transcripts
    
    # Get original folders
    uuid_folders = [
        d for d in root.iterdir() 
        if d.is_dir() and len(d.name) == 36 and d.name.count('-') == 4
    ]
    assert len(uuid_folders) == 2
    
    # Create backup manager
    backup_manager = BackupManager(root)
    
    # Create backup before organizing
    backup_id = backup_manager.create_backup(
        items_to_backup=uuid_folders,
        operation_type='organize'
    )
    
    assert backup_id is not None
    
    # Organize
    results = organize_recursively(
        root_dir=root,
        dry_run=False,
        ide='cursor',
        organize_nested=False
    )
    
    # Verify organization happened
    assert results['summary']['organized_main'] == 2
    
    # Check folders were renamed
    organized_folders = [
        d for d in root.iterdir()
        if d.is_dir() and d.name.startswith('2026-')
    ]
    assert len(organized_folders) == 2
    
    # Undo organization
    result = backup_manager.restore_backup(backup_id, confirm=True)
    
    assert result.success
    assert result.restored_count == 2
    
    # Verify folders restored to UUID names
    restored_uuid_folders = [
        d for d in root.iterdir()
        if d.is_dir() and len(d.name) == 36 and d.name.count('-') == 4
    ]
    assert len(restored_uuid_folders) == 2


def test_clean_with_backup(test_workspace_with_transcripts):
    """Test that clean creates backup and can be undone."""
    root = test_workspace_with_transcripts
    
    # Verify empty folders exist
    assert (root / "empty_folder").exists()
    assert (root / "mcp").exists()
    
    # Create backup manager
    backup_manager = BackupManager(root)
    
    # Scan for cleanup
    cleaner_scan = TranscriptCleaner(root, dry_run=True)
    folders_to_cleanup = cleaner_scan.scan_for_cleanup(max_depth=2)
    
    assert len(folders_to_cleanup) >= 2
    
    # Create backup
    backup_id = backup_manager.create_backup(
        items_to_backup=[r.path for r in folders_to_cleanup],
        operation_type='clean'
    )
    
    assert backup_id is not None
    
    # Perform cleanup
    cleaner = TranscriptCleaner(root, dry_run=False)
    cleaner.clean(max_depth=2)
    
    # Verify folders deleted
    assert not (root / "empty_folder").exists()
    assert not (root / "mcp").exists()
    
    # Undo cleanup
    result = backup_manager.restore_backup(backup_id, confirm=True)
    
    assert result.success
    assert result.restored_count >= 2
    
    # Verify folders restored
    assert (root / "empty_folder").exists()
    assert (root / "mcp").exists()


def test_backup_list_after_operations(test_workspace_with_transcripts):
    """Test listing backups after multiple operations."""
    root = test_workspace_with_transcripts
    backup_manager = BackupManager(root)
    
    # Create backup for organize
    uuid_folders = [
        d for d in root.iterdir()
        if d.is_dir() and len(d.name) == 36 and d.name.count('-') == 4
    ]
    
    backup_id1 = backup_manager.create_backup(uuid_folders, 'organize')
    
    # Create backup for clean
    empty_folders = [root / "empty_folder", root / "mcp"]
    backup_id2 = backup_manager.create_backup(empty_folders, 'clean')
    
    # List backups
    backups = backup_manager.list_backups()
    
    assert len(backups) == 2
    
    # Verify operation types
    operation_types = {b.operation_type for b in backups}
    assert 'organize' in operation_types
    assert 'clean' in operation_types


def test_backup_cleanup_after_max_backups(test_workspace_with_transcripts):
    """Test that old backups are automatically cleaned up."""
    root = test_workspace_with_transcripts
    backup_manager = BackupManager(root, max_backups=3)
    
    test_file = root / "test.txt"
    test_file.write_text("test content")
    
    # Create 5 backups
    backup_ids = []
    for i in range(5):
        backup_id = backup_manager.create_backup([test_file], f'test_{i}')
        backup_ids.append(backup_id)
        import time
        time.sleep(0.1)
    
    # Should only keep 3 newest backups
    backups = backup_manager.list_backups()
    assert len(backups) <= 3
    
    # Oldest backups should be deleted
    assert not backup_manager._get_backup_dir(backup_ids[0]).exists()
    assert not backup_manager._get_backup_dir(backup_ids[1]).exists()
    
    # Newest backups should exist
    assert backup_manager._get_backup_dir(backup_ids[3]).exists()
    assert backup_manager._get_backup_dir(backup_ids[4]).exists()


def test_organize_and_clean_with_backup_flow(test_workspace_with_transcripts):
    """Test complete workflow: organize, clean, and undo both."""
    root = test_workspace_with_transcripts
    backup_manager = BackupManager(root, max_backups=10)
    
    # Step 1: Organize with backup
    uuid_folders = [
        d for d in root.iterdir()
        if d.is_dir() and len(d.name) == 36 and d.name.count('-') == 4
    ]
    organize_backup_id = backup_manager.create_backup(uuid_folders, 'organize')
    
    organize_recursively(root, dry_run=False, ide='cursor', organize_nested=False)
    
    # Step 2: Clean with backup
    cleaner_scan = TranscriptCleaner(root, dry_run=True)
    folders_to_cleanup = cleaner_scan.scan_for_cleanup(max_depth=2)
    clean_backup_id = backup_manager.create_backup(
        [r.path for r in folders_to_cleanup], 'clean'
    )
    
    cleaner = TranscriptCleaner(root, dry_run=False)
    cleaner.clean(max_depth=2)
    
    # Verify state: organized folders, no empty folders
    organized = [d for d in root.iterdir() if d.is_dir() and d.name.startswith('2026-')]
    assert len(organized) >= 2
    assert not (root / "empty_folder").exists()
    
    # Step 3: Undo clean
    clean_result = backup_manager.restore_backup(clean_backup_id, confirm=True)
    assert clean_result.success
    
    # Verify: organized folders still there, empty folders restored
    assert (root / "empty_folder").exists()
    assert (root / "mcp").exists()
    
    # Step 4: Undo organize
    organize_result = backup_manager.restore_backup(organize_backup_id, confirm=True)
    assert organize_result.success
    
    # Verify: back to original UUID folders
    uuid_folders_after = [
        d for d in root.iterdir()
        if d.is_dir() and len(d.name) == 36 and d.name.count('-') == 4
    ]
    assert len(uuid_folders_after) == 2


def test_backup_preserves_file_content(test_workspace_with_transcripts):
    """Test that backup preserves exact file content during organize."""
    root = test_workspace_with_transcripts
    backup_manager = BackupManager(root)
    
    # Get first UUID folder
    uuid_folder = [
        d for d in root.iterdir()
        if d.is_dir() and len(d.name) == 36 and d.name.count('-') == 4
    ][0]
    
    # Read original content
    original_content = (uuid_folder / "chat.jsonl").read_text()
    
    # Create backup
    backup_id = backup_manager.create_backup([uuid_folder], 'organize')
    
    # Organize
    organize_recursively(root, dry_run=False, ide='cursor', organize_nested=False)
    
    # Restore
    backup_manager.restore_backup(backup_id, confirm=True)
    
    # Verify content preserved
    restored_content = (uuid_folder / "chat.jsonl").read_text()
    assert restored_content == original_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
