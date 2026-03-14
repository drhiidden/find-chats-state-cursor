"""Tests for cleanup functionality."""
import tempfile
from pathlib import Path
import pytest

from cursor_org.cleanup import TranscriptCleaner, CleanupResult


@pytest.fixture
def test_dir():
    """Create a temporary test directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create various folder structures
        # 1. Empty folder
        (root / "empty_folder").mkdir()
        
        # 2. MCP folder (empty)
        (root / "mcp").mkdir()
        
        # 3. agent-tools folder (empty)
        (root / "agent-tools").mkdir()
        
        # 4. Folder with only hidden files
        hidden_folder = root / "hidden_only"
        hidden_folder.mkdir()
        (hidden_folder / ".DS_Store").touch()
        (hidden_folder / ".gitkeep").touch()
        
        # 5. Folder with actual content (should NOT be deleted)
        content_folder = root / "with_content"
        content_folder.mkdir()
        (content_folder / "transcript.jsonl").write_text('{"test": 1}')
        
        # 6. Nested empty folders
        nested = root / "nested" / "empty" / "deep"
        nested.mkdir(parents=True)
        
        # 7. Protected folder (agent-transcripts)
        protected = root / "agent-transcripts"
        protected.mkdir()
        
        # 8. Folder with subfolder that has content
        mixed = root / "mixed"
        mixed.mkdir()
        (mixed / "sub").mkdir()
        (mixed / "sub" / "file.txt").write_text("content")
        
        yield root


def test_is_empty_folder_true(test_dir):
    """Test detecting empty folders."""
    cleaner = TranscriptCleaner(test_dir)
    
    assert cleaner.is_empty_folder(test_dir / "empty_folder")
    assert cleaner.is_empty_folder(test_dir / "mcp")
    assert cleaner.is_empty_folder(test_dir / "agent-tools")
    assert cleaner.is_empty_folder(test_dir / "nested")


def test_is_empty_folder_false(test_dir):
    """Test detecting non-empty folders."""
    cleaner = TranscriptCleaner(test_dir)
    
    assert not cleaner.is_empty_folder(test_dir / "with_content")
    assert not cleaner.is_empty_folder(test_dir / "mixed")
    assert not cleaner.is_empty_folder(test_dir / "hidden_only")  # Has files


def test_has_only_hidden_files(test_dir):
    """Test detecting folders with only hidden files."""
    cleaner = TranscriptCleaner(test_dir)
    
    assert cleaner.has_only_hidden_files(test_dir / "hidden_only")
    assert not cleaner.has_only_hidden_files(test_dir / "with_content")
    assert not cleaner.has_only_hidden_files(test_dir / "empty_folder")


def test_is_irrelevant_folder(test_dir):
    """Test identifying irrelevant folders."""
    cleaner = TranscriptCleaner(test_dir)
    
    # Should be irrelevant
    is_irrelevant, reason = cleaner.is_irrelevant_folder(test_dir / "mcp")
    assert is_irrelevant
    assert "mcp" in reason.lower()
    
    is_irrelevant, reason = cleaner.is_irrelevant_folder(test_dir / "agent-tools")
    assert is_irrelevant
    
    is_irrelevant, reason = cleaner.is_irrelevant_folder(test_dir / "empty_folder")
    assert is_irrelevant
    assert "empty" in reason.lower()
    
    is_irrelevant, reason = cleaner.is_irrelevant_folder(test_dir / "hidden_only")
    assert is_irrelevant
    assert "hidden" in reason.lower()


def test_is_not_irrelevant_folder(test_dir):
    """Test identifying relevant folders."""
    cleaner = TranscriptCleaner(test_dir)
    
    # Should NOT be irrelevant
    is_irrelevant, _ = cleaner.is_irrelevant_folder(test_dir / "with_content")
    assert not is_irrelevant
    
    is_irrelevant, _ = cleaner.is_irrelevant_folder(test_dir / "mixed")
    assert not is_irrelevant


def test_protected_folders(test_dir):
    """Test that protected folders are never marked for cleanup."""
    cleaner = TranscriptCleaner(test_dir)
    
    # agent-transcripts should never be irrelevant even if empty
    is_irrelevant, _ = cleaner.is_irrelevant_folder(test_dir / "agent-transcripts")
    assert not is_irrelevant


def test_get_folder_size(test_dir):
    """Test calculating folder size."""
    cleaner = TranscriptCleaner(test_dir)
    
    # Empty folder
    size_kb, count = cleaner.get_folder_size(test_dir / "empty_folder")
    assert size_kb == 0.0
    assert count == 0
    
    # Folder with content
    size_kb, count = cleaner.get_folder_size(test_dir / "with_content")
    assert size_kb > 0
    assert count == 1
    
    # Folder with hidden files
    size_kb, count = cleaner.get_folder_size(test_dir / "hidden_only")
    assert count == 2


def test_scan_for_cleanup(test_dir):
    """Test scanning for folders to cleanup."""
    cleaner = TranscriptCleaner(test_dir, dry_run=True)
    results = cleaner.scan_for_cleanup()
    
    # Should find several folders to clean
    assert len(results) > 0
    
    # Check that we found the expected folders
    found_paths = {r.path.name for r in results}
    assert "mcp" in found_paths
    assert "agent-tools" in found_paths
    assert "empty_folder" in found_paths
    assert "hidden_only" in found_paths
    
    # Should NOT include these
    assert "with_content" not in found_paths
    assert "agent-transcripts" not in found_paths


def test_clean_dry_run(test_dir):
    """Test cleanup in dry-run mode."""
    cleaner = TranscriptCleaner(test_dir, dry_run=True)
    results = cleaner.clean()
    
    # Should have results
    assert len(results) > 0
    
    # No results should be deleted in dry-run
    assert all(not r.deleted for r in results)
    
    # All folders should still exist
    assert (test_dir / "mcp").exists()
    assert (test_dir / "empty_folder").exists()


def test_clean_apply(test_dir):
    """Test actual cleanup."""
    cleaner = TranscriptCleaner(test_dir, dry_run=False)
    results = cleaner.clean()
    
    # Should have results
    assert len(results) > 0
    
    # Results should be marked as deleted
    assert any(r.deleted for r in results)
    
    # Irrelevant folders should be deleted
    assert not (test_dir / "mcp").exists()
    assert not (test_dir / "empty_folder").exists()
    
    # Content folders should still exist
    assert (test_dir / "with_content").exists()
    assert (test_dir / "mixed").exists()


def test_cleanup_result_dataclass():
    """Test CleanupResult dataclass."""
    result = CleanupResult(
        path=Path("/test/path"),
        reason="Empty folder",
        size_kb=0.0,
        item_count=0,
        deleted=False
    )
    
    assert result.path == Path("/test/path")
    assert result.reason == "Empty folder"
    assert result.size_kb == 0.0
    assert result.item_count == 0
    assert not result.deleted


def test_max_depth_respected(test_dir):
    """Test that max_depth limits scanning depth."""
    cleaner = TranscriptCleaner(test_dir, dry_run=True)
    
    # Scan with depth 1 - should find top-level folders only
    results_shallow = cleaner.scan_for_cleanup(max_depth=1)
    
    # Scan with depth 3 - should find nested folders too
    results_deep = cleaner.scan_for_cleanup(max_depth=3)
    
    # Deep scan should find at least as many as shallow
    assert len(results_deep) >= len(results_shallow)


def test_nested_empty_folders(test_dir):
    """Test handling of nested empty folder structures."""
    cleaner = TranscriptCleaner(test_dir, dry_run=True)
    
    # The nested empty structure should be detected
    assert cleaner.is_empty_folder(test_dir / "nested")
    assert cleaner.is_empty_folder(test_dir / "nested" / "empty")
    assert cleaner.is_empty_folder(test_dir / "nested" / "empty" / "deep")


def test_mixed_folder_not_cleaned(test_dir):
    """Test that folders with some content are not cleaned."""
    cleaner = TranscriptCleaner(test_dir, dry_run=False)
    cleaner.clean()
    
    # Mixed folder has a subfolder with content, should not be deleted
    assert (test_dir / "mixed").exists()
    assert (test_dir / "mixed" / "sub" / "file.txt").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
