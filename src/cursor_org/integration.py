"""Integration with .procontext structure for session tracking."""

from datetime import datetime
from pathlib import Path
import re

from .models import TranscriptMetadata


def sync_to_procontext(
    summary_content: str,
    metadata: TranscriptMetadata,
    procontext_root: Path | None = None,
) -> Path:
    """
    Copy transcript summary to .procontext/sessions/ directory.

    Creates daily aggregated structure:
    .procontext/sessions/YYYY-MM-DD/HHhMM_topic-slug_uuid.md

    Args:
        summary_content: Markdown summary content
        metadata: Transcript metadata
        procontext_root: Root .procontext directory (auto-detected if None)

    Returns:
        Path to the created summary file
    """
    # Auto-detect .procontext directory if not provided
    if procontext_root is None:
        procontext_root = _find_procontext_root(metadata.file_path)

    # Create sessions directory structure
    date_str = metadata.start_time.strftime("%Y-%m-%d")
    sessions_dir = procontext_root / "sessions" / date_str
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    time_str = metadata.start_time.strftime("%Hh%M")
    filename = f"{time_str}_{metadata.topic_slug}_{metadata.uuid_short}.md"
    output_path = sessions_dir / filename

    # Write summary
    output_path.write_text(summary_content, encoding="utf-8")

    return output_path


def generate_daily_summary(date: datetime, procontext_root: Path | None = None) -> str:
    """
    Generate an aggregated summary for all sessions on a given date.

    Args:
        date: Date to summarize
        procontext_root: Root .procontext directory (auto-detected if None)

    Returns:
        Markdown-formatted daily summary
    """
    if procontext_root is None:
        procontext_root = Path.cwd() / ".procontext"
        if not procontext_root.exists():
            raise FileNotFoundError(
                f"No .procontext directory found at {procontext_root}"
            )

    date_str = date.strftime("%Y-%m-%d")
    sessions_dir = procontext_root / "sessions" / date_str

    if not sessions_dir.exists():
        return f"# Daily Summary: {date_str}\n\nNo sessions found for this date.\n"

    # Collect all session files
    session_files = sorted(sessions_dir.glob("*.md"))

    if not session_files:
        return f"# Daily Summary: {date_str}\n\nNo sessions found for this date.\n"

    # Build summary
    summary = f"# Daily Summary: {date_str}\n\n"
    summary += f"**Total Sessions**: {len(session_files)}\n\n"
    summary += "---\n\n"

    for session_file in session_files:
        # Extract metadata from filename: HHhMM_topic-slug_uuid.md
        match = re.match(r"(\d{2}h\d{2})_(.+)_([a-f0-9]{8})\.md", session_file.name)
        if match:
            time_str, topic_slug, uuid_short = match.groups()
            topic_display = topic_slug.replace("-", " ").title()

            summary += f"## {time_str} - {topic_display}\n\n"
            summary += f"**UUID**: `{uuid_short}`  \n"
            summary += f"**File**: `{session_file.name}`\n\n"

            # Optionally include excerpt
            content = session_file.read_text(encoding="utf-8")
            excerpt = _extract_excerpt(content)
            if excerpt:
                summary += f"> {excerpt}\n\n"

    summary += "---\n\n"
    summary += "_Generated automatically by cursor-org_\n"

    return summary


def save_daily_summary(date: datetime, procontext_root: Path | None = None) -> Path:
    """
    Generate and save daily summary to .procontext/sessions/YYYY-MM-DD/README.md

    Args:
        date: Date to summarize
        procontext_root: Root .procontext directory (auto-detected if None)

    Returns:
        Path to the created README.md file
    """
    if procontext_root is None:
        procontext_root = Path.cwd() / ".procontext"

    date_str = date.strftime("%Y-%m-%d")
    sessions_dir = procontext_root / "sessions" / date_str
    sessions_dir.mkdir(parents=True, exist_ok=True)

    summary_content = generate_daily_summary(date, procontext_root)
    output_path = sessions_dir / "README.md"
    output_path.write_text(summary_content, encoding="utf-8")

    return output_path


def _find_procontext_root(start_path: Path) -> Path:
    """
    Search upwards from start_path to find .procontext directory.

    Args:
        start_path: Starting path to search from

    Returns:
        Path to .procontext directory

    Raises:
        FileNotFoundError: If no .procontext directory found
    """
    current = start_path.resolve()

    # Search up to 10 levels
    for _ in range(10):
        procontext = current / ".procontext"
        if procontext.exists() and procontext.is_dir():
            return procontext

        parent = current.parent
        if parent == current:
            break
        current = parent

    # Fallback to cwd
    cwd_procontext = Path.cwd() / ".procontext"
    if cwd_procontext.exists():
        return cwd_procontext

    raise FileNotFoundError(
        "No .procontext directory found. Create one at project root."
    )


def _extract_excerpt(content: str, max_length: int = 100) -> str:
    """Extract a brief excerpt from markdown content."""
    # Skip header and metadata lines
    lines = content.split("\n")
    for line in lines:
        # Skip empty, headers, and metadata lines
        if (
            line.strip()
            and not line.startswith("#")
            and not line.startswith("**")
            and not line.startswith("_")
            and not line.startswith("-")
            and not line.startswith(">")
        ):
            excerpt = line.strip()
            if len(excerpt) > max_length:
                return excerpt[:max_length] + "..."
            return excerpt
    return ""
