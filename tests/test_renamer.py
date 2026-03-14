import pytest
from pathlib import Path
from cursor_org.renamer import rename_transcript_folder, validate_path_length
from cursor_org.models import TranscriptMetadata
from datetime import datetime, timezone


@pytest.fixture
def sample_metadata():
    """Create sample metadata for testing."""
    return TranscriptMetadata(
        uuid="b104cc43-a667-4487-9a6c-c5973777592a",
        file_path=Path("test.jsonl"),
        start_time=datetime(2026, 3, 12, 14, 30, tzinfo=timezone.utc),
        end_time=datetime(2026, 3, 12, 16, 45, tzinfo=timezone.utc),
        topic_raw="Fix parser bug in production",
    )


def test_rename_dry_run(tmp_path, sample_metadata):
    """Test renaming in dry-run mode."""
    # Create a UUID folder
    uuid_folder = tmp_path / sample_metadata.uuid
    uuid_folder.mkdir()

    # Dry run should return new path without renaming
    new_path = rename_transcript_folder(uuid_folder, sample_metadata, dry_run=True)

    assert new_path is not None
    assert "2026-03-12_14h30" in new_path.name
    assert "fix-parser-bug-in-production" in new_path.name
    assert uuid_folder.exists()  # Original still exists
    assert not new_path.exists()  # New path not created


def test_rename_actual(tmp_path, sample_metadata):
    """Test actual renaming."""
    uuid_folder = tmp_path / sample_metadata.uuid
    uuid_folder.mkdir()

    # Create a dummy file inside
    (uuid_folder / "test.jsonl").touch()

    # Execute rename
    new_path = rename_transcript_folder(uuid_folder, sample_metadata, dry_run=False)

    assert new_path is not None
    assert new_path.exists()
    assert not uuid_folder.exists()
    assert (new_path / "test.jsonl").exists()


def test_validate_path_length():
    """Test path length validation."""
    short_path = Path("C:/short/path")
    long_path = Path("C:/" + "x" * 300)

    assert validate_path_length(short_path)
    assert not validate_path_length(long_path)
