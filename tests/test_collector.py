"""Tests for the generic transcript collector."""
import tempfile
from pathlib import Path
import pytest

from cursor_org.collector import (
    TranscriptCollector,
    FileFilter,
    TranscriptFile,
    group_transcripts_by_parent
)


@pytest.fixture
def test_structure(tmp_path):
    """Create a test directory structure with various transcript layouts."""
    # Main UUID folder with transcript
    uuid_folder1 = tmp_path / "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    uuid_folder1.mkdir()
    (uuid_folder1 / "a1b2c3d4-e5f6-7890-abcd-ef1234567890.jsonl").write_text('{"test": 1}')
    
    # Main UUID folder with subagents
    uuid_folder2 = tmp_path / "b2c3d4e5-f6a7-8901-bcde-f12345678901"
    uuid_folder2.mkdir()
    (uuid_folder2 / "b2c3d4e5-f6a7-8901-bcde-f12345678901.jsonl").write_text('{"test": 2}')
    
    subagents = uuid_folder2 / "subagents"
    subagents.mkdir()
    (subagents / "c3d4e5f6-a7b8-9012-cdef-123456789012.jsonl").write_text('{"test": 3}')
    (subagents / "d4e5f6a7-b8c9-0123-def1-234567890123.jsonl").write_text('{"test": 4}')
    
    # Already organized folder
    organized = tmp_path / "2026-03-14_10h30_some-topic_e5f6a7b8"
    organized.mkdir()
    (organized / "e5f6a7b8-c9d0-1234-ef12-345678901234.jsonl").write_text('{"test": 5}')
    
    # Random folder to skip
    random = tmp_path / "some-other-folder"
    random.mkdir()
    (random / "data.jsonl").write_text('{"test": 6}')
    
    return tmp_path


def test_file_filter_is_jsonl(tmp_path):
    """Test JSONL file detection."""
    jsonl = tmp_path / "test.jsonl"
    txt = tmp_path / "test.txt"
    jsonl.touch()
    txt.touch()
    
    assert FileFilter.is_jsonl(jsonl)
    assert not FileFilter.is_jsonl(txt)


def test_file_filter_is_uuid_folder(tmp_path):
    """Test UUID folder detection."""
    uuid_folder = tmp_path / "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    normal_folder = tmp_path / "normal-folder"
    uuid_folder.mkdir()
    normal_folder.mkdir()
    
    assert FileFilter.is_uuid_folder(uuid_folder)
    assert not FileFilter.is_uuid_folder(normal_folder)


def test_file_filter_is_organized_folder(tmp_path):
    """Test organized folder detection."""
    organized = tmp_path / "2026-03-14_10h30_topic_a1b2c3d4"
    uuid = tmp_path / "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    organized.mkdir()
    uuid.mkdir()
    
    assert FileFilter.is_organized_folder(organized)
    assert not FileFilter.is_organized_folder(uuid)


def test_collector_collect_all(test_structure):
    """Test collecting all transcripts."""
    collector = TranscriptCollector(test_structure)
    transcripts = list(collector.collect_all())
    
    # Should find all 6 JSONL files
    assert len(transcripts) == 6
    
    # Check that we have both nested and non-nested
    # Nested means depth > 1 (e.g., root/folder/subagents/file.jsonl)
    nested = [t for t in transcripts if t.is_nested]
    non_nested = [t for t in transcripts if not t.is_nested]
    
    assert len(nested) == 2  # The 2 subagent files (depth 2)
    assert len(non_nested) == 4  # Main files (depth 1)


def test_collector_collect_from_uuid_folders(test_structure):
    """Test collecting only from UUID folders."""
    collector = TranscriptCollector(test_structure)
    transcripts = list(collector.collect_from_uuid_folders())
    
    # Should find only files in UUID-named folders (2 main + not organized/random)
    # Actually, collect_from_uuid_folders only looks at direct children of UUID folders
    uuid_transcripts = [t for t in transcripts if FileFilter.is_uuid_folder(t.parent_dir)]
    
    assert len(uuid_transcripts) >= 2  # At least the 2 main UUID folders


def test_collector_max_depth(test_structure):
    """Test depth limiting."""
    collector = TranscriptCollector(test_structure)
    
    # Depth 0: only files in root
    transcripts_d0 = list(collector.collect_all(max_depth=0))
    assert len(transcripts_d0) == 0  # No files directly in root
    
    # Depth 1: files in immediate subdirectories
    transcripts_d1 = list(collector.collect_all(max_depth=1))
    assert len(transcripts_d1) >= 3  # Main transcript files
    
    # Depth 2: includes nested files
    transcripts_d2 = list(collector.collect_all(max_depth=2))
    assert len(transcripts_d2) >= 5  # Includes subagents


def test_collector_exclude_nested(test_structure):
    """Test excluding nested files."""
    collector = TranscriptCollector(test_structure)
    transcripts = list(collector.collect_all(include_nested=False))
    
    # Should only get top-level files
    assert all(not t.is_nested for t in transcripts)
    assert len(transcripts) == 4  # Only main files


def test_group_transcripts_by_parent(test_structure):
    """Test grouping transcripts by parent directory."""
    collector = TranscriptCollector(test_structure)
    all_transcripts = list(collector.collect_all())
    
    groups = group_transcripts_by_parent(all_transcripts)
    
    # Should have multiple groups (one per unique parent directory)
    assert len(groups) >= 3  # At least: 2 UUID folders + 1 organized + 1 subagents
    
    # Find the group with subagents
    subagent_groups = [g for g in groups if len(g.children) > 0]
    
    # The subagents folder should have multiple transcripts
    if subagent_groups:
        assert len(subagent_groups[0].all_transcripts) > 1


def test_transcript_file_properties(test_structure):
    """Test TranscriptFile property accessors."""
    collector = TranscriptCollector(test_structure)
    transcript = next(collector.collect_all())
    
    assert transcript.name.endswith('.jsonl')
    assert transcript.parent_name is not None
    assert transcript.path.exists()
    assert transcript.depth >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
