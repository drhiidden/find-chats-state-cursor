"""Simple folder renaming utilities."""

from pathlib import Path
from typing import Optional

from .models import TranscriptMetadata


def rename_transcript_folder(
    folder_path: Path, metadata: TranscriptMetadata, dry_run: bool = True
) -> Optional[Path]:
    """
    Rename a transcript folder to a human-readable format.

    Args:
        folder_path: Path to the UUID-named folder
        metadata: Extracted transcript metadata
        dry_run: If True, only return new path without renaming

    Returns:
        New path if successful, None if failed
    """
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    # Generate new name
    new_name = metadata.suggested_dirname
    new_path = folder_path.parent / new_name

    # Check for collisions
    if new_path.exists() and new_path != folder_path:
        # Add UUID to avoid collision
        new_name = f"{new_name}_{metadata.uuid_short}"
        new_path = folder_path.parent / new_name

    # Dry run: just return what would happen
    if dry_run:
        return new_path

    # Execute rename
    try:
        folder_path.rename(new_path)
        return new_path
    except OSError as e:
        print(f"Error renaming {folder_path}: {e}")
        return None


def validate_path_length(path: Path, max_length: int = 260) -> bool:
    """Check if path exceeds Windows MAX_PATH limit."""
    return len(str(path.absolute())) < max_length
