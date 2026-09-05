"""Optional session journal export (local summaries outside transcript store)."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
import re

from .models import TranscriptMetadata

DEFAULT_JOURNAL_DIRNAME = ".session-journal"


def sync_to_session_journal(
    summary_content: str,
    metadata: TranscriptMetadata,
    journal_root: Path | None = None,
) -> Path:
    """
    Copy a transcript summary into a local session journal tree.

    Layout:
        <journal_root>/sessions/YYYY-MM-DD/HHhMM_topic-slug_uuid.md

    Journal root resolution (first match):
    1. ``journal_root`` argument
    2. ``CURSOR_ORG_JOURNAL_ROOT`` environment variable
    3. Walk up from transcript path for ``.session-journal/``

    Args:
        summary_content: Markdown summary content
        metadata: Transcript metadata
        journal_root: Root directory for the journal (optional)

    Returns:
        Path to the created summary file
    """
    root = journal_root or _find_journal_root(metadata.file_path)

    date_str = metadata.start_time.strftime("%Y-%m-%d")
    sessions_dir = root / "sessions" / date_str
    sessions_dir.mkdir(parents=True, exist_ok=True)

    time_str = metadata.start_time.strftime("%Hh%M")
    filename = f"{time_str}_{metadata.topic_slug}_{metadata.uuid_short}.md"
    output_path = sessions_dir / filename
    output_path.write_text(summary_content, encoding="utf-8")

    return output_path


def generate_daily_summary(date: datetime, journal_root: Path | None = None) -> str:
    """Aggregate markdown for all session files on a given date."""
    root = journal_root or Path.cwd() / DEFAULT_JOURNAL_DIRNAME
    if not root.exists():
        raise FileNotFoundError(f"No session journal found at {root}")

    date_str = date.strftime("%Y-%m-%d")
    sessions_dir = root / "sessions" / date_str

    if not sessions_dir.exists():
        return f"# Daily Summary: {date_str}\n\nNo sessions found for this date.\n"

    session_files = sorted(sessions_dir.glob("*.md"))

    if not session_files:
        return f"# Daily Summary: {date_str}\n\nNo sessions found for this date.\n"

    summary = f"# Daily Summary: {date_str}\n\n"
    summary += f"**Total Sessions**: {len(session_files)}\n\n"
    summary += "---\n\n"

    for session_file in session_files:
        match = re.match(r"(\d{2}h\d{2})_(.+)_([a-f0-9]{8})\.md", session_file.name)
        if match:
            time_str, topic_slug, uuid_short = match.groups()
            topic_display = topic_slug.replace("-", " ").title()

            summary += f"## {time_str} - {topic_display}\n\n"
            summary += f"**UUID**: `{uuid_short}`  \n"
            summary += f"**File**: `{session_file.name}`\n\n"

            content = session_file.read_text(encoding="utf-8")
            excerpt = _extract_excerpt(content)
            if excerpt:
                summary += f"> {excerpt}\n\n"

    summary += "---\n\n"
    summary += "_Generated automatically by cursor-org_\n"

    return summary


def save_daily_summary(date: datetime, journal_root: Path | None = None) -> Path:
    """Write aggregated daily summary to sessions/YYYY-MM-DD/README.md."""
    root = journal_root or Path.cwd() / DEFAULT_JOURNAL_DIRNAME

    date_str = date.strftime("%Y-%m-%d")
    sessions_dir = root / "sessions" / date_str
    sessions_dir.mkdir(parents=True, exist_ok=True)

    summary_content = generate_daily_summary(date, root)
    output_path = sessions_dir / "README.md"
    output_path.write_text(summary_content, encoding="utf-8")

    return output_path


def _find_journal_root(start_path: Path) -> Path:
    """
    Resolve session journal root from env or filesystem walk.

    Does not assume any vendor-specific project layout.
    """
    env_root = os.environ.get("CURSOR_ORG_JOURNAL_ROOT")
    if env_root:
        path = Path(env_root).expanduser().resolve()
        if path.is_dir():
            return path
        raise FileNotFoundError(
            f"CURSOR_ORG_JOURNAL_ROOT is set but not a directory: {path}"
        )

    current = start_path.resolve()
    for _ in range(10):
        candidate = current / DEFAULT_JOURNAL_DIRNAME
        if candidate.is_dir():
            return candidate

        parent = current.parent
        if parent == current:
            break
        current = parent

    cwd_candidate = Path.cwd() / DEFAULT_JOURNAL_DIRNAME
    if cwd_candidate.is_dir():
        return cwd_candidate

    raise FileNotFoundError(
        "No session journal found. Create .session-journal/ at project root "
        "or set CURSOR_ORG_JOURNAL_ROOT."
    )


def _extract_excerpt(content: str, max_length: int = 100) -> str:
    """Extract a brief excerpt from markdown content."""
    lines = content.split("\n")
    for line in lines:
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
