"""Tests for statistics generation module."""

import pytest
import json
from pathlib import Path
from datetime import datetime, timezone

from cursor_org.stats import (
    calculate_statistics,
    get_top_topics,
    _extract_token_usage,
    _format_duration,
)


@pytest.fixture
def sample_transcript_dir(tmp_path):
    """Create a temporary directory with sample transcript files."""
    # Create first transcript
    transcript1_dir = tmp_path / "2026-03-14_10h30_fix-auth-bug_abc12345"
    transcript1_dir.mkdir()
    transcript1_file = transcript1_dir / "abc12345-1234-1234-1234-123456789abc.jsonl"

    messages1 = [
        {
            "role": "user",
            "message": {"content": [{"type": "text", "text": "Fix the authentication bug"}]},
            "tokenUsage": {"input": 100, "output": 0},
        },
        {
            "role": "assistant",
            "message": {"content": [{"type": "text", "text": "I'll help you with that"}]},
            "tokenUsage": {"input": 50, "output": 150},
        },
        {
            "role": "user",
            "message": {"content": [{"type": "text", "text": "Great, let's start"}]},
            "tokenUsage": {"input": 80, "output": 0},
        },
    ]

    with open(transcript1_file, "w", encoding="utf-8") as f:
        for msg in messages1:
            f.write(json.dumps(msg) + "\n")

    # Create second transcript
    transcript2_dir = tmp_path / "2026-03-14_14h00_implement-new-feature_def45678"
    transcript2_dir.mkdir()
    transcript2_file = transcript2_dir / "def45678-5678-5678-5678-567890abcdef.jsonl"

    messages2 = [
        {
            "role": "user",
            "message": {"content": [{"type": "text", "text": "Implement new feature X"}]},
            "tokenUsage": {"input": 120, "output": 0},
        },
        {
            "role": "assistant",
            "message": {"content": [{"type": "text", "text": "Sure thing"}]},
            "tokenUsage": {"input": 60, "output": 200},
        },
    ]

    with open(transcript2_file, "w", encoding="utf-8") as f:
        for msg in messages2:
            f.write(json.dumps(msg) + "\n")

    return tmp_path


@pytest.fixture
def empty_transcript_dir(tmp_path):
    """Create an empty directory."""
    return tmp_path


def test_calculate_statistics_basic(sample_transcript_dir):
    """Test basic statistics calculation."""
    stats = calculate_statistics(sample_transcript_dir)

    assert stats["total_sessions"] == 2
    assert stats["total_messages"] == 5  # 3 + 2
    assert stats["user_messages"] == 3  # 2 + 1
    assert stats["assistant_messages"] == 2  # 1 + 1


def test_calculate_statistics_token_usage(sample_transcript_dir):
    """Test token usage calculation."""
    stats = calculate_statistics(sample_transcript_dir)

    # Total input: 100 + 50 + 80 + 120 + 60 = 410
    # Total output: 150 + 200 = 350
    assert stats["token_usage"]["input"] == 410
    assert stats["token_usage"]["output"] == 350
    assert stats["token_usage"]["total"] == 760


def test_calculate_statistics_duration(sample_transcript_dir):
    """Test duration calculation."""
    stats = calculate_statistics(sample_transcript_dir)

    # Should have some duration (based on file timestamps)
    assert stats["total_duration_seconds"] >= 0


def test_calculate_statistics_topics(sample_transcript_dir):
    """Test topic extraction."""
    stats = calculate_statistics(sample_transcript_dir)

    assert len(stats["topics"]) == 2
    # Topics should contain text from first user messages
    topics_text = " ".join(stats["topics"])
    assert "authentication" in topics_text or "feature" in topics_text


def test_calculate_statistics_activity_by_day(sample_transcript_dir):
    """Test activity by day calculation."""
    stats = calculate_statistics(sample_transcript_dir)

    # Should have at least one day with activity
    assert len(stats["activity_by_day"]) > 0
    # All sessions should be counted
    total_sessions = sum(stats["activity_by_day"].values())
    assert total_sessions == 2


def test_calculate_statistics_empty_directory(empty_transcript_dir):
    """Test statistics on empty directory."""
    stats = calculate_statistics(empty_transcript_dir)

    assert stats["total_sessions"] == 0
    assert stats["total_messages"] == 0
    assert stats["user_messages"] == 0
    assert stats["assistant_messages"] == 0
    assert stats["token_usage"]["total"] == 0
    assert len(stats["topics"]) == 0
    assert len(stats["activity_by_day"]) == 0


def test_extract_token_usage_with_tokens():
    """Test extracting token usage from messages."""
    messages = [
        {"role": "user", "tokenUsage": {"input": 100, "output": 0}},
        {"role": "assistant", "tokenUsage": {"input": 50, "output": 200}},
        {"role": "user", "tokenUsage": {"input": 75, "output": 0}},
    ]

    result = _extract_token_usage(messages)

    assert result["input"] == 225  # 100 + 50 + 75
    assert result["output"] == 200
    assert result["total"] == 425


def test_extract_token_usage_without_tokens():
    """Test extracting token usage when no tokenUsage field exists."""
    messages = [
        {"role": "user", "message": {"content": [{"type": "text", "text": "Hello"}]}},
        {"role": "assistant", "message": {"content": [{"type": "text", "text": "Hi"}]}},
    ]

    result = _extract_token_usage(messages)

    assert result["input"] == 0
    assert result["output"] == 0
    assert result["total"] == 0


def test_get_top_topics():
    """Test getting top N topics."""
    topics = [
        "Fix authentication bug",
        "Implement feature X",
        "Fix authentication bug",
        "Debug issue Y",
        "Fix authentication bug",
        "Implement feature X",
    ]

    top_topics = get_top_topics(topics, n=3)

    assert len(top_topics) == 3
    # Most frequent should be "Fix authentication bug" (3 times)
    assert top_topics[0][0] == "Fix authentication bug"
    assert top_topics[0][1] == 3
    # Second most frequent should be "Implement feature X" (2 times)
    assert top_topics[1][0] == "Implement feature X"
    assert top_topics[1][1] == 2


def test_get_top_topics_with_truncation():
    """Test topic truncation to 60 chars."""
    long_topic = "A" * 100  # 100 character topic

    topics = [long_topic, long_topic, "Short topic"]

    top_topics = get_top_topics(topics, n=2)

    # Long topic should be truncated to 60 chars
    assert len(top_topics[0][0]) == 60
    assert top_topics[0][1] == 2  # Should appear twice


def test_format_duration():
    """Test duration formatting."""
    assert _format_duration(30) == "30s"
    assert _format_duration(90) == "1m"
    assert _format_duration(3600) == "1h"
    assert _format_duration(3660) == "1h 1m"
    assert _format_duration(7200) == "2h"
    assert _format_duration(7260) == "2h 1m"
