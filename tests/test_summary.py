"""Tests for summary generation module."""

import pytest
from datetime import datetime, timezone
from pathlib import Path

from cursor_org.models import TranscriptMetadata
from cursor_org.summary import (
    generate_summary,
    _extract_session_summary,
    _format_duration,
    _calculate_token_usage,
    save_summary,
)


@pytest.fixture
def basic_metadata():
    """Create basic metadata for testing."""
    return TranscriptMetadata(
        uuid="12345678-1234-1234-1234-123456789abc",
        file_path=Path("/fake/path/transcript.jsonl"),
        start_time=datetime(2026, 3, 14, 10, 30, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 3, 14, 11, 45, 0, tzinfo=timezone.utc),
        message_count=25,
        user_messages=10,
        assistant_messages=15,
        topic_raw="Implement new feature X",
    )


@pytest.fixture
def metadata_with_injected():
    """Create metadata with injected fields."""
    return TranscriptMetadata(
        uuid="87654321-4321-4321-4321-cba987654321",
        file_path=Path("/fake/path/transcript.jsonl"),
        start_time=datetime(2026, 3, 14, 14, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 3, 14, 14, 30, 0, tzinfo=timezone.utc),
        message_count=12,
        user_messages=5,
        assistant_messages=7,
        topic_raw="Debug authentication issue",
        injected_role="Senior Developer",
        injected_goal="Fix login bug in production",
        injected_status="COMPLETED",
        injected_files=["src/auth.py", "tests/test_auth.py"],
    )


@pytest.fixture
def messages_with_session_summary():
    """Messages containing a <session_summary> block."""
    return [
        {
            "role": "user",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Let's work on feature X\n\n<session_summary>\nSTATUS: COMPLETED\nWe successfully implemented feature X with full test coverage.\nNo blockers encountered.\n</session_summary>",
                    }
                ]
            },
        }
    ]


@pytest.fixture
def messages_without_summary():
    """Messages without session_summary."""
    return [
        {"role": "user", "message": {"content": [{"type": "text", "text": "Hello"}]}},
        {
            "role": "assistant",
            "message": {"content": [{"type": "text", "text": "Hi there!"}]},
        },
    ]


def test_generate_basic_summary(basic_metadata):
    """Test generating a basic summary without injected session_summary."""
    summary = generate_summary(basic_metadata, messages=None)

    assert "# Chat Summary:" in summary
    assert "Implement new feature X" in summary
    assert "12345678-1234-1234-1234-123456789abc" in summary
    assert "2026-03-14 10:30" in summary
    assert "Duration" in summary
    assert "**Messages**: 25" in summary
    assert "User: 10" in summary
    assert "Assistant: 15" in summary
    assert "_Generated automatically by cursor-org_" in summary


def test_generate_summary_with_injected_metadata(metadata_with_injected):
    """Test summary generation with injected metadata."""
    summary = generate_summary(metadata_with_injected, messages=None)

    assert "Debug authentication issue" in summary
    assert "Role**: Senior Developer" in summary
    assert "Goal**: Fix login bug in production" in summary
    assert "Status**: COMPLETED" in summary
    assert "src/auth.py" in summary
    assert "tests/test_auth.py" in summary


def test_generate_summary_with_session_summary_block(
    basic_metadata, messages_with_session_summary
):
    """Test that <session_summary> blocks are extracted and used."""
    summary = generate_summary(basic_metadata, messages_with_session_summary)

    assert "## Session Summary" in summary
    assert "STATUS: COMPLETED" in summary
    assert "successfully implemented feature X" in summary


def test_extract_session_summary_found(messages_with_session_summary):
    """Test extracting <session_summary> when present."""
    result = _extract_session_summary(messages_with_session_summary)

    assert result is not None
    assert "STATUS: COMPLETED" in result
    assert "successfully implemented feature X" in result


def test_extract_session_summary_not_found(messages_without_summary):
    """Test extracting <session_summary> when not present."""
    result = _extract_session_summary(messages_without_summary)
    assert result is None


def test_format_duration():
    """Test duration formatting helper."""
    assert _format_duration(30) == "30s"
    assert _format_duration(90) == "1m"
    assert _format_duration(3600) == "1h"
    assert _format_duration(3660) == "1h 1m"
    assert _format_duration(7200) == "2h"


def test_save_summary(tmp_path, basic_metadata):
    """Test saving summary to file."""
    summary_content = generate_summary(basic_metadata)
    output_path = tmp_path / "test_folder" / "summary.md"

    save_summary(summary_content, output_path)

    assert output_path.exists()
    saved_content = output_path.read_text(encoding="utf-8")
    assert saved_content == summary_content
    assert "# Chat Summary:" in saved_content


def test_generate_summary_empty_metadata():
    """Test summary generation with minimal metadata."""
    minimal_metadata = TranscriptMetadata(
        uuid="minimal-uuid",
        file_path=Path("/fake/minimal.jsonl"),
        start_time=datetime(2026, 3, 14, 10, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 3, 14, 10, 5, 0, tzinfo=timezone.utc),
    )

    summary = generate_summary(minimal_metadata)

    assert "minimal-uuid" in summary
    assert "Unknown Topic" in summary
    assert "**Messages**: 0" in summary


def test_calculate_token_usage_with_tokens():
    """Test calculating token usage from messages."""
    messages = [
        {"role": "user", "tokenUsage": {"input": 100, "output": 0}},
        {"role": "assistant", "tokenUsage": {"input": 50, "output": 200}},
        {"role": "user", "tokenUsage": {"input": 75, "output": 0}},
    ]

    result = _calculate_token_usage(messages)

    assert result["input"] == 225  # 100 + 50 + 75
    assert result["output"] == 200
    assert result["total"] == 425


def test_calculate_token_usage_without_tokens():
    """Test calculating token usage when no tokenUsage field exists."""
    messages = [
        {"role": "user", "message": {"content": [{"type": "text", "text": "Hello"}]}},
        {"role": "assistant", "message": {"content": [{"type": "text", "text": "Hi"}]}},
    ]

    result = _calculate_token_usage(messages)

    assert result["input"] == 0
    assert result["output"] == 0
    assert result["total"] == 0


def test_generate_summary_with_token_usage(basic_metadata):
    """Test that token usage is included in summary when messages have tokenUsage."""
    messages_with_tokens = [
        {"role": "user", "tokenUsage": {"input": 100, "output": 0}},
        {"role": "assistant", "tokenUsage": {"input": 50, "output": 200}},
    ]

    summary = generate_summary(basic_metadata, messages=messages_with_tokens)

    assert "**Tokens**:" in summary
    assert "350" in summary  # Total tokens (150 input + 200 output)
    assert "150 input" in summary
    assert "200 output" in summary


def test_generate_summary_without_token_usage(basic_metadata):
    """Test that summary works fine without token usage."""
    messages_without_tokens = [
        {"role": "user", "message": {"content": [{"type": "text", "text": "Hello"}]}},
    ]

    summary = generate_summary(basic_metadata, messages=messages_without_tokens)

    # Should not have Tokens line when no tokens available
    assert "**Tokens**:" not in summary
    assert "# Chat Summary:" in summary
