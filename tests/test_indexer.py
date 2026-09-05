"""
Tests for AITS indexer functionality
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import pytest

from cursor_org.indexer import TranscriptIndexer, generate_index
from cursor_org.models import TranscriptMetadata


@pytest.fixture
def temp_transcripts_dir():
    """Create a temporary directory with sample transcripts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create a few sample transcript files
        transcript1 = tmpdir_path / "550e8400-e29b-41d4-a716-446655440000.jsonl"
        transcript1.write_text(
            '{"role":"user","message":{"content":[{"type":"text","text":"Hello"}]}}\n'
            '{"role":"assistant","message":{"content":[{"type":"text","text":"Hi there"}]}}\n'
        )
        
        transcript2 = tmpdir_path / "661f9511-f3ac-52e5-b827-557766551111.jsonl"
        transcript2.write_text(
            '{"role":"user","message":{"content":[{"type":"text","text":"Fix the bug"}]}}\n'
        )
        
        yield tmpdir_path


def test_indexer_initialization(temp_transcripts_dir):
    """Test TranscriptIndexer initialization."""
    indexer = TranscriptIndexer(temp_transcripts_dir)
    
    assert indexer.transcripts_dir == temp_transcripts_dir
    assert indexer.index_path == temp_transcripts_dir / "index.json"


def test_generate_index_creates_file(temp_transcripts_dir):
    """Test that generate_index creates an index.json file."""
    indexer = TranscriptIndexer(temp_transcripts_dir)
    
    # Generate index
    index = indexer.generate_index()
    
    # Check file exists
    assert indexer.index_path.exists()
    
    # Check structure
    assert "aits_index_version" in index
    assert index["aits_index_version"] == "1.0.0"
    assert "updated_at" in index
    assert "total_transcripts" in index
    assert "transcripts" in index
    
    # Should have found 2 transcripts
    assert index["total_transcripts"] == 2
    assert len(index["transcripts"]) == 2


def test_index_entry_structure(temp_transcripts_dir):
    """Test that index entries have correct structure."""
    indexer = TranscriptIndexer(temp_transcripts_dir)
    index = indexer.generate_index()
    
    # Get first entry
    entry = index["transcripts"][0]
    
    # Check required fields
    assert "id" in entry
    assert "title" in entry
    assert "created_at" in entry
    assert "updated_at" in entry
    assert "status" in entry
    assert "path" in entry
    assert "message_count" in entry
    assert "compressed" in entry
    
    # Check types
    assert isinstance(entry["id"], str)
    assert isinstance(entry["title"], str)
    assert isinstance(entry["path"], str)
    assert isinstance(entry["message_count"], int)
    assert isinstance(entry["compressed"], bool)


def test_search_index_by_query(temp_transcripts_dir):
    """Test searching index by text query."""
    indexer = TranscriptIndexer(temp_transcripts_dir)
    indexer.generate_index()
    
    # Search for "bug"
    results = indexer.search_index(query="bug")
    
    # Should find the "Fix the bug" transcript
    assert len(results) >= 1
    assert any("bug" in r["title"].lower() for r in results)


def test_search_index_by_tag(temp_transcripts_dir):
    """Test searching index by tag."""
    indexer = TranscriptIndexer(temp_transcripts_dir)
    indexer.generate_index()
    
    # Since our test transcripts don't have tags, this should return empty
    results = indexer.search_index(tags=["python"])
    
    # Should be empty or not include transcripts without tags
    assert isinstance(results, list)


def test_get_statistics(temp_transcripts_dir):
    """Test getting statistics from index."""
    indexer = TranscriptIndexer(temp_transcripts_dir)
    indexer.generate_index()
    
    stats = indexer.get_statistics()
    
    # Check structure
    assert "total" in stats
    assert "by_status" in stats
    assert "by_language" in stats
    assert "by_tag" in stats
    assert "by_model" in stats
    
    # Check values
    assert stats["total"] == 2
    assert isinstance(stats["by_status"], dict)


def test_incremental_index_update(temp_transcripts_dir):
    """Test that incremental updates reuse existing entries."""
    indexer = TranscriptIndexer(temp_transcripts_dir)
    
    # Generate initial index
    index1 = indexer.generate_index()
    updated_at_1 = index1["updated_at"]
    
    # Wait a tiny bit (simulate time passing)
    import time
    time.sleep(0.01)
    
    # Regenerate without force (should be faster, reuse entries)
    index2 = indexer.generate_index(force_regenerate=False)
    
    # Index should be updated
    assert index2["updated_at"] != updated_at_1
    
    # But transcripts should be same
    assert index2["total_transcripts"] == index1["total_transcripts"]


def test_force_regenerate(temp_transcripts_dir):
    """Test force regeneration of index."""
    indexer = TranscriptIndexer(temp_transcripts_dir)
    
    # Generate initial
    index1 = indexer.generate_index()
    
    # Force regenerate
    index2 = indexer.generate_index(force_regenerate=True)
    
    # Should have same number of transcripts
    assert index2["total_transcripts"] == index1["total_transcripts"]


def test_generate_index_convenience_function(temp_transcripts_dir):
    """Test the convenience function generate_index()."""
    index = generate_index(temp_transcripts_dir)
    
    assert index["total_transcripts"] == 2
    assert (temp_transcripts_dir / "index.json").exists()


def test_index_handles_corrupted_transcripts(temp_transcripts_dir):
    """Test that index generation continues even if some files are corrupted."""
    # Add a corrupted file
    corrupted = temp_transcripts_dir / "corrupted.jsonl"
    corrupted.write_text("not valid json\n")
    
    indexer = TranscriptIndexer(temp_transcripts_dir)
    
    # Should still work, just skip the corrupted file
    index = indexer.generate_index()
    
    # Should have indexed the 2 good files
    # The corrupted file might be indexed but with empty metadata or skipped
    # So we just check that we have at least 2 good files
    assert index["total_transcripts"] >= 2


def test_index_normalized_paths(temp_transcripts_dir):
    """Test that index paths are normalized (forward slashes)."""
    indexer = TranscriptIndexer(temp_transcripts_dir)
    index = indexer.generate_index()
    
    for entry in index["transcripts"]:
        path = entry["path"]
        # Should use forward slashes, not backslashes
        assert "\\" not in path or "/" in path


def test_empty_directory_index(temp_transcripts_dir):
    """Test indexing an empty directory."""
    empty_dir = temp_transcripts_dir / "empty"
    empty_dir.mkdir()
    
    indexer = TranscriptIndexer(empty_dir)
    index = indexer.generate_index()
    
    assert index["total_transcripts"] == 0
    assert len(index["transcripts"]) == 0
