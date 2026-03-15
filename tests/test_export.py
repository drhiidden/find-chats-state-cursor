"""Tests for export command and exporters.

Tests the CLI export command and various export formats.
"""
import pytest
import json
from pathlib import Path
from cursor_org.exporters import (
    export_to_json, export_to_markdown, export_to_html, export_to_cjson
)
from cursor_org.models import TranscriptMetadata
from datetime import datetime, timezone


@pytest.fixture
def sample_metadata():
    """Create sample metadata for testing."""
    return TranscriptMetadata(
        schema_version="1.0.0",
        uuid="abc123-test",
        created_at=datetime(2026, 3, 14, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 14, 11, 30, 0, tzinfo=timezone.utc),
        title="Implement user authentication",
        model="claude-sonnet-4.5",
        workspace="/home/user/myproject",
        tool="cursor",
        tool_version="0.42.0",
        tags=["authentication", "backend"],
        languages=["python", "typescript"],
        files_touched=["src/auth.py", "tests/test_auth.py"],
        tokens={"input": 5000, "output": 3000, "total": 8000},
        mode="agent",
        message_count=10,
        user_messages=5,
        assistant_messages=5,
    )


@pytest.fixture
def sample_messages():
    """Create sample messages for testing."""
    return [
        {
            "role": "user",
            "timestamp": "2026-03-14T10:00:00Z",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "I need to implement JWT authentication"
                    }
                ]
            }
        },
        {
            "role": "assistant",
            "timestamp": "2026-03-14T10:00:30Z",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "I'll help you implement JWT authentication."
                    }
                ]
            }
        },
        {
            "role": "user",
            "timestamp": "2026-03-14T10:01:00Z",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Great, let's start with the token generation"
                    }
                ]
            }
        }
    ]


def test_export_to_json_basic(sample_metadata, sample_messages, tmp_path):
    """Test basic JSON export."""
    output_path = tmp_path / "export.json"
    
    export_to_json(sample_metadata, sample_messages, output_path)
    
    assert output_path.exists()
    
    # Verify JSON is valid
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert "metadata" in data
    assert "messages" in data
    assert "exported_at" in data
    assert "exporter" in data
    
    # Verify metadata
    assert data["metadata"]["id"] == "abc123-test"
    assert data["metadata"]["title"] == "Implement user authentication"
    assert data["metadata"]["tool"] == "cursor"
    
    # Verify messages preserved
    assert len(data["messages"]) == 3


def test_export_to_json_aits_compliance(sample_metadata, sample_messages, tmp_path):
    """Test JSON export AITS v1.0 compliance."""
    output_path = tmp_path / "export.json"
    
    export_to_json(sample_metadata, sample_messages, output_path)
    
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    metadata = data["metadata"]
    
    # AITS Tier 1: Essential
    assert metadata["schema_version"] == "1.0.0"
    assert metadata["id"] is not None
    assert metadata["created_at"] is not None
    assert metadata["title"] is not None
    
    # AITS Tier 2: Common
    assert metadata["tool"] == "cursor"
    assert metadata["model"] is not None
    assert metadata["workspace"] is not None
    
    # AITS Tier 3: Extended
    assert "tokens" in metadata
    assert metadata["tokens"]["total"] == 8000
    assert "tags" in metadata
    assert "languages" in metadata


def test_export_to_markdown(sample_metadata, sample_messages, tmp_path):
    """Test markdown export."""
    output_path = tmp_path / "export.md"
    
    export_to_markdown(sample_metadata, sample_messages, output_path)
    
    assert output_path.exists()
    
    content = output_path.read_text(encoding="utf-8")
    
    # Verify markdown structure
    assert "# Chat Summary: Implement user authentication" in content
    assert "## Overview" in content
    assert "## Full Conversation" in content
    
    # Verify metadata present
    assert "abc123-test" in content
    assert "claude-sonnet-4.5" in content
    
    # Verify messages present
    assert "JWT authentication" in content
    assert "I'll help you" in content


def test_export_to_html(sample_metadata, sample_messages, tmp_path):
    """Test HTML export."""
    output_path = tmp_path / "export.html"
    
    export_to_html(sample_metadata, sample_messages, output_path)
    
    assert output_path.exists()
    
    content = output_path.read_text(encoding="utf-8")
    
    # Verify HTML structure
    assert "<!DOCTYPE html>" in content
    assert "<html" in content
    assert "</html>" in content
    
    # Verify content present
    assert "Implement user authentication" in content
    assert "abc123-test" in content
    assert "JWT authentication" in content
    
    # Verify styling present
    assert "<style>" in content
    assert "background" in content


def test_export_to_cjson(sample_metadata, sample_messages, tmp_path):
    """Test CJSON export."""
    output_path = tmp_path / "export.cjson.json"
    
    export_to_cjson(sample_metadata, sample_messages, output_path)
    
    assert output_path.exists()
    
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Verify CJSON structure
    assert data["version"] == "1.0"
    assert data["standard"] == "CJSON"
    assert "session" in data
    assert "messages" in data
    
    # Verify session info
    session = data["session"]
    assert session["id"] == "abc123-test"
    assert session["title"] == "Implement user authentication"
    assert session["message_count"] == 10
    
    # Verify messages converted
    assert len(data["messages"]) == 3


def test_export_with_tool_calls(tmp_path):
    """Test export with tool calls."""
    from cursor_org.models import ToolCall
    
    metadata = TranscriptMetadata(
        uuid="tool-test",
        title="Test with tools",
        tool_calls=[
            ToolCall(
                tool="Read",
                input_data={"file_path": "src/main.py"},
                timestamp="2026-03-14T10:00:00Z"
            ),
            ToolCall(
                tool="Write",
                input_data={"file_path": "src/main.py", "content": "..."},
                timestamp="2026-03-14T10:00:30Z"
            )
        ],
        message_count=5
    )
    
    messages = [
        {"role": "user", "message": {"content": [{"type": "text", "text": "Update main.py"}]}}
    ]
    
    output_path = tmp_path / "with_tools.json"
    export_to_json(metadata, messages, output_path)
    
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Verify tool calls present
    assert "tool_calls" in data["metadata"]
    assert len(data["metadata"]["tool_calls"]) == 2
    assert data["metadata"]["tool_calls"][0]["tool"] == "Read"


def test_export_with_thinking_blocks(tmp_path):
    """Test export with thinking blocks."""
    metadata = TranscriptMetadata(
        uuid="thinking-test",
        title="Test with thinking",
        thinking_blocks=[
            "First, I need to understand the requirements...",
            "Then I'll implement the solution..."
        ],
        message_count=3
    )
    
    messages = []
    
    output_path = tmp_path / "with_thinking.json"
    export_to_json(metadata, messages, output_path)
    
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Verify thinking blocks present
    assert "thinking_blocks" in data["metadata"]
    assert len(data["metadata"]["thinking_blocks"]) == 2


def test_export_empty_messages(sample_metadata, tmp_path):
    """Test export with no messages."""
    output_path = tmp_path / "empty_messages.json"
    
    export_to_json(sample_metadata, [], output_path)
    
    assert output_path.exists()
    
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert data["messages"] == []
    assert data["metadata"]["id"] == "abc123-test"


def test_export_creates_directories(sample_metadata, sample_messages, tmp_path):
    """Test that export creates parent directories if needed."""
    output_path = tmp_path / "nested" / "dir" / "export.json"
    
    export_to_json(sample_metadata, sample_messages, output_path)
    
    assert output_path.exists()
    assert output_path.parent.exists()


def test_export_unicode_content(sample_messages, tmp_path):
    """Test export handles unicode content correctly."""
    metadata = TranscriptMetadata(
        uuid="unicode-test",
        title="Test with émojis 🚀 and 中文",
        message_count=1
    )
    
    messages = [
        {
            "role": "user",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Hello 世界 🌍 with special chars: áéíóú"
                    }
                ]
            }
        }
    ]
    
    output_path = tmp_path / "unicode.json"
    export_to_json(metadata, messages, output_path)
    
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Verify unicode preserved
    assert "🚀" in data["metadata"]["title"]
    assert "世界" in data["messages"][0]["message"]["content"][0]["text"]


def test_all_export_formats(sample_metadata, sample_messages, tmp_path):
    """Test that all export formats work without errors."""
    formats = {
        "json": export_to_json,
        "markdown": export_to_markdown,
        "html": export_to_html,
        "cjson": export_to_cjson
    }
    
    for format_name, export_func in formats.items():
        output_path = tmp_path / f"export.{format_name}"
        export_func(sample_metadata, sample_messages, output_path)
        
        assert output_path.exists(), f"{format_name} export failed"
        assert output_path.stat().st_size > 0, f"{format_name} export is empty"
