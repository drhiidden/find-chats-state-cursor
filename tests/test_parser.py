import pytest
import json
from cursor_org.parser import TranscriptParser


@pytest.fixture
def sample_jsonl(tmp_path):
    """Creates a temporary .jsonl file with sample data."""
    file_path = tmp_path / "test_chat.jsonl"
    messages = [
        {
            "role": "user",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Start Session\n<session_metadata>\nROLE: Architect\nGOAL: Fix bug in parser\n</session_metadata>",
                    }
                ]
            },
        },
        {
            "role": "assistant",
            "message": {"content": [{"type": "text", "text": "Okay, I'm ready."}]},
        },
        {
            "role": "user",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Wrap up\n<session_summary>\nSTATUS: COMPLETED\nFILES_MODIFIED:\n- src/parser.py\n- tests/test_parser.py\n</session_summary>",
                    }
                ]
            },
        },
    ]

    with open(file_path, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    return file_path


def test_parser_basic_stats(sample_jsonl):
    parser = TranscriptParser(sample_jsonl)
    meta = parser.parse()

    assert meta.message_count == 3
    assert meta.user_messages == 2
    assert meta.assistant_messages == 1
    assert meta.uuid == "test_chat"


def test_parser_injected_metadata(sample_jsonl):
    parser = TranscriptParser(sample_jsonl)
    meta = parser.parse()

    assert meta.injected_role == "Architect"
    assert meta.injected_goal == "Fix bug in parser"
    assert meta.injected_status == "COMPLETED"
    assert "src/parser.py" in meta.injected_files
    assert len(meta.injected_files) == 2


def test_topic_slug_generation(sample_jsonl):
    parser = TranscriptParser(sample_jsonl)
    meta = parser.parse()

    # Topic should come from injected goal because it exists
    assert meta.topic_raw == "Fix bug in parser"
    assert meta.topic_slug == "fix-bug-in-parser"


def test_parser_fallback_topic(tmp_path):
    """Test fallback when no metadata is injected."""
    file_path = tmp_path / "fallback.jsonl"
    messages = [
        {
            "role": "user",
            "message": {
                "content": [{"type": "text", "text": "Hello, how do I install Python?"}]
            },
        }
    ]
    with open(file_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    parser = TranscriptParser(file_path)
    meta = parser.parse()

    assert "how do I install Python" in meta.topic_raw
    assert meta.topic_slug == "hello-how-do-i-install-python"


def test_parser_tool_calls_extraction(tmp_path):
    """Test extraction of tool calls from messages."""
    file_path = tmp_path / "tools.jsonl"
    messages = [
        {
            "role": "user",
            "message": {"content": [{"type": "text", "text": "Read file.py"}]},
        },
        {
            "role": "assistant",
            "toolUses": [
                {
                    "tool": "Read",
                    "input": {"path": "file.py"},
                    "output": "File content here",
                }
            ],
            "message": {"content": [{"type": "text", "text": "I've read the file"}]},
        },
    ]
    with open(file_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    parser = TranscriptParser(file_path)
    meta = parser.parse()

    assert len(meta.tool_calls) == 1
    assert meta.tool_calls[0].tool == "Read"
    assert meta.tool_calls[0].input_data.get("path") == "file.py"


def test_parser_token_extraction(tmp_path):
    """Test extraction of token usage."""
    file_path = tmp_path / "tokens.jsonl"
    messages = [
        {
            "role": "user",
            "message": {"content": [{"type": "text", "text": "Hello"}]},
            "tokenUsage": {"input": 100, "output": 50},
        },
        {
            "role": "assistant",
            "message": {"content": [{"type": "text", "text": "Hi"}]},
            "tokenUsage": {"input": 50, "output": 200},
        },
    ]
    with open(file_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    parser = TranscriptParser(file_path)
    meta = parser.parse()

    assert meta.tokens is not None
    assert meta.tokens["input"] == 150
    assert meta.tokens["output"] == 250
    assert meta.tokens["total"] == 400


def test_parser_thinking_blocks(tmp_path):
    """Test extraction of thinking blocks."""
    file_path = tmp_path / "thinking.jsonl"
    messages = [
        {
            "role": "assistant",
            "message": {"content": [{"type": "text", "text": "Let me think..."}]},
            "thinking": {
                "blocks": [
                    {"content": "First, I need to analyze..."},
                    {"content": "Then, I should consider..."},
                ]
            },
        }
    ]
    with open(file_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    parser = TranscriptParser(file_path)
    meta = parser.parse()

    assert len(meta.thinking_blocks) == 2
    assert "First, I need to analyze" in meta.thinking_blocks[0]
    assert "Then, I should consider" in meta.thinking_blocks[1]


def test_parser_aits_export(sample_jsonl):
    """Test AITS v1.0 export format."""
    parser = TranscriptParser(sample_jsonl)
    meta = parser.parse()

    aits_dict = meta.to_aits_dict()

    assert "schema_version" in aits_dict
    assert aits_dict["schema_version"] == "1.0.0"
    assert "id" in aits_dict
    assert "created_at" in aits_dict
    assert "title" in aits_dict
