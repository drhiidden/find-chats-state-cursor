"""Tests for optional session journal export module."""

import pytest
from datetime import datetime, timezone
from pathlib import Path

from cursor_org.models import TranscriptMetadata
from cursor_org.integration import (
    sync_to_session_journal,
    generate_daily_summary,
    save_daily_summary,
    _find_journal_root,
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
def journal_root(tmp_path):
    """Create a temporary session journal root."""
    root = tmp_path / ".session-journal"
    root.mkdir()
    return root


def test_sync_to_session_journal(sample_metadata, journal_root):
    """Test syncing summary to sessions/ structure."""
    summary_content = "# Test Summary\n\nThis is a test summary."

    output_path = sync_to_session_journal(
        summary_content, sample_metadata, journal_root=journal_root
    )

    assert output_path.exists()
    assert output_path.parent.name == "2026-03-14"
    assert output_path.name == "15h30_test-implementation-of-feature-y_test1234.md"

    saved_content = output_path.read_text(encoding="utf-8")
    assert saved_content == summary_content


def test_sync_creates_directory_structure(sample_metadata, journal_root):
    """Test that sync creates nested directories if they don't exist."""
    summary_content = "# Test"

    output_path = sync_to_session_journal(
        summary_content, sample_metadata, journal_root=journal_root
    )

    sessions_dir = journal_root / "sessions"
    date_dir = sessions_dir / "2026-03-14"

    assert sessions_dir.exists()
    assert date_dir.exists()
    assert output_path.exists()


def test_generate_daily_summary_empty(journal_root):
    """Test daily summary generation when no sessions exist."""
    date = datetime(2026, 3, 14, tzinfo=timezone.utc)

    summary = generate_daily_summary(date, journal_root=journal_root)

    assert "# Daily Summary: 2026-03-14" in summary
    assert "No sessions found" in summary


def test_generate_daily_summary_with_sessions(sample_metadata, journal_root):
    """Test daily summary generation with existing sessions."""
    sessions_dir = journal_root / "sessions" / "2026-03-14"
    sessions_dir.mkdir(parents=True)

    (sessions_dir / "10h30_implement-auth_12345678.md").write_text(
        "# Summary\nAuth implementation completed."
    )
    (sessions_dir / "14h00_fix-bug_abcdef12.md").write_text("# Summary\nBug fixed.")

    date = datetime(2026, 3, 14, tzinfo=timezone.utc)
    summary = generate_daily_summary(date, journal_root=journal_root)

    assert "# Daily Summary: 2026-03-14" in summary
    assert "**Total Sessions**: 2" in summary
    assert "10h30 - Implement Auth" in summary
    assert "14h00 - Fix Bug" in summary


def test_save_daily_summary(journal_root):
    """Test saving daily summary to README.md."""
    sessions_dir = journal_root / "sessions" / "2026-03-14"
    sessions_dir.mkdir(parents=True)

    (sessions_dir / "10h00_test-session_12345678.md").write_text("# Test")

    date = datetime(2026, 3, 14, tzinfo=timezone.utc)
    output_path = save_daily_summary(date, journal_root=journal_root)

    assert output_path.exists()
    assert output_path.name == "README.md"
    assert output_path.parent == sessions_dir

    content = output_path.read_text(encoding="utf-8")
    assert "# Daily Summary: 2026-03-14" in content


def test_find_journal_root_in_parent(tmp_path):
    """Test finding .session-journal in parent directory."""
    journal = tmp_path / ".session-journal"
    journal.mkdir()

    sub_dir = tmp_path / "sub" / "nested"
    sub_dir.mkdir(parents=True)
    test_file = sub_dir / "file.txt"
    test_file.write_text("test")

    found = _find_journal_root(test_file)
    assert found == journal


def test_find_journal_root_via_env(tmp_path, monkeypatch):
    """Test CURSOR_ORG_JOURNAL_ROOT environment variable."""
    journal = tmp_path / "custom-journal"
    journal.mkdir()
    test_file = tmp_path / "file.txt"
    test_file.write_text("test")

    monkeypatch.setenv("CURSOR_ORG_JOURNAL_ROOT", str(journal))
    found = _find_journal_root(test_file)
    assert found == journal.resolve()


def test_find_journal_root_not_found(tmp_path, monkeypatch):
    """Test FileNotFoundError when no journal root exists."""
    test_file = tmp_path / "file.txt"
    test_file.write_text("test")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CURSOR_ORG_JOURNAL_ROOT", raising=False)

    with pytest.raises(FileNotFoundError):
        _find_journal_root(test_file)


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
