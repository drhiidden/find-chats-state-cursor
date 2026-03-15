"""
Tests for validation module.

Tests input validation for all CLI commands.
"""

import pytest
import os
from pathlib import Path
from cursor_org.validation import (
    PathValidator,
    CleanupValidator,
    ValidationResult,
    validate_organize_command,
    validate_clean_command,
    validate_inspect_command,
)


class TestPathValidator:
    """Test PathValidator class."""
    
    def test_validate_existing_directory(self, tmp_path):
        """Test validation of existing directory."""
        result = PathValidator.validate_path(tmp_path)
        assert result.success
    
    def test_validate_nonexistent_path(self, tmp_path):
        """Test validation of nonexistent path."""
        nonexistent = tmp_path / "nonexistent"
        result = PathValidator.validate_path(nonexistent)
        assert not result.success
        assert result.error_type == "PATH_NOT_FOUND"
        assert "Check if the path is correct" in result.suggestions[0]
    
    def test_validate_file_not_directory(self, tmp_path):
        """Test validation of file when directory expected."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        
        result = PathValidator.validate_path(test_file)
        assert not result.success
        assert result.error_type == "NOT_A_DIRECTORY"
    
    def test_validate_write_permission(self, tmp_path):
        """Test write permission validation."""
        result = PathValidator.validate_path(tmp_path, require_write=True)
        assert result.success
    
    def test_validate_transcript_dir_with_jsonl(self, tmp_path):
        """Test validation of directory with transcripts."""
        # Create a .jsonl file
        (tmp_path / "test.jsonl").write_text("{}")
        
        result = PathValidator.validate_transcript_dir(tmp_path)
        assert result.success
        assert result.details["files_found"] == 1
    
    def test_validate_transcript_dir_empty(self, tmp_path):
        """Test validation of directory without transcripts."""
        result = PathValidator.validate_transcript_dir(tmp_path)
        assert not result.success
        assert result.error_type == "NO_TRANSCRIPTS"
    
    def test_validate_has_uuid_folders(self, tmp_path):
        """Test detection of UUID folders."""
        # Create a UUID folder
        uuid_folder = tmp_path / "b104cc43-a667-4487-9a6c-c5973777592a"
        uuid_folder.mkdir()
        
        result = PathValidator.validate_has_uuid_folders(tmp_path)
        assert result.success
        assert result.details["uuid_folders_found"] == 1
    
    def test_validate_no_uuid_folders(self, tmp_path):
        """Test detection when no UUID folders present."""
        # Create a non-UUID folder
        (tmp_path / "not-a-uuid").mkdir()
        
        result = PathValidator.validate_has_uuid_folders(tmp_path)
        assert not result.success
        assert result.error_type == "NO_FOLDERS_TO_ORGANIZE"
    
    def test_check_disk_space(self, tmp_path):
        """Test disk space check."""
        # Should have plenty of space on test system
        result = PathValidator.check_disk_space(tmp_path, required_mb=1)
        assert result.success
        assert result.details["available_mb"] > 0


class TestCleanupValidator:
    """Test CleanupValidator class."""
    
    def test_validate_cleanup_with_empty_folders(self, tmp_path):
        """Test validation when empty folders exist."""
        # Create empty folder
        empty_folder = tmp_path / "empty"
        empty_folder.mkdir()
        
        result = CleanupValidator.validate_cleanup_target(tmp_path)
        assert result.success
        assert result.details["folders_found"] == 1
    
    def test_validate_cleanup_no_folders(self, tmp_path):
        """Test validation when no folders to clean."""
        result = CleanupValidator.validate_cleanup_target(tmp_path)
        assert not result.success
        assert result.error_type == "NO_FOLDERS_TO_CLEAN"
    
    def test_validate_cleanup_protected_folder(self, tmp_path):
        """Test protection of system folders."""
        # Create protected folder
        git_folder = tmp_path / ".git"
        git_folder.mkdir()
        
        result = CleanupValidator.validate_cleanup_target(tmp_path)
        assert not result.success
        assert result.error_type == "PROTECTED_FOLDER"
    
    def test_validate_cleanup_too_many_folders(self, tmp_path):
        """Test warning for too many folders."""
        # Create many empty folders
        for i in range(15):
            (tmp_path / f"empty_{i}").mkdir()
        
        result = CleanupValidator.validate_cleanup_target(tmp_path, max_folders=10)
        assert not result.success
        assert result.error_type == "TOO_MANY_FOLDERS"
        assert result.details["count"] == 15


class TestCommandValidation:
    """Test command-level validation functions."""
    
    def test_validate_organize_success(self, tmp_path):
        """Test successful organize command validation."""
        # Create UUID folder with transcript
        uuid_folder = tmp_path / "b104cc43-a667-4487-9a6c-c5973777592a"
        uuid_folder.mkdir()
        (uuid_folder / "test.jsonl").write_text("{}")
        
        is_valid, result = validate_organize_command(tmp_path, apply=False)
        assert is_valid
        assert result is None
    
    def test_validate_organize_no_transcripts(self, tmp_path):
        """Test organize validation with no transcripts."""
        is_valid, result = validate_organize_command(tmp_path, apply=False)
        assert not is_valid
        assert result.error_type == "NO_TRANSCRIPTS"
    
    def test_validate_organize_no_uuid_folders(self, tmp_path):
        """Test organize validation with no UUID folders."""
        # Create transcript but not in UUID folder
        (tmp_path / "test.jsonl").write_text("{}")
        
        is_valid, result = validate_organize_command(tmp_path, apply=False)
        assert not is_valid
        assert result.error_type == "NO_FOLDERS_TO_ORGANIZE"
    
    def test_validate_clean_success(self, tmp_path):
        """Test successful clean command validation."""
        # Create empty folder
        (tmp_path / "empty").mkdir()
        
        is_valid, result = validate_clean_command(tmp_path, apply=False)
        assert is_valid
        assert result is None
    
    def test_validate_clean_no_folders(self, tmp_path):
        """Test clean validation with no folders to clean."""
        is_valid, result = validate_clean_command(tmp_path, apply=False)
        assert not is_valid
        assert result.error_type == "NO_FOLDERS_TO_CLEAN"
    
    def test_validate_inspect_success(self, tmp_path):
        """Test successful inspect command validation."""
        test_file = tmp_path / "test.jsonl"
        test_file.write_text("{}")
        
        is_valid, result = validate_inspect_command(test_file)
        assert is_valid
        assert result is None
    
    def test_validate_inspect_nonexistent(self, tmp_path):
        """Test inspect validation with nonexistent file."""
        test_file = tmp_path / "nonexistent.jsonl"
        
        is_valid, result = validate_inspect_command(test_file)
        assert not is_valid
        assert result.error_type == "PATH_NOT_FOUND"
    
    def test_validate_inspect_wrong_type(self, tmp_path):
        """Test inspect validation with wrong file type."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        
        is_valid, result = validate_inspect_command(test_file)
        assert not is_valid
        assert result.error_type == "INVALID_FILE_TYPE"
    
    def test_validate_inspect_directory(self, tmp_path):
        """Test inspect validation with directory instead of file."""
        is_valid, result = validate_inspect_command(tmp_path)
        assert not is_valid
        assert result.error_type == "NOT_A_FILE"


class TestValidationResult:
    """Test ValidationResult class."""
    
    def test_is_warning_property(self):
        """Test is_warning property."""
        # Warning error types
        result_warning = ValidationResult(
            success=False,
            error_type="NO_TRANSCRIPTS"
        )
        assert result_warning.is_warning
        
        # Fatal error type
        result_fatal = ValidationResult(
            success=False,
            error_type="PATH_NOT_FOUND"
        )
        assert not result_fatal.is_warning
    
    def test_validation_result_with_details(self):
        """Test ValidationResult with details."""
        result = ValidationResult(
            success=True,
            details={"path": "/test", "count": 5}
        )
        assert result.success
        assert result.details["count"] == 5


class TestUUIDDetection:
    """Test UUID folder detection."""
    
    def test_is_uuid_folder_valid(self):
        """Test valid UUID folder detection."""
        valid_uuid = "b104cc43-a667-4487-9a6c-c5973777592a"
        assert PathValidator._is_uuid_folder(valid_uuid)
    
    def test_is_uuid_folder_invalid_length(self):
        """Test invalid UUID (wrong length)."""
        invalid_uuid = "b104cc43-a667-4487-9a6c"
        assert not PathValidator._is_uuid_folder(invalid_uuid)
    
    def test_is_uuid_folder_invalid_dashes(self):
        """Test invalid UUID (wrong dash count)."""
        invalid_uuid = "b104cc43a6674487-9a6c-c5973777592a"
        assert not PathValidator._is_uuid_folder(invalid_uuid)
    
    def test_is_uuid_folder_invalid_hex(self):
        """Test invalid UUID (non-hex characters)."""
        invalid_uuid = "g104cc43-a667-4487-9a6c-c5973777592a"
        assert not PathValidator._is_uuid_folder(invalid_uuid)


class TestPermissions:
    """Test permission checking."""
    
    def test_get_permissions_string(self, tmp_path):
        """Test permissions string generation."""
        perms = PathValidator._get_permissions_string(tmp_path)
        assert "read" in perms
        assert "write" in perms
    
    @pytest.mark.skipif(os.name == 'nt', reason="Unix-specific test")
    def test_validate_no_read_permission(self, tmp_path):
        """Test validation with no read permission (Unix only)."""
        test_dir = tmp_path / "no_read"
        test_dir.mkdir()
        os.chmod(test_dir, 0o000)
        
        try:
            result = PathValidator.validate_path(test_dir)
            assert not result.success
            assert result.error_type == "PERMISSION_DENIED"
        finally:
            # Restore permissions for cleanup
            os.chmod(test_dir, 0o755)


class TestDiskSpace:
    """Test disk space validation."""
    
    def test_check_disk_space_sufficient(self, tmp_path):
        """Test disk space check with sufficient space."""
        result = PathValidator.check_disk_space(tmp_path, required_mb=1)
        assert result.success
        assert result.details["available_mb"] > 1
    
    def test_check_disk_space_insufficient(self, tmp_path):
        """Test disk space check with insufficient space."""
        # Request unrealistic amount of space
        result = PathValidator.check_disk_space(tmp_path, required_mb=999999999)
        assert not result.success
        assert result.error_type == "INSUFFICIENT_SPACE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
