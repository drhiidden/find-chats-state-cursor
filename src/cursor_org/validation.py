"""
Input validation utilities for cursor-org.

Provides comprehensive pre-flight checks before executing commands
to ensure better user experience and prevent errors.
"""

import os
import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Tuple
from .constants import UUID_LENGTH, UUID_DASH_COUNT


@dataclass
class ValidationResult:
    """Result of a validation check."""
    success: bool
    error_type: Optional[str] = None
    message: Optional[str] = None
    suggestions: Optional[List[str]] = None
    details: Optional[dict] = None
    
    @property
    def is_warning(self) -> bool:
        """Check if this is a warning (not fatal error)."""
        return self.error_type in ["NO_TRANSCRIPTS", "NO_FOLDERS_TO_ORGANIZE", "NO_FOLDERS_TO_CLEAN"]


class PathValidator:
    """Validates file system paths and permissions."""
    
    @staticmethod
    def validate_path(path: Path, require_write: bool = False) -> ValidationResult:
        """
        Validate that a path exists, is a directory, and has required permissions.
        
        Args:
            path: Path to validate
            require_write: Whether write permission is required
            
        Returns:
            ValidationResult with success status and error details
        """
        # Check if path exists
        if not path.exists():
            return ValidationResult(
                success=False,
                error_type="PATH_NOT_FOUND",
                message="Directory not found",
                suggestions=[
                    "Check if the path is correct",
                    "Use 'cursor-org projects' to see available projects",
                    "Try: cursor-org goto <project-name>"
                ],
                details={"path": str(path)}
            )
        
        # Check if it's a directory
        if not path.is_dir():
            return ValidationResult(
                success=False,
                error_type="NOT_A_DIRECTORY",
                message="Path is not a directory",
                suggestions=[
                    f"Expected a directory, but '{path.name}' is a file",
                    "Provide path to a directory containing transcripts",
                    "Use 'cursor-org inspect' to analyze individual files"
                ],
                details={"path": str(path), "name": path.name}
            )
        
        # Check read permission
        if not os.access(path, os.R_OK):
            return ValidationResult(
                success=False,
                error_type="PERMISSION_DENIED",
                message="Permission denied",
                suggestions=[
                    "Run with elevated permissions (administrator/sudo)",
                    "Check folder permissions",
                    "Ensure you own this directory"
                ],
                details={
                    "path": str(path),
                    "permission": "read",
                    "current_perms": PathValidator._get_permissions_string(path)
                }
            )
        
        # Check write permission if required
        if require_write and not os.access(path, os.W_OK):
            return ValidationResult(
                success=False,
                error_type="PERMISSION_DENIED",
                message="Permission denied",
                suggestions=[
                    "Run with elevated permissions (administrator/sudo)",
                    "Check folder permissions",
                    "Ensure you own this directory",
                    "Try without --apply flag to preview changes first"
                ],
                details={
                    "path": str(path),
                    "permission": "write",
                    "current_perms": PathValidator._get_permissions_string(path)
                }
            )
        
        return ValidationResult(success=True)
    
    @staticmethod
    def _get_permissions_string(path: Path) -> str:
        """Get human-readable permissions string."""
        perms = []
        if os.access(path, os.R_OK):
            perms.append("read")
        if os.access(path, os.W_OK):
            perms.append("write")
        if os.access(path, os.X_OK):
            perms.append("execute")
        return ", ".join(perms) if perms else "none"
    
    @staticmethod
    def validate_transcript_dir(path: Path) -> ValidationResult:
        """
        Validate that a directory contains transcripts (.jsonl files).
        
        Args:
            path: Directory to check
            
        Returns:
            ValidationResult indicating if transcripts were found
        """
        # Look for .jsonl files
        jsonl_files = list(path.rglob("*.jsonl"))
        
        if not jsonl_files:
            return ValidationResult(
                success=False,
                error_type="NO_TRANSCRIPTS",
                message="No transcripts found",
                suggestions=[
                    "Path may be incorrect",
                    "Transcripts might be in subdirectories",
                    "Project may have no transcripts yet",
                    "Try: cursor-org projects --pending",
                    "Use --recursive flag to search in subdirectories"
                ],
                details={"path": str(path), "files_found": 0}
            )
        
        return ValidationResult(
            success=True,
            details={"path": str(path), "files_found": len(jsonl_files)}
        )
    
    @staticmethod
    def validate_has_uuid_folders(path: Path) -> ValidationResult:
        """
        Check if directory has UUID folders to organize.
        
        Args:
            path: Directory to check
            
        Returns:
            ValidationResult indicating if UUID folders were found
        """
        uuid_folders = []
        
        for item in path.iterdir():
            if item.is_dir() and PathValidator._is_uuid_folder(item.name):
                uuid_folders.append(item)
        
        if not uuid_folders:
            return ValidationResult(
                success=False,
                error_type="NO_FOLDERS_TO_ORGANIZE",
                message="No folders to organize",
                suggestions=[
                    "All folders are already organized",
                    "Directory contains no UUID folders",
                    "Use 'cursor-org projects --pending' to find projects needing organization",
                    "Transcripts may already have human-readable names"
                ],
                details={"path": str(path), "uuid_folders_found": 0}
            )
        
        return ValidationResult(
            success=True,
            details={"path": str(path), "uuid_folders_found": len(uuid_folders)}
        )
    
    @staticmethod
    def _is_uuid_folder(name: str) -> bool:
        """Check if a folder name looks like a UUID."""
        # UUID format: 8-4-4-4-12 characters (total 36 with dashes)
        if len(name) != UUID_LENGTH:
            return False
        if name.count("-") != UUID_DASH_COUNT:
            return False
        
        # Try to parse as hex
        parts = name.split("-")
        try:
            for part in parts:
                int(part, 16)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def check_disk_space(path: Path, required_mb: float = 100) -> ValidationResult:
        """
        Check if there's sufficient disk space available.
        
        Args:
            path: Path to check disk space for
            required_mb: Minimum required space in MB
            
        Returns:
            ValidationResult indicating if space is sufficient
        """
        try:
            # Get disk usage stats
            stat = shutil.disk_usage(path)
            available_mb = stat.free / (1024 * 1024)
            
            if available_mb < required_mb:
                return ValidationResult(
                    success=False,
                    error_type="INSUFFICIENT_SPACE",
                    message="Insufficient disk space",
                    suggestions=[
                        "Free up disk space",
                        "Try organizing fewer transcripts at once",
                        "Clean up temporary files",
                        "Consider using --no-summaries to save space"
                    ],
                    details={
                        "path": str(path),
                        "required_mb": required_mb,
                        "available_mb": available_mb
                    }
                )
            
            return ValidationResult(
                success=True,
                details={
                    "path": str(path),
                    "available_mb": available_mb
                }
            )
        except Exception as e:
            # If we can't check disk space, just warn
            return ValidationResult(
                success=True,
                message=f"Warning: Could not check disk space: {e}"
            )


class CleanupValidator:
    """Validates cleanup operations."""
    
    PROTECTED_FOLDERS = {
        ".git", ".vscode", ".cursor", ".idea",
        "node_modules", "venv", ".venv", "__pycache__",
        ".procontext", "dist", "build"
    }
    
    @staticmethod
    def validate_cleanup_target(path: Path, max_folders: int = 10) -> ValidationResult:
        """
        Validate cleanup operation before execution.
        
        Args:
            path: Directory to clean
            max_folders: Maximum folders to delete without confirmation
            
        Returns:
            ValidationResult with validation status
        """
        # Check for empty folders
        empty_folders = CleanupValidator._find_empty_folders(path)
        
        if not empty_folders:
            return ValidationResult(
                success=False,
                error_type="NO_FOLDERS_TO_CLEAN",
                message="No folders to clean",
                suggestions=[
                    "Directory is already clean",
                    "No empty or irrelevant folders found",
                    "Your workspace is well organized 🎉"
                ],
                details={"path": str(path), "folders_found": 0}
            )
        
        # Check if any protected folders would be deleted
        protected = [f for f in empty_folders if CleanupValidator._is_protected(f)]
        if protected:
            return ValidationResult(
                success=False,
                error_type="PROTECTED_FOLDER",
                message="Cannot delete protected folder",
                suggestions=[
                    "This folder is marked as protected",
                    f"Protected folders include: {', '.join(CleanupValidator.PROTECTED_FOLDERS)}",
                    "Remove the folder manually if you're sure",
                    "Check your .gitignore for protected patterns"
                ],
                details={
                    "path": str(path),
                    "protected_folders": [str(f) for f in protected]
                }
            )
        
        # Warn if too many folders
        if len(empty_folders) > max_folders:
            return ValidationResult(
                success=False,
                error_type="TOO_MANY_FOLDERS",
                message=f"Too many folders to delete ({len(empty_folders)} folders)",
                suggestions=[
                    "This action will delete a large number of folders",
                    "Review the folders first with a dry-run (without --apply)",
                    "Use --max-depth to limit the scope",
                    "Confirm by reviewing the list carefully"
                ],
                details={
                    "path": str(path),
                    "count": len(empty_folders),
                    "folders": [str(f) for f in empty_folders[:20]]  # Show first 20
                }
            )
        
        return ValidationResult(
            success=True,
            details={
                "path": str(path),
                "folders_found": len(empty_folders)
            }
        )
    
    @staticmethod
    def _find_empty_folders(path: Path, max_depth: int = 3) -> List[Path]:
        """Find empty folders in a directory."""
        empty_folders = []
        
        def scan_dir(current_path: Path, depth: int):
            if depth > max_depth:
                return
            
            try:
                for item in current_path.iterdir():
                    if item.is_dir():
                        # Check if empty
                        if not any(item.iterdir()):
                            empty_folders.append(item)
                        else:
                            scan_dir(item, depth + 1)
            except PermissionError:
                pass
        
        scan_dir(path, 0)
        return empty_folders
    
    @staticmethod
    def _is_protected(folder: Path) -> bool:
        """Check if a folder is protected."""
        return folder.name in CleanupValidator.PROTECTED_FOLDERS


def validate_organize_command(
    target_dir: Path,
    apply: bool = False
) -> Tuple[bool, Optional[ValidationResult]]:
    """
    Comprehensive validation for organize command.
    
    Args:
        target_dir: Directory to organize
        apply: Whether changes will be applied
        
    Returns:
        Tuple of (is_valid, validation_result)
    """
    validator = PathValidator()
    
    # 1. Check path exists and is directory
    result = validator.validate_path(target_dir, require_write=apply)
    if not result.success:
        return False, result
    
    # 2. Check has transcripts (return error, not just warning)
    result = validator.validate_transcript_dir(target_dir)
    if not result.success:
        return False, result
    
    # 3. Check has UUID folders to organize (return error, not just warning)
    result = validator.validate_has_uuid_folders(target_dir)
    if not result.success:
        return False, result
    
    # 4. Check disk space if applying
    if apply:
        result = validator.check_disk_space(target_dir, required_mb=50)
        if not result.success:
            return False, result
    
    return True, None


def validate_clean_command(
    target_dir: Path,
    apply: bool = False,
    max_depth: int = 3
) -> Tuple[bool, Optional[ValidationResult]]:
    """
    Comprehensive validation for clean command.
    
    Args:
        target_dir: Directory to clean
        apply: Whether changes will be applied
        max_depth: Maximum depth to scan
        
    Returns:
        Tuple of (is_valid, validation_result)
    """
    validator = PathValidator()
    cleanup_validator = CleanupValidator()
    
    # 1. Check path exists and is directory
    result = validator.validate_path(target_dir, require_write=apply)
    if not result.success:
        return False, result
    
    # 2. Check for folders to clean (return error, not just warning)
    result = cleanup_validator.validate_cleanup_target(target_dir, max_folders=10)
    if not result.success:
        return False, result
    
    return True, None


def validate_inspect_command(file_path: Path) -> Tuple[bool, Optional[ValidationResult]]:
    """
    Validate inspect command input.
    
    Args:
        file_path: Path to transcript file
        
    Returns:
        Tuple of (is_valid, validation_result)
    """
    # Check file exists
    if not file_path.exists():
        return False, ValidationResult(
            success=False,
            error_type="PATH_NOT_FOUND",
            message="File not found",
            suggestions=[
                "Check if the path is correct",
                "Verify the file exists",
                "Use 'cursor-org projects' to find transcripts"
            ],
            details={"path": str(file_path)}
        )
    
    # Check it's a file (not directory)
    if file_path.is_dir():
        return False, ValidationResult(
            success=False,
            error_type="NOT_A_FILE",
            message="Path is a directory",
            suggestions=[
                f"Expected a file, but '{file_path.name}' is a directory",
                "Use 'cursor-org organize' to process directories",
                "Provide path to a .jsonl transcript file"
            ],
            details={"path": str(file_path), "name": file_path.name}
        )
    
    # Check it's a .jsonl file
    if file_path.suffix != ".jsonl":
        return False, ValidationResult(
            success=False,
            error_type="INVALID_FILE_TYPE",
            message="Invalid file type",
            suggestions=[
                f"Expected a .jsonl file, but got '{file_path.suffix}'",
                "Cursor transcripts use .jsonl format",
                "Check the file extension"
            ],
            details={"path": str(file_path), "suffix": file_path.suffix}
        )
    
    # Check read permission
    if not os.access(file_path, os.R_OK):
        return False, ValidationResult(
            success=False,
            error_type="PERMISSION_DENIED",
            message="Permission denied",
            suggestions=[
                "Check file permissions",
                "Ensure you have read access",
                "Run with elevated permissions if needed"
            ],
            details={
                "path": str(file_path),
                "permission": "read"
            }
        )
    
    return True, None
