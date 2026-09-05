from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
import re


@dataclass
class ToolCall:
    """Represents a tool call made during the session."""
    tool: str
    input_data: Optional[Dict[str, Any]] = field(default_factory=dict)
    output: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class TranscriptMetadata:
    """Metadata extracted from a Cursor chat transcript.
    
    Complies with AITS v1.0 (AI Transcript Standard).
    """

    # AITS v1.0 - Tier 1: Essential (Required)
    schema_version: str = "1.0.0"
    uuid: str = ""  # Will be populated from file
    created_at: datetime = None  # ISO8601 timestamp
    
    # AITS v1.0 - Tier 2: Common (Recommended)
    title: str = "Unknown Topic"
    updated_at: Optional[datetime] = None
    model: Optional[str] = None  # e.g., "claude-sonnet-4.5"
    workspace: Optional[Path] = None  # Project path
    status: str = "active"  # "active" | "archived" | "deleted"
    tool: str = "cursor"
    tool_version: Optional[str] = None
    
    # AITS v1.0 - Tier 3: Extended (Optional)
    tags: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    files_touched: List[str] = field(default_factory=list)
    cost: Optional[float] = None  # USD
    tokens: Optional[Dict[str, int]] = None  # {input, output, total}
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    parent_id: Optional[str] = None
    mode: Optional[str] = None  # "agent", "debug", "ask", "plan"
    outcome: Optional[str] = None  # "success", "partial", "failed", "abandoned"

    # Legacy fields (backward compatibility)
    file_path: Path = None
    start_time: datetime = None  # Alias for created_at
    end_time: datetime = None    # Alias for updated_at
    message_count: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    topic_raw: str = "Unknown Topic"  # Alias for title
    
    # Legacy: Injected Metadata (via Prompt Engineering)
    injected_role: Optional[str] = None
    injected_goal: Optional[str] = None
    injected_files: List[str] = field(default_factory=list)
    injected_status: Optional[str] = None  # COMPLETED, IN_PROGRESS
    
    # M4: Advanced Metadata (following industry best practices)
    tool_calls: List[ToolCall] = field(default_factory=list)
    thinking_blocks: List[str] = field(default_factory=list)
    subagents_spawned: int = 0
    
    def __post_init__(self):
        """Synchronize AITS fields with legacy fields for backward compatibility."""
        # Sync created_at <-> start_time
        if self.created_at is None and self.start_time is not None:
            self.created_at = self.start_time
        elif self.start_time is None and self.created_at is not None:
            self.start_time = self.created_at
            
        # Sync updated_at <-> end_time
        if self.updated_at is None and self.end_time is not None:
            self.updated_at = self.end_time
        elif self.end_time is None and self.updated_at is not None:
            self.end_time = self.updated_at
            
        # Sync title <-> topic_raw
        if self.title == "Unknown Topic" and self.topic_raw != "Unknown Topic":
            self.title = self.topic_raw
        elif self.topic_raw == "Unknown Topic" and self.title != "Unknown Topic":
            self.topic_raw = self.title
            
        # Initialize tokens dict if needed
        if self.tokens is None:
            self.tokens = {"input": 0, "output": 0, "total": 0}

    @property
    def topic_slug(self) -> str:
        """Generate a filesystem-safe slug from the topic."""
        # Use title (AITS) or fallback to topic_raw (legacy)
        topic_text = self.title or self.topic_raw
        # Remove non-alphanumeric chars (keep spaces/hyphens)
        slug = re.sub(r"[^a-zA-Z0-9\s-]", "", topic_text)
        # Replace spaces with hyphens
        slug = re.sub(r"[\s]+", "-", slug)
        # Lowercase and trim
        slug = slug.lower().strip("-")
        # Limit length to 50 chars to avoid path limits
        return slug[:50]

    @property
    def uuid_short(self) -> str:
        """First 8 chars of UUID are sufficient for uniqueness."""
        return self.uuid[:8] if self.uuid else ""

    @property
    def suggested_dirname(self) -> str:
        """Generate the standardized folder name."""
        # Format: YYYY-MM-DD_HHhMM_topic-slug_uuid
        timestamp = self.created_at or self.start_time
        if timestamp is None:
            return f"unknown_{self.uuid_short}"
        date_str = timestamp.strftime("%Y-%m-%d")
        time_str = timestamp.strftime("%Hh%M")
        return f"{date_str}_{time_str}_{self.topic_slug}_{self.uuid_short}"
    
    def to_aits_dict(self) -> Dict[str, Any]:
        """Export to AITS v1.0 compliant dictionary (for JSON/JSONL serialization)."""
        result = {
            "schema_version": self.schema_version,
            "id": self.uuid,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "title": self.title,
        }
        
        # Tier 2: Common (include if present)
        if self.updated_at:
            result["updated_at"] = self.updated_at.isoformat()
        if self.model:
            result["model"] = self.model
        if self.workspace:
            result["workspace"] = str(self.workspace)
        if self.status:
            result["status"] = self.status
        if self.tool:
            result["tool"] = self.tool
        if self.tool_version:
            result["tool_version"] = self.tool_version
            
        # Tier 3: Extended (include if present)
        if self.tags:
            result["tags"] = self.tags
        if self.languages:
            result["languages"] = self.languages
        if self.files_touched:
            result["files_touched"] = self.files_touched
        if self.cost is not None:
            result["cost"] = self.cost
        if self.tokens and (self.tokens.get("total", 0) > 0):
            result["tokens"] = self.tokens
        if self.git_commit:
            result["git_commit"] = self.git_commit
        if self.git_branch:
            result["git_branch"] = self.git_branch
        if self.parent_id:
            result["parent_id"] = self.parent_id
        if self.mode:
            result["mode"] = self.mode
        if self.outcome:
            result["outcome"] = self.outcome
        
        # M4: Advanced metadata
        if self.tool_calls:
            result["tool_calls"] = [
                {
                    "tool": tc.tool,
                    "input": tc.input_data,
                    "output": tc.output,
                    "timestamp": tc.timestamp
                }
                for tc in self.tool_calls
            ]
        if self.thinking_blocks:
            result["thinking_blocks"] = self.thinking_blocks
        if self.subagents_spawned > 0:
            result["subagents_spawned"] = self.subagents_spawned
            
        return result
