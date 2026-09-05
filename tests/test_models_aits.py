"""
Tests for AITS v1.0 compliant TranscriptMetadata model
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from cursor_org.models import TranscriptMetadata


def test_metadata_aits_fields():
    """Test that TranscriptMetadata has all AITS v1.0 required fields."""
    metadata = TranscriptMetadata(
        uuid="550e8400-e29b-41d4-a716-446655440000",
        created_at=datetime.now(timezone.utc),
        title="Test Transcript"
    )
    
    # Tier 1: Essential
    assert hasattr(metadata, 'schema_version')
    assert hasattr(metadata, 'uuid')
    assert hasattr(metadata, 'created_at')
    
    # Tier 2: Common
    assert hasattr(metadata, 'title')
    assert hasattr(metadata, 'updated_at')
    assert hasattr(metadata, 'model')
    assert hasattr(metadata, 'workspace')
    assert hasattr(metadata, 'status')
    assert hasattr(metadata, 'tool')
    assert hasattr(metadata, 'tool_version')
    
    # Tier 3: Extended
    assert hasattr(metadata, 'tags')
    assert hasattr(metadata, 'languages')
    assert hasattr(metadata, 'files_touched')
    assert hasattr(metadata, 'cost')
    assert hasattr(metadata, 'tokens')
    assert hasattr(metadata, 'git_commit')
    assert hasattr(metadata, 'git_branch')
    assert hasattr(metadata, 'mode')
    assert hasattr(metadata, 'outcome')


def test_metadata_default_values():
    """Test default values for AITS fields."""
    metadata = TranscriptMetadata(
        uuid="test-uuid",
        created_at=datetime.now(timezone.utc),
        title="Test"
    )
    
    assert metadata.schema_version == "1.0.0"
    assert metadata.status == "active"
    assert metadata.tool == "cursor"
    assert metadata.tags == []
    assert metadata.languages == []
    assert metadata.files_touched == []
    assert isinstance(metadata.tokens, dict)
    assert metadata.tokens["total"] == 0


def test_metadata_backward_compatibility():
    """Test that legacy fields are synchronized with AITS fields."""
    now = datetime.now(timezone.utc)
    
    # Create with legacy fields
    metadata = TranscriptMetadata(
        uuid="test-uuid",
        start_time=now,
        topic_raw="My Topic"
    )
    
    # AITS fields should be synchronized
    assert metadata.created_at == now
    assert metadata.title == "My Topic"


def test_metadata_to_aits_dict():
    """Test conversion to AITS v1.0 compliant dictionary."""
    now = datetime.now(timezone.utc)
    metadata = TranscriptMetadata(
        uuid="550e8400-e29b-41d4-a716-446655440000",
        created_at=now,
        updated_at=now,
        title="Test Transcript",
        model="claude-sonnet-4.5",
        tags=["python", "bug-fix"],
        languages=["python", "javascript"],
        tokens={"input": 1000, "output": 500, "total": 1500}
    )
    
    aits_dict = metadata.to_aits_dict()
    
    # Check required fields
    assert aits_dict["schema_version"] == "1.0.0"
    assert aits_dict["id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert aits_dict["title"] == "Test Transcript"
    assert "created_at" in aits_dict
    
    # Check optional fields are included
    assert aits_dict["model"] == "claude-sonnet-4.5"
    assert aits_dict["tags"] == ["python", "bug-fix"]
    assert aits_dict["languages"] == ["python", "javascript"]
    assert aits_dict["tokens"] == {"input": 1000, "output": 500, "total": 1500}


def test_metadata_to_aits_dict_omits_empty():
    """Test that to_aits_dict omits empty optional fields."""
    metadata = TranscriptMetadata(
        uuid="test-uuid",
        created_at=datetime.now(timezone.utc),
        title="Test"
    )
    
    aits_dict = metadata.to_aits_dict()
    
    # Empty lists/None values should not be in dict
    assert "git_commit" not in aits_dict
    assert "git_branch" not in aits_dict
    assert "parent_id" not in aits_dict
    
    # Empty tags list should not be included
    if "tags" in aits_dict:
        assert len(aits_dict["tags"]) > 0


def test_metadata_tokens_initialization():
    """Test that tokens field is properly initialized."""
    metadata = TranscriptMetadata(
        uuid="test-uuid",
        created_at=datetime.now(timezone.utc),
        title="Test"
    )
    
    # Should have tokens dict with zeros
    assert metadata.tokens is not None
    assert "input" in metadata.tokens
    assert "output" in metadata.tokens
    assert "total" in metadata.tokens
    assert metadata.tokens["input"] == 0
    assert metadata.tokens["output"] == 0
    assert metadata.tokens["total"] == 0


def test_metadata_with_git_info():
    """Test metadata with git information."""
    metadata = TranscriptMetadata(
        uuid="test-uuid",
        created_at=datetime.now(timezone.utc),
        title="Test",
        git_commit="a1b2c3d4e5f6",
        git_branch="feature/new-feature"
    )
    
    assert metadata.git_commit == "a1b2c3d4e5f6"
    assert metadata.git_branch == "feature/new-feature"
    
    aits_dict = metadata.to_aits_dict()
    assert aits_dict["git_commit"] == "a1b2c3d4e5f6"
    assert aits_dict["git_branch"] == "feature/new-feature"


def test_metadata_with_cost():
    """Test metadata with cost information."""
    metadata = TranscriptMetadata(
        uuid="test-uuid",
        created_at=datetime.now(timezone.utc),
        title="Test",
        cost=2.45
    )
    
    assert metadata.cost == 2.45
    
    aits_dict = metadata.to_aits_dict()
    assert aits_dict["cost"] == 2.45


def test_metadata_with_mode():
    """Test metadata with agent mode."""
    metadata = TranscriptMetadata(
        uuid="test-uuid",
        created_at=datetime.now(timezone.utc),
        title="Test",
        mode="debug"
    )
    
    assert metadata.mode == "debug"
    
    aits_dict = metadata.to_aits_dict()
    assert aits_dict["mode"] == "debug"


def test_metadata_with_outcome():
    """Test metadata with outcome information."""
    metadata = TranscriptMetadata(
        uuid="test-uuid",
        created_at=datetime.now(timezone.utc),
        title="Test",
        outcome="success"
    )
    
    assert metadata.outcome == "success"
    
    aits_dict = metadata.to_aits_dict()
    assert aits_dict["outcome"] == "success"


def test_topic_slug_with_aits_title():
    """Test that topic_slug works with AITS title field."""
    metadata = TranscriptMetadata(
        uuid="test-uuid",
        created_at=datetime.now(timezone.utc),
        title="Fix Bug in Authentication Module"
    )
    
    slug = metadata.topic_slug
    assert slug == "fix-bug-in-authentication-module"


def test_suggested_dirname_with_aits_fields():
    """Test suggested_dirname works with AITS created_at."""
    dt = datetime(2026, 3, 14, 15, 30, 0, tzinfo=timezone.utc)
    
    metadata = TranscriptMetadata(
        uuid="550e8400-e29b-41d4-a716-446655440000",
        created_at=dt,
        title="Test Transcript"
    )
    
    dirname = metadata.suggested_dirname
    
    assert dirname.startswith("2026-03-14_15h30")
    assert "test-transcript" in dirname
    assert "550e8400" in dirname


def test_uuid_short():
    """Test uuid_short property."""
    metadata = TranscriptMetadata(
        uuid="550e8400-e29b-41d4-a716-446655440000",
        created_at=datetime.now(timezone.utc),
        title="Test"
    )
    
    assert metadata.uuid_short == "550e8400"


def test_metadata_with_workspace_path():
    """Test metadata with workspace path."""
    workspace = Path("/home/user/project")
    
    metadata = TranscriptMetadata(
        uuid="test-uuid",
        created_at=datetime.now(timezone.utc),
        title="Test",
        workspace=workspace
    )
    
    assert metadata.workspace == workspace
    
    aits_dict = metadata.to_aits_dict()
    assert aits_dict["workspace"] == str(workspace)


def test_metadata_with_files_touched():
    """Test metadata with files_touched list."""
    files = ["src/main.py", "src/utils.py", "tests/test_main.py"]
    
    metadata = TranscriptMetadata(
        uuid="test-uuid",
        created_at=datetime.now(timezone.utc),
        title="Test",
        files_touched=files
    )
    
    assert metadata.files_touched == files
    
    aits_dict = metadata.to_aits_dict()
    assert aits_dict["files_touched"] == files
