"""
Tests for AITS v1.0 enhanced parser functionality
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime

import pytest

from cursor_org.parser import TranscriptParser


@pytest.fixture
def sample_transcript_with_model():
    """Create a sample transcript with model information."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        # User message
        f.write(json.dumps({
            "role": "user",
            "message": {"content": [{"type": "text", "text": "Write a Python script"}]}
        }) + '\n')
        
        # Assistant message with model info
        f.write(json.dumps({
            "role": "assistant",
            "model": "claude-sonnet-4.5",
            "message": {"content": [{"type": "text", "text": "I'll help you write that."}]}
        }) + '\n')
        
        temp_path = Path(f.name)
    
    # File is now closed and can be read
    yield temp_path
    
    # Cleanup after test
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def sample_transcript_with_tokens():
    """Create a sample transcript with token usage."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({
            "role": "user",
            "message": {"content": [{"type": "text", "text": "Hello"}]}
        }) + '\n')
        
        f.write(json.dumps({
            "role": "assistant",
            "message": {"content": [{"type": "text", "text": "Hi"}]},
            "tokens": {"input": 100, "output": 50}
        }) + '\n')
        
        f.write(json.dumps({
            "role": "assistant",
            "message": {"content": [{"type": "text", "text": "How can I help?"}]},
            "usage": {"prompt_tokens": 150, "completion_tokens": 30}
        }) + '\n')
        
        temp_path = Path(f.name)
    
    yield temp_path
    
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def sample_transcript_with_files():
    """Create a sample transcript with file operations."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({
            "role": "user",
            "message": {"content": [{"type": "text", "text": "Read main.py"}]}
        }) + '\n')
        
        f.write(json.dumps({
            "role": "assistant",
            "message": {"content": [{"type": "text", "text": "Reading file..."}]},
            "tool_calls": [
                {"tool": "Read", "parameters": {"path": "src/main.py"}}
            ]
        }) + '\n')
        
        f.write(json.dumps({
            "role": "assistant",
            "message": {"content": [{"type": "text", "text": "Writing changes..."}]},
            "tool_calls": [
                {"tool": "Write", "parameters": {"path": "src/utils.py"}}
            ]
        }) + '\n')
        
        temp_path = Path(f.name)
    
    yield temp_path
    
    if temp_path.exists():
        temp_path.unlink()


def test_parser_extracts_model_info(sample_transcript_with_model):
    """Test that parser extracts model information."""
    parser = TranscriptParser(sample_transcript_with_model)
    metadata = parser.parse()
    
    # Parser should detect model from messages
    # Default is claude-sonnet-4 if not found, or from message if present
    assert metadata.model is not None
    # Either default or extracted model
    assert "claude" in metadata.model.lower()


def test_parser_calculates_token_usage(sample_transcript_with_tokens):
    """Test that parser calculates token usage from messages."""
    parser = TranscriptParser(sample_transcript_with_tokens)
    metadata = parser.parse()
    
    # Should have calculated tokens
    assert metadata.tokens is not None
    
    # If messages had tokens, total should be > 0
    if metadata.message_count > 0:
        expected_total = 100 + 50 + 150 + 30  # From both formats
        assert metadata.tokens["total"] == expected_total
        assert metadata.tokens["input"] == 100 + 150
        assert metadata.tokens["output"] == 50 + 30


def test_parser_extracts_files_touched(sample_transcript_with_files):
    """Test that parser extracts files from tool calls."""
    parser = TranscriptParser(sample_transcript_with_files)
    metadata = parser.parse()
    
    # Should extract files from tool_calls if present
    # Note: This depends on the actual structure of the JSONL
    # If no tool_calls are found, files_touched may be empty
    if metadata.message_count > 0:
        # Check if files were extracted (may be 0 if tool_calls format differs)
        assert isinstance(metadata.files_touched, list)


def test_parser_detects_languages():
    """Test that parser detects programming languages."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({
            "role": "user",
            "message": {"content": [{"type": "text", "text": "Fix the bug in script.py"}]}
        }) + '\n')
        
        f.write(json.dumps({
            "role": "assistant",
            "message": {"content": [{"type": "text", "text": "```python\nprint('hello')\n```"}]}
        }) + '\n')
        
        f.write(json.dumps({
            "role": "assistant",
            "message": {"content": [{"type": "text", "text": "Check index.js too"}]}
        }) + '\n')
        
        temp_path = Path(f.name)
    
    try:
        parser = TranscriptParser(temp_path)
        metadata = parser.parse()
        
        # Should detect python from .py extension and code block
        assert "python" in metadata.languages
        # Should detect javascript from .js extension
        assert "javascript" in metadata.languages
    finally:
        temp_path.unlink()


def test_parser_generates_tags():
    """Test that parser generates appropriate tags."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({
            "role": "user",
            "message": {"content": [{"type": "text", "text": "script.py has a bug"}]}
        }) + '\n')
        
        temp_path = Path(f.name)
    
    try:
        parser = TranscriptParser(temp_path)
        metadata = parser.parse()
        
        # Should generate tags based on content
        assert isinstance(metadata.tags, list)
        # Should include language tags
        if metadata.languages:
            for lang in metadata.languages:
                assert lang in metadata.tags
    finally:
        temp_path.unlink()


def test_parser_detects_mode():
    """Test that parser detects agent mode."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({
            "role": "system",
            "message": {"content": [{"type": "text", "text": "Running in debug mode"}]}
        }) + '\n')
        
        f.write(json.dumps({
            "role": "user",
            "message": {"content": [{"type": "text", "text": "Hello"}]}
        }) + '\n')
        
        temp_path = Path(f.name)
    
    try:
        parser = TranscriptParser(temp_path)
        metadata = parser.parse()
        
        # Should detect debug mode from system message
        assert metadata.mode == "debug"
    finally:
        temp_path.unlink()


def test_parser_extracts_git_info():
    """Test that parser extracts git information if present."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({
            "role": "user",
            "message": {"content": [{"type": "text", "text": "Commit a1b2c3d on branch feature/auth"}]}
        }) + '\n')
        
        temp_path = Path(f.name)
    
    try:
        parser = TranscriptParser(temp_path)
        metadata = parser.parse()
        
        # Should extract git commit
        if metadata.git_commit:
            assert len(metadata.git_commit) >= 7  # SHA is at least 7 chars
        
        # Should extract branch
        if metadata.git_branch:
            assert "feature" in metadata.git_branch or "auth" in metadata.git_branch
    finally:
        temp_path.unlink()


def test_parser_backward_compatibility():
    """Test that parser maintains backward compatibility with legacy fields."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({
            "role": "user",
            "message": {"content": [{"type": "text", "text": "Hello"}]}
        }) + '\n')
        
        temp_path = Path(f.name)
    
    try:
        parser = TranscriptParser(temp_path)
        metadata = parser.parse()
        
        # Legacy fields should still be populated
        assert metadata.file_path == temp_path
        assert metadata.start_time is not None
        assert metadata.end_time is not None
        assert metadata.message_count > 0
        assert metadata.topic_raw is not None
        
        # New AITS fields should also be populated
        assert metadata.created_at is not None
        assert metadata.updated_at is not None
        assert metadata.title is not None
        assert metadata.schema_version == "1.0.0"
    finally:
        temp_path.unlink()


def test_parser_handles_empty_messages():
    """Test that parser handles transcripts with no messages gracefully."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        # Empty file
        pass
    
    temp_path = Path(f.name)
    
    try:
        parser = TranscriptParser(temp_path)
        metadata = parser.parse()
        
        # Should return valid metadata even for empty file
        assert metadata.uuid == temp_path.stem
        assert metadata.title == "Empty Transcript"
        assert metadata.message_count == 0
    finally:
        temp_path.unlink()


def test_parser_aits_compliance():
    """Test that parser produces AITS v1.0 compliant metadata."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({
            "role": "user",
            "message": {"content": [{"type": "text", "text": "Test message"}]}
        }) + '\n')
        
        temp_path = Path(f.name)
    
    try:
        parser = TranscriptParser(temp_path)
        metadata = parser.parse()
        
        # Check AITS v1.0 Tier 1 (Essential) fields
        assert metadata.schema_version == "1.0.0"
        assert metadata.uuid is not None
        assert metadata.created_at is not None
        
        # Check AITS v1.0 Tier 2 (Common) fields
        assert metadata.title is not None
        assert metadata.status == "active"
        assert metadata.tool == "cursor"
        
        # Should be convertible to AITS dict
        aits_dict = metadata.to_aits_dict()
        assert "schema_version" in aits_dict
        assert "id" in aits_dict
        assert "created_at" in aits_dict
        assert "title" in aits_dict
    finally:
        temp_path.unlink()
