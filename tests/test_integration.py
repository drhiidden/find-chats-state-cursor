"""Tests for .procontext integration module."""

import pytest
from datetime import datetime, timezone
from pathlib import Path

from cursor_org.models import TranscriptMetadata
from cursor_org.integration import (
    sync_to_procontext,
    generate_daily_summary,
    save_daily_summary,
    _find_procontext_root,
    _extract_excerpt,
)


@pytest.fixture
def sample_metadata():
    """Create sample metadata for testing."""
    return TranscriptMetadata(
        uuid="test1234-5678-90ab-cdef-123456789abc",
        file_path=Path("/fake/transcript.jsonl"),
        start_time=datetime(2026, 3, 14, 15, 30, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 3, 14, 16, 0, 0, tzinfo=timezone.utc),
        message_count=20,
        user_messages=8,
        assistant_messages=12,
        topic_raw="Test implementation of feature Y",
    )


@pytest.fixture
def procontext_root(tmp_path):
    """Create a temporary .procontext directory structure."""
    procontext = tmp_path / ".procontext"
    procontext.mkdir()
    return procontext


def test_sync_to_procontext(sample_metadata, procontext_root):
    """Test syncing summary to .procontext/sessions/ structure."""
    summary_content = "# Test Summary\n\nThis is a test summary."

    output_path = sync_to_procontext(
        summary_content, sample_metadata, procontext_root=procontext_root
    )

    assert output_path.exists()
    assert output_path.parent.name == "2026-03-14"
    assert output_path.name == "15h30_test-implementation-of-feature-y_test1234.md"

    saved_content = output_path.read_text(encoding="utf-8")
    assert saved_content == summary_content


def test_sync_creates_directory_structure(sample_metadata, procontext_root):
    """Test that sync creates nested directories if they don't exist."""
    summary_content = "# Test"

    output_path = sync_to_procontext(
        summary_content, sample_metadata, procontext_root=procontext_root
    )

    sessions_dir = procontext_root / "sessions"
    date_dir = sessions_dir / "2026-03-14"

    assert sessions_dir.exists()
    assert date_dir.exists()
    assert output_path.exists()


def test_generate_daily_summary_empty(procontext_root):
    """Test daily summary generation when no sessions exist."""
    date = datetime(2026, 3, 14, tzinfo=timezone.utc)

    summary = generate_daily_summary(date, procontext_root=procontext_root)

    assert "# Daily Summary: 2026-03-14" in summary
    assert "No sessions found" in summary


def test_generate_daily_summary_with_sessions(sample_metadata, procontext_root):
    """Test daily summary generation with existing sessions."""
    # Create some session files
    sessions_dir = procontext_root / "sessions" / "2026-03-14"
    sessions_dir.mkdir(parents=True)

    (sessions_dir / "10h30_implement-auth_12345678.md").write_text(
        "# Summary\nAuth implementation completed."
    )
    (sessions_dir / "14h00_fix-bug_abcdef12.md").write_text("# Summary\nBug fixed.")

    date = datetime(2026, 3, 14, tzinfo=timezone.utc)
    summary = generate_daily_summary(date, procontext_root=procontext_root)

    assert "# Daily Summary: 2026-03-14" in summary
    assert "**Total Sessions**: 2" in summary
    assert "10h30 - Implement Auth" in summary
    assert "14h00 - Fix Bug" in summary


def test_save_daily_summary(procontext_root):
    """Test saving daily summary to README.md."""
    sessions_dir = procontext_root / "sessions" / "2026-03-14"
    sessions_dir.mkdir(parents=True)

    (sessions_dir / "10h00_test-session_12345678.md").write_text("# Test")

    date = datetime(2026, 3, 14, tzinfo=timezone.utc)
    output_path = save_daily_summary(date, procontext_root=procontext_root)

    assert output_path.exists()
    assert output_path.name == "README.md"
    assert output_path.parent == sessions_dir

    content = output_path.read_text(encoding="utf-8")
    assert "# Daily Summary: 2026-03-14" in content


def test_find_procontext_root_in_parent(tmp_path):
    """Test finding .procontext in parent directory."""
    # Create structure: tmp_path/.procontext and tmp_path/sub/file.txt
    procontext = tmp_path / ".procontext"
    procontext.mkdir()

    sub_dir = tmp_path / "sub" / "nested"
    sub_dir.mkdir(parents=True)
    test_file = sub_dir / "file.txt"
    test_file.write_text("test")

    found = _find_procontext_root(test_file)
    assert found == procontext


def test_find_procontext_root_not_found(tmp_path, monkeypatch):
    """Test that FileNotFoundError is raised when .procontext not found."""
    test_file = tmp_path / "file.txt"
    test_file.write_text("test")

    # Change cwd to tmp_path to avoid finding the real .procontext
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError):
        _find_procontext_root(test_file)


def test_extract_excerpt():
    """Test excerpt extraction from markdown content."""
    content = """# Title

**Metadata**: value

This is the main content that should be extracted.

More content here.
"""
    excerpt = _extract_excerpt(content, max_length=50)
    assert "main content" in excerpt
    assert len(excerpt) <= 53


def test_extract_excerpt_long_content():
    """Test excerpt truncation for long content."""
    content = """# Title

This is a very long line that should be truncated to the maximum length specified in the function call.
"""
    excerpt = _extract_excerpt(content, max_length=30)
    assert len(excerpt) <= 33
    assert excerpt.endswith("...")


def test_extract_excerpt_no_content():
    """Test excerpt extraction when no suitable content found."""
    content = """# Title
## Subtitle
**Metadata**
---
"""
    excerpt = _extract_excerpt(content)
    assert excerpt == ""
