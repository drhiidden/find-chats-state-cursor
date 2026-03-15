"""
Tests for errors module.

Tests custom exceptions and error message formatting.
"""

import pytest
from pathlib import Path
from cursor_org.errors import (
    TranscriptOrgError,
    PathNotFoundError,
    NotADirectoryError,
    PermissionError,
    NoTranscriptsFoundError,
    NoFoldersToOrganizeError,
    NoFoldersToCleanError,
    InsufficientSpaceError,
    OperationInProgressError,
    TooManyFoldersError,
    ProtectedFolderError,
    format_error_message,
    ERROR_TEMPLATES,
)


class TestBaseException:
    """Test TranscriptOrgError base exception."""
    
    def test_base_exception_with_message(self):
        """Test base exception creation with message."""
        error = TranscriptOrgError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.suggestions == []
    
    def test_base_exception_with_suggestions(self):
        """Test base exception with suggestions."""
        suggestions = ["Suggestion 1", "Suggestion 2"]
        error = TranscriptOrgError("Test error", suggestions=suggestions)
        assert error.suggestions == suggestions
    
    def test_format_message_basic(self):
        """Test basic message formatting."""
        error = TranscriptOrgError("Test error")
        formatted = error.format_message()
        assert "[ERROR] Test error" in formatted
        assert "Need help? Run: cursor-org --help" in formatted
    
    def test_format_message_with_suggestions(self):
        """Test message formatting with suggestions."""
        suggestions = ["Try this", "Or that"]
        error = TranscriptOrgError("Test error", suggestions=suggestions)
        formatted = error.format_message()
        assert "Suggestions:" in formatted
        assert "* Try this" in formatted
        assert "* Or that" in formatted


class TestPathNotFoundError:
    """Test PathNotFoundError exception."""
    
    def test_path_not_found_error(self, tmp_path):
        """Test PathNotFoundError creation."""
        test_path = tmp_path / "nonexistent"
        error = PathNotFoundError(test_path)
        
        assert "Directory not found" in error.message
        assert str(test_path) in error.message
        assert error.path == test_path
        assert len(error.suggestions) > 0
        assert "Check if the path is correct" in error.suggestions[0]


class TestNotADirectoryError:
    """Test NotADirectoryError exception."""
    
    def test_not_a_directory_error(self, tmp_path):
        """Test NotADirectoryError creation."""
        test_file = tmp_path / "test.txt"
        error = NotADirectoryError(test_file)
        
        assert "Path is not a directory" in error.message
        assert str(test_file) in error.message
        assert error.path == test_file
        assert "Expected a directory" in error.suggestions[0]


class TestPermissionError:
    """Test PermissionError exception."""
    
    def test_permission_error(self, tmp_path):
        """Test PermissionError creation."""
        error = PermissionError(tmp_path, "write", "read-only")
        
        assert "Permission denied" in error.message
        assert "write" in error.message
        assert "read-only" in error.message
        assert error.path == tmp_path
        assert error.permission == "write"


class TestNoTranscriptsFoundError:
    """Test NoTranscriptsFoundError exception."""
    
    def test_no_transcripts_error(self, tmp_path):
        """Test NoTranscriptsFoundError creation."""
        error = NoTranscriptsFoundError(tmp_path)
        
        assert "No transcripts found" in error.message
        assert str(tmp_path) in error.message
        assert error.path == tmp_path
        assert "Path may be incorrect" in error.suggestions[0]


class TestNoFoldersToOrganizeError:
    """Test NoFoldersToOrganizeError exception."""
    
    def test_no_folders_to_organize_error(self, tmp_path):
        """Test NoFoldersToOrganizeError creation."""
        error = NoFoldersToOrganizeError(tmp_path)
        
        assert "No folders to organize" in error.message
        assert str(tmp_path) in error.message
        assert error.path == tmp_path
        assert "already organized" in error.suggestions[0]


class TestNoFoldersToCleanError:
    """Test NoFoldersToCleanError exception."""
    
    def test_no_folders_to_clean_error(self, tmp_path):
        """Test NoFoldersToCleanError creation."""
        error = NoFoldersToCleanError(tmp_path)
        
        assert "No folders to clean" in error.message
        assert str(tmp_path) in error.message
        assert error.path == tmp_path
        assert "already clean" in error.suggestions[0]


class TestInsufficientSpaceError:
    """Test InsufficientSpaceError exception."""
    
    def test_insufficient_space_error(self, tmp_path):
        """Test InsufficientSpaceError creation."""
        error = InsufficientSpaceError(100.5, 50.2, tmp_path)
        
        assert "Insufficient disk space" in error.message
        assert "100.5 MB" in error.message
        assert "50.2 MB" in error.message
        assert error.required_mb == 100.5
        assert error.available_mb == 50.2
        assert error.path == tmp_path


class TestOperationInProgressError:
    """Test OperationInProgressError exception."""
    
    def test_operation_in_progress_error(self, tmp_path):
        """Test OperationInProgressError creation."""
        lock_file = tmp_path / ".lock"
        error = OperationInProgressError(lock_file)
        
        assert "Operation already in progress" in error.message
        assert str(lock_file) in error.message
        assert error.lock_file == lock_file


class TestTooManyFoldersError:
    """Test TooManyFoldersError exception."""
    
    def test_too_many_folders_error(self):
        """Test TooManyFoldersError creation."""
        error = TooManyFoldersError(50)
        
        assert "Too many folders to delete" in error.message
        assert "50" in error.message
        assert error.count == 50
        assert "--force" in error.suggestions[1]


class TestProtectedFolderError:
    """Test ProtectedFolderError exception."""
    
    def test_protected_folder_error(self, tmp_path):
        """Test ProtectedFolderError creation."""
        git_folder = tmp_path / ".git"
        error = ProtectedFolderError(git_folder)
        
        assert "Cannot delete protected folder" in error.message
        assert str(git_folder) in error.message
        assert error.folder == git_folder
        assert "protected" in error.suggestions[0]


class TestErrorTemplates:
    """Test error message templates."""
    
    def test_all_templates_exist(self):
        """Test that all expected templates exist."""
        expected_templates = [
            "PATH_NOT_FOUND",
            "NOT_A_DIRECTORY",
            "NO_TRANSCRIPTS",
            "PERMISSION_DENIED",
            "INSUFFICIENT_SPACE",
            "NO_FOLDERS_TO_ORGANIZE",
            "NO_FOLDERS_TO_CLEAN",
        ]
        
        for template_key in expected_templates:
            assert template_key in ERROR_TEMPLATES
            assert len(ERROR_TEMPLATES[template_key]) > 0
    
    def test_format_path_not_found(self, tmp_path):
        """Test formatting PATH_NOT_FOUND template."""
        message = format_error_message(
            "PATH_NOT_FOUND",
            path=str(tmp_path)
        )
        
        assert "[ERROR] Directory not found" in message
        assert str(tmp_path) in message
        assert "Suggestions:" in message
    
    def test_format_not_a_directory(self, tmp_path):
        """Test formatting NOT_A_DIRECTORY template."""
        test_file = tmp_path / "test.txt"
        message = format_error_message(
            "NOT_A_DIRECTORY",
            path=str(test_file),
            name="test.txt"
        )
        
        assert "[ERROR] Path is not a directory" in message
        assert "test.txt" in message
    
    def test_format_no_transcripts(self, tmp_path):
        """Test formatting NO_TRANSCRIPTS template."""
        message = format_error_message(
            "NO_TRANSCRIPTS",
            path=str(tmp_path)
        )
        
        assert "[WARNING] No transcripts found" in message
        assert str(tmp_path) in message
    
    def test_format_permission_denied(self, tmp_path):
        """Test formatting PERMISSION_DENIED template."""
        message = format_error_message(
            "PERMISSION_DENIED",
            path=str(tmp_path),
            permission="write",
            current_perms="read-only"
        )
        
        assert "[ERROR] Permission denied" in message
        assert "write" in message
        assert "read-only" in message
    
    def test_format_insufficient_space(self, tmp_path):
        """Test formatting INSUFFICIENT_SPACE template."""
        message = format_error_message(
            "INSUFFICIENT_SPACE",
            required_mb=100.5,
            available_mb=50.2,
            path=str(tmp_path)
        )
        
        assert "[ERROR] Insufficient disk space" in message
        assert "100.5 MB" in message
        assert "50.2 MB" in message
    
    def test_format_no_folders_to_organize(self, tmp_path):
        """Test formatting NO_FOLDERS_TO_ORGANIZE template."""
        message = format_error_message(
            "NO_FOLDERS_TO_ORGANIZE",
            path=str(tmp_path)
        )
        
        assert "[SUCCESS] Directory is already organized!" in message
        assert str(tmp_path) in message
    
    def test_format_no_folders_to_clean(self, tmp_path):
        """Test formatting NO_FOLDERS_TO_CLEAN template."""
        message = format_error_message(
            "NO_FOLDERS_TO_CLEAN",
            path=str(tmp_path)
        )
        
        assert "[SUCCESS] Directory is already clean!" in message
        assert str(tmp_path) in message
    
    def test_format_unknown_template(self):
        """Test formatting unknown template."""
        message = format_error_message("UNKNOWN_ERROR")
        assert "Unknown error: UNKNOWN_ERROR" in message


class TestErrorConsistency:
    """Test error message consistency."""
    
    def test_all_errors_have_suggestions(self):
        """Test that all custom errors provide suggestions."""
        test_path = Path("/test/path")
        
        errors = [
            PathNotFoundError(test_path),
            NotADirectoryError(test_path),
            PermissionError(test_path, "write", "read"),
            NoTranscriptsFoundError(test_path),
            NoFoldersToOrganizeError(test_path),
            NoFoldersToCleanError(test_path),
            InsufficientSpaceError(100, 50, test_path),
            OperationInProgressError(test_path / ".lock"),
            TooManyFoldersError(50),
            ProtectedFolderError(test_path),
        ]
        
        for error in errors:
            assert len(error.suggestions) > 0
            assert all(isinstance(s, str) for s in error.suggestions)
    
    def test_all_errors_format_correctly(self):
        """Test that all errors format correctly."""
        test_path = Path("/test/path")
        
        errors = [
            PathNotFoundError(test_path),
            NotADirectoryError(test_path),
            NoTranscriptsFoundError(test_path),
            NoFoldersToOrganizeError(test_path),
            NoFoldersToCleanError(test_path),
        ]
        
        for error in errors:
            formatted = error.format_message()
            assert "[ERROR]" in formatted or "[WARNING]" in formatted or "[SUCCESS]" in formatted
            assert "Suggestions:" in formatted or "This could mean:" in formatted
            assert "cursor-org" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
