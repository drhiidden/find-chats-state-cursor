"""Tests for Claude Code parser.

Tests the ClaudeCodeParser with mock data simulating Claude Code's JSONL format.
"""
import pytest
import json
from pathlib import Path
from cursor_org.parsers import get_parser, auto_detect_ide
from cursor_org.parsers.claude_code_parser import ClaudeCodeParser


@pytest.fixture
def sample_claude_code_jsonl(tmp_path):
    """Creates a temporary Claude Code format .jsonl file with sample data."""
    file_path = tmp_path / "abc123-session.jsonl"
    
    records = [
        # System message (first record in session)
        {
            "type": "system",
            "uuid": "sys-001",
            "timestamp": "2026-03-14T10:00:00.000Z",
            "sessionId": "abc123",
            "cwd": "/home/user/myproject",
            "message": {
                "role": "system",
                "content": "You are Claude Code, an AI coding assistant..."
            }
        },
        # User message
        {
            "type": "user",
            "uuid": "user-001",
            "parentUuid": "sys-001",
            "timestamp": "2026-03-14T10:00:15.000Z",
            "sessionId": "abc123",
            "cwd": "/home/user/myproject",
            "message": {
                "role": "user",
                "content": "Add input validation to the createUser endpoint"
            }
        },
        # Assistant message with thinking and tool use
        {
            "type": "assistant",
            "uuid": "asst-001",
            "parentUuid": "user-001",
            "timestamp": "2026-03-14T10:00:45.000Z",
            "sessionId": "abc123",
            "cwd": "/home/user/myproject",
            "message": {
                "role": "assistant",
                "model": "claude-opus-4-5-20251101",
                "content": [
                    {
                        "type": "thinking",
                        "thinking": "The user wants validation on createUser. I should check what validation library they use..."
                    },
                    {
                        "type": "text",
                        "text": "I'll add input validation using zod schemas."
                    },
                    {
                        "type": "tool_use",
                        "id": "toolu_01abc",
                        "name": "Read",
                        "input": {
                            "file_path": "/home/user/myproject/src/routes/users.ts"
                        }
                    }
                ],
                "usage": {
                    "input_tokens": 1200,
                    "output_tokens": 350,
                    "cache_read_input_tokens": 800
                }
            }
        },
        # Tool result
        {
            "type": "tool_result",
            "uuid": "tool-res-001",
            "parentUuid": "asst-001",
            "timestamp": "2026-03-14T10:00:46.000Z",
            "toolUseResult": {
                "tool_use_id": "toolu_01abc",
                "content": "export const createUser = async (req, res) => {\n  // No validation yet\n}",
                "is_error": False
            }
        },
        # Another assistant message with file write
        {
            "type": "assistant",
            "uuid": "asst-002",
            "parentUuid": "tool-res-001",
            "timestamp": "2026-03-14T10:01:00.000Z",
            "sessionId": "abc123",
            "message": {
                "role": "assistant",
                "model": "claude-opus-4-5-20251101",
                "content": [
                    {
                        "type": "text",
                        "text": "Here's the updated code with validation:"
                    },
                    {
                        "type": "tool_use",
                        "id": "toolu_02def",
                        "name": "Write",
                        "input": {
                            "file_path": "/home/user/myproject/src/routes/users.ts",
                            "content": "import { z } from 'zod';\n\nconst createUserSchema = z.object({...});"
                        }
                    }
                ],
                "usage": {
                    "input_tokens": 1500,
                    "output_tokens": 420,
                    "cache_read_input_tokens": 1000
                }
            }
        }
    ]
    
    with open(file_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")
    
    return file_path


@pytest.fixture
def claude_code_session_with_subagent(tmp_path):
    """Creates Claude Code session with subagent spawn."""
    file_path = tmp_path / "team-session.jsonl"
    
    records = [
        {
            "type": "system",
            "uuid": "sys-001",
            "timestamp": "2026-03-14T11:00:00.000Z",
            "sessionId": "team-123",
            "message": {"role": "system", "content": "System prompt"}
        },
        {
            "type": "user",
            "uuid": "user-001",
            "parentUuid": "sys-001",
            "timestamp": "2026-03-14T11:00:15.000Z",
            "message": {"role": "user", "content": "Search for all auth middleware"}
        },
        {
            "type": "assistant",
            "uuid": "asst-001",
            "parentUuid": "user-001",
            "timestamp": "2026-03-14T11:00:30.000Z",
            "message": {
                "role": "assistant",
                "model": "claude-opus-4-5-20251101",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_spawn_01",
                        "name": "Task",
                        "input": {
                            "subagent_type": "Explore",
                            "description": "Find auth middleware",
                            "prompt": "Search for JWT validation..."
                        }
                    }
                ],
                "usage": {
                    "input_tokens": 500,
                    "output_tokens": 100
                }
            }
        }
    ]
    
    with open(file_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")
    
    return file_path


def test_claude_code_parser_basic_metadata(sample_claude_code_jsonl):
    """Test basic metadata extraction from Claude Code format."""
    parser = ClaudeCodeParser(sample_claude_code_jsonl)
    meta = parser.parse()
    
    assert meta.tool == "claude"
    assert meta.uuid == "abc123-session"
    assert meta.message_count == 5
    assert meta.user_messages == 1
    assert meta.assistant_messages == 2


def test_claude_code_parser_title_extraction(sample_claude_code_jsonl):
    """Test title extraction from first user message."""
    parser = ClaudeCodeParser(sample_claude_code_jsonl)
    meta = parser.parse()
    
    assert meta.title == "Add input validation to the createUser endpoint"
    assert meta.topic_raw == "Add input validation to the createUser endpoint"


def test_claude_code_parser_timestamps(sample_claude_code_jsonl):
    """Test timestamp parsing from ISO8601 format."""
    parser = ClaudeCodeParser(sample_claude_code_jsonl)
    meta = parser.parse()
    
    # Should extract timestamps from records (more accurate than filesystem)
    assert meta.created_at is not None
    assert meta.updated_at is not None
    assert meta.created_at < meta.updated_at


def test_claude_code_parser_model_info(sample_claude_code_jsonl):
    """Test model extraction from assistant messages."""
    parser = ClaudeCodeParser(sample_claude_code_jsonl)
    meta = parser.parse()
    
    assert meta.model == "claude-opus-4-5-20251101"


def test_claude_code_parser_token_usage(sample_claude_code_jsonl):
    """Test token usage calculation."""
    parser = ClaudeCodeParser(sample_claude_code_jsonl)
    meta = parser.parse()
    
    # Should sum up all assistant messages' tokens
    # asst-001: 1200 + 800 (cache) = 2000 input, 350 output
    # asst-002: 1500 + 1000 (cache) = 2500 input, 420 output
    # Total: 4500 input, 770 output
    assert meta.tokens["input"] == 4500
    assert meta.tokens["output"] == 770
    assert meta.tokens["total"] == 5270


def test_claude_code_parser_workspace_extraction(sample_claude_code_jsonl):
    """Test workspace extraction from cwd field."""
    parser = ClaudeCodeParser(sample_claude_code_jsonl)
    meta = parser.parse()
    
    assert meta.workspace == "/home/user/myproject"


def test_claude_code_parser_tool_calls(sample_claude_code_jsonl):
    """Test tool call extraction."""
    parser = ClaudeCodeParser(sample_claude_code_jsonl)
    meta = parser.parse()
    
    assert len(meta.tool_calls) == 2
    assert meta.tool_calls[0].tool == "Read"
    assert meta.tool_calls[0].input_data["file_path"] == "/home/user/myproject/src/routes/users.ts"
    assert meta.tool_calls[1].tool == "Write"


def test_claude_code_parser_thinking_blocks(sample_claude_code_jsonl):
    """Test extended thinking extraction."""
    parser = ClaudeCodeParser(sample_claude_code_jsonl)
    meta = parser.parse()
    
    assert len(meta.thinking_blocks) == 1
    assert "validation library" in meta.thinking_blocks[0]


def test_claude_code_parser_files_touched(sample_claude_code_jsonl):
    """Test file path extraction from tool calls."""
    parser = ClaudeCodeParser(sample_claude_code_jsonl)
    meta = parser.parse()
    
    assert len(meta.files_touched) == 1
    assert "/home/user/myproject/src/routes/users.ts" in meta.files_touched


def test_claude_code_parser_languages(sample_claude_code_jsonl):
    """Test language detection from file extensions."""
    parser = ClaudeCodeParser(sample_claude_code_jsonl)
    meta = parser.parse()
    
    # Should detect typescript from .ts files
    assert "typescript" in meta.languages


def test_claude_code_parser_subagents(claude_code_session_with_subagent):
    """Test subagent counting from Task tool calls."""
    parser = ClaudeCodeParser(claude_code_session_with_subagent)
    meta = parser.parse()
    
    assert meta.subagents_spawned == 1


def test_claude_code_parser_aits_compliance(sample_claude_code_jsonl):
    """Test AITS v1.0 compliance."""
    parser = ClaudeCodeParser(sample_claude_code_jsonl)
    meta = parser.parse()
    
    aits_dict = meta.to_aits_dict()
    
    # AITS Tier 1: Essential
    assert aits_dict["schema_version"] == "1.0.0"
    assert aits_dict["id"] == "abc123-session"
    assert aits_dict["created_at"] is not None
    assert aits_dict["title"] is not None
    
    # AITS Tier 2: Common
    assert aits_dict["tool"] == "claude"
    assert aits_dict["model"] == "claude-opus-4-5-20251101"
    assert aits_dict["workspace"] == "/home/user/myproject"
    
    # AITS Tier 3: Extended
    assert "tokens" in aits_dict
    assert aits_dict["tokens"]["total"] == 5270


def test_claude_code_parser_empty_file(tmp_path):
    """Test handling of empty JSONL file."""
    file_path = tmp_path / "empty.jsonl"
    file_path.write_text("", encoding="utf-8")
    
    parser = ClaudeCodeParser(file_path)
    meta = parser.parse()
    
    assert meta.title == "Empty Transcript"
    assert meta.message_count == 0


def test_claude_code_auto_detection(tmp_path):
    """Test IDE auto-detection for Claude Code paths."""
    # Create Claude Code path structure
    claude_path = tmp_path / ".claude" / "projects" / "test" / "sessions"
    claude_path.mkdir(parents=True)
    
    file_path = claude_path / "session-123.jsonl"
    file_path.write_text('{"type":"user","message":{"content":"test"}}\n', encoding="utf-8")
    
    detected_ide = auto_detect_ide(file_path)
    assert detected_ide == "claude"


def test_claude_code_parser_malformed_json(tmp_path):
    """Test handling of malformed JSON lines."""
    file_path = tmp_path / "malformed.jsonl"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('{"type":"user","message":{"content":"valid"}}\n')
        f.write('{"broken json without closing brace\n')  # Malformed
        f.write('{"type":"assistant","message":{"content":"also valid"}}\n')
    
    parser = ClaudeCodeParser(file_path)
    meta = parser.parse()
    
    # Should parse valid records and skip malformed ones
    assert meta.message_count == 2


def test_get_parser_claude_code(sample_claude_code_jsonl):
    """Test parser factory returns correct parser for claude."""
    parser = get_parser("claude", sample_claude_code_jsonl)
    assert isinstance(parser, ClaudeCodeParser)
    
    meta = parser.parse()
    assert meta.tool == "claude"


def test_claude_code_suggested_dirname(sample_claude_code_jsonl):
    """Test suggested directory name generation."""
    parser = ClaudeCodeParser(sample_claude_code_jsonl)
    meta = parser.parse()
    
    # Format: YYYY-MM-DD_HHhMM_topic-slug_uuid-short
    dirname = meta.suggested_dirname
    
    assert "2026-03-14" in dirname
    assert "10h00" in dirname
    assert "add-input-validation" in dirname
    assert meta.uuid_short in dirname
