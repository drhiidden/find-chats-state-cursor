"""
Custom exceptions and error message templates for cursor-org.

Provides user-friendly error messages with actionable suggestions
to improve the CLI user experience.
"""

from pathlib import Path
from typing import List, Optional


class TranscriptOrgError(Exception):
    """Base exception for all cursor-org errors."""
    
    def __init__(self, message: str, suggestions: Optional[List[str]] = None):
        self.message = message
        self.suggestions = suggestions or []
        super().__init__(message)
    
    def format_message(self) -> str:
        """Format error message with suggestions."""
        lines = [f"[ERROR] {self.message}"]
        
        if self.suggestions:
            lines.append("\nSuggestions:")
            for suggestion in self.suggestions:
                lines.append(f"  * {suggestion}")
        
        lines.append("\nNeed help? Run: cursor-org --help")
        return "\n".join(lines)


class PathNotFoundError(TranscriptOrgError):
    """Raised when a specified path does not exist."""
    
    def __init__(self, path: Path):
        message = f"Directory not found\n\nPath: {path}"
        suggestions = [
            "Check if the path is correct",
            "Verify you have permission to access it",
            "Use 'cursor-org projects' to see available projects",
            "Try: cursor-org goto <project-name>"
        ]
        super().__init__(message, suggestions)
        self.path = path


class NotADirectoryError(TranscriptOrgError):
    """Raised when path is a file instead of a directory."""
    
    def __init__(self, path: Path):
        message = f"Path is not a directory\n\nPath: {path}"
        suggestions = [
            f"Expected a directory, but '{path.name}' is a file",
            "Provide path to a directory containing transcripts",
            "Use 'cursor-org inspect' to analyze individual files"
        ]
        super().__init__(message, suggestions)
        self.path = path


class PermissionError(TranscriptOrgError):
    """Raised when user lacks required permissions."""
    
    def __init__(self, path: Path, permission: str, current_perms: str):
        message = (
            f"Permission denied\n\n"
            f"Path: {path}\n"
            f"Required: {permission} access\n"
            f"Current permissions: {current_perms}"
        )
        suggestions = [
            "Run with elevated permissions (administrator/sudo)",
            "Check folder permissions",
            "Ensure you own this directory",
            "Verify your user account has the necessary rights"
        ]
        super().__init__(message, suggestions)
        self.path = path
        self.permission = permission


class NoTranscriptsFoundError(TranscriptOrgError):
    """Raised when no transcripts are found in the specified directory."""
    
    def __init__(self, path: Path):
        message = f"No transcripts found\n\nDirectory: {path}"
        suggestions = [
            "Path may be incorrect",
            "Transcripts might be in subdirectories",
            "Project may have no transcripts yet",
            "Try: cursor-org projects --pending",
            "Use --recursive flag to search in subdirectories"
        ]
        super().__init__(message, suggestions)
        self.path = path


class NoFoldersToOrganizeError(TranscriptOrgError):
    """Raised when there are no UUID folders to organize."""
    
    def __init__(self, path: Path):
        message = f"No folders to organize\n\nDirectory: {path}"
        suggestions = [
            "All folders are already organized",
            "Directory contains no UUID folders",
            "Use 'cursor-org projects --pending' to find projects needing organization",
            "Transcripts may already have human-readable names"
        ]
        super().__init__(message, suggestions)
        self.path = path


class NoFoldersToCleanError(TranscriptOrgError):
    """Raised when there are no folders to clean up."""
    
    def __init__(self, path: Path):
        message = f"No folders to clean\n\nDirectory: {path}"
        suggestions = [
            "Directory is already clean",
            "No empty or irrelevant folders found",
            "Your workspace is well organized 🎉"
        ]
        super().__init__(message, suggestions)
        self.path = path


class InsufficientSpaceError(TranscriptOrgError):
    """Raised when there's not enough disk space."""
    
    def __init__(self, required_mb: float, available_mb: float, path: Path):
        message = (
            f"Insufficient disk space\n\n"
            f"Required: {required_mb:.1f} MB\n"
            f"Available: {available_mb:.1f} MB\n"
            f"Path: {path}"
        )
        suggestions = [
            "Free up disk space",
            "Try organizing fewer transcripts at once",
            "Clean up temporary files",
            "Consider using --no-summaries to save space"
        ]
        super().__init__(message, suggestions)
        self.required_mb = required_mb
        self.available_mb = available_mb
        self.path = path


class OperationInProgressError(TranscriptOrgError):
    """Raised when another operation is already in progress."""
    
    def __init__(self, lock_file: Path):
        message = (
            f"Operation already in progress\n\n"
            f"Lock file: {lock_file}"
        )
        suggestions = [
            "Wait for the current operation to complete",
            "If the operation failed, remove the lock file manually",
            f"Delete: {lock_file}",
            "Check if another cursor-org process is running"
        ]
        super().__init__(message, suggestions)
        self.lock_file = lock_file


class TooManyFoldersError(TranscriptOrgError):
    """Raised when trying to delete many folders without confirmation."""
    
    def __init__(self, count: int):
        message = (
            f"Too many folders to delete\n\n"
            f"About to delete {count} folders"
        )
        suggestions = [
            "This action will delete a large number of folders",
            "Please confirm by running with --force flag",
            "Review the folders first with a dry-run (without --apply)",
            "Use --max-depth to limit the scope"
        ]
        super().__init__(message, suggestions)
        self.count = count


class ProtectedFolderError(TranscriptOrgError):
    """Raised when trying to delete protected folders."""
    
    def __init__(self, folder: Path):
        message = (
            f"Cannot delete protected folder\n\n"
            f"Folder: {folder}"
        )
        suggestions = [
            "This folder is marked as protected",
            "Protected folders include: .git, .vscode, node_modules",
            "Remove the folder manually if you're sure",
            "Check your .gitignore for protected patterns"
        ]
        super().__init__(message, suggestions)
        self.folder = folder


# Error message templates for formatting
ERROR_TEMPLATES = {
    "PATH_NOT_FOUND": """
[ERROR] Directory not found

Path: {path}

Suggestions:
  * Check if the path is correct
  * Verify you have permission to access it
  * Use 'cursor-org projects' to see available projects
  * Try: cursor-org goto <project-name>

Need help? Run: cursor-org --help
""",
    
    "NOT_A_DIRECTORY": """
[ERROR] Path is not a directory

Path: {path}

Suggestions:
  * Expected a directory, but '{name}' is a file
  * Provide path to a directory containing transcripts
  * Use 'cursor-org inspect' to analyze individual files

Need help? Run: cursor-org --help
""",
    
    "NO_TRANSCRIPTS": """
[WARNING] No transcripts found

Directory: {path}

This could mean:
  * Path is incorrect
  * Transcripts are in subdirectories (try --recursive)
  * Project has no transcripts yet

To see all projects:
  cursor-org projects

Need help? Run: cursor-org --help
""",
    
    "PERMISSION_DENIED": """
[ERROR] Permission denied

Path: {path}
Required: {permission} access

Solutions:
  * Run with elevated permissions (administrator/sudo)
  * Check folder permissions
  * Ensure you own this directory

Current permissions: {current_perms}

Need help? Run: cursor-org --help
""",
    
    "INSUFFICIENT_SPACE": """
[ERROR] Insufficient disk space

Required: {required_mb:.1f} MB
Available: {available_mb:.1f} MB
Path: {path}

Solutions:
  * Free up disk space
  * Try organizing fewer transcripts at once
  * Clean up temporary files
  * Consider using --no-summaries to save space

Need help? Run: cursor-org --help
""",
    
    "NO_FOLDERS_TO_ORGANIZE": """
[SUCCESS] Directory is already organized!

Directory: {path}

All folders already have human-readable names.
No UUID folders found to organize.

To see project status:
  cursor-org projects
""",
    
    "NO_FOLDERS_TO_CLEAN": """
[SUCCESS] Directory is already clean!

Directory: {path}

No empty or irrelevant folders found.
Your workspace is well organized!

To organize transcripts:
  cursor-org organize {path}
""",
}


def format_error_message(template_key: str, **kwargs) -> str:
    """
    Format an error message from a template.
    
    Args:
        template_key: Key from ERROR_TEMPLATES
        **kwargs: Template variables
    
    Returns:
        Formatted error message
    """
    template = ERROR_TEMPLATES.get(template_key, "")
    if not template:
        return f"Unknown error: {template_key}"
    
    return template.format(**kwargs).strip()
