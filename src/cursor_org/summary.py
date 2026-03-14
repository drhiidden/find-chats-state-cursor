"""Generate markdown summaries from transcript metadata."""

from pathlib import Path
from typing import List, Dict, Any
import re

from .models import TranscriptMetadata


def generate_summary(
    metadata: TranscriptMetadata, messages: List[Dict[str, Any]] | None = None
) -> str:
    """
    Generate a markdown summary for a transcript.

    If a <session_summary> block is found in messages, use it directly.
    Otherwise, generate a basic summary with statistics.

    Args:
        metadata: Parsed transcript metadata
        messages: Optional list of message dictionaries from the .jsonl file

    Returns:
        Markdown-formatted summary string
    """
    # Try to extract injected summary first
    if messages:
        injected_summary = _extract_session_summary(messages)
        if injected_summary:
            return _format_injected_summary(metadata, injected_summary, messages)

    # Otherwise, generate basic summary
    return _generate_basic_summary(metadata, messages)


def _extract_session_summary(messages: List[Dict[str, Any]]) -> str | None:
    """Extract <session_summary> block from messages if present."""
    full_text = ""
    for msg in messages:
        content = msg.get("message", {}).get("content", [])
        if isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    full_text += item.get("text", "") + "\n"

    # Look for <session_summary> block
    match = re.search(
        r"<session_summary>(.*?)</session_summary>",
        full_text,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return None


def _format_injected_summary(metadata: TranscriptMetadata, summary_content: str, messages: List[Dict[str, Any]] | None = None) -> str:
    """Format an injected summary with metadata header."""
    duration = metadata.end_time - metadata.start_time
    duration_str = _format_duration(duration.total_seconds())

    # Calculate token usage
    token_info = ""
    if metadata.tokens and metadata.tokens.get("total", 0) > 0:
        tokens = metadata.tokens
        token_info = f"**Tokens**: {tokens['total']:,} ({tokens['input']:,} input, {tokens['output']:,} output)  \n"
    
    # Git information
    git_info = ""
    if metadata.git_branch or metadata.git_commit:
        git_parts = []
        if metadata.git_branch:
            git_parts.append(f"Branch: `{metadata.git_branch}`")
        if metadata.git_commit:
            git_parts.append(f"Commit: `{metadata.git_commit[:8]}`")
        git_info = f"**Git**: {', '.join(git_parts)}  \n"
    
    # Model information
    model_info = ""
    if metadata.model:
        model_info = f"**Model**: {metadata.model}  \n"
    
    # Workspace information
    workspace_info = ""
    if metadata.workspace:
        workspace_info = f"**Workspace**: `{metadata.workspace}`  \n"

    header = f"""# Chat Summary: {metadata.topic_raw[:60]}

**UUID**: `{metadata.uuid}`  
**Date**: {metadata.start_time.strftime("%Y-%m-%d %H:%M")}  
**Duration**: {duration_str}  
**Messages**: {metadata.message_count} (User: {metadata.user_messages}, Assistant: {metadata.assistant_messages})  
{model_info}{token_info}{git_info}{workspace_info}
---

## Session Summary

{summary_content}
"""

    # Add tool calls summary if available
    if metadata.tool_calls:
        tool_summary = _format_tool_calls_summary(metadata.tool_calls)
        header += f"\n{tool_summary}\n"
    
    # Add files modified if available
    if metadata.files_touched:
        header += "\n## Files Modified\n\n"
        for file in metadata.files_touched[:20]:  # Limit to first 20
            header += f"- `{file}`\n"
        if len(metadata.files_touched) > 20:
            header += f"\n*...and {len(metadata.files_touched) - 20} more files*\n"
        header += "\n"
    
    # Add thinking blocks summary if available
    if metadata.thinking_blocks:
        header += "\n## Extended Thinking\n\n"
        header += f"This session included {len(metadata.thinking_blocks)} extended thinking block(s) for complex reasoning.\n\n"
    
    # Add subagents info if available
    if metadata.subagents_spawned > 0:
        header += "\n## Subagents\n\n"
        header += f"{metadata.subagents_spawned} subagent(s) were spawned during this session.\n\n"

    header += """---

_Generated automatically by cursor-org_
"""
    return header


def _generate_basic_summary(metadata: TranscriptMetadata, messages: List[Dict[str, Any]] | None = None) -> str:
    """Generate a basic summary with statistics only."""
    duration = metadata.end_time - metadata.start_time
    duration_str = _format_duration(duration.total_seconds())

    # Calculate token usage from metadata or messages
    token_info = ""
    if metadata.tokens and metadata.tokens.get("total", 0) > 0:
        tokens = metadata.tokens
        token_info = f"**Tokens**: {tokens['total']:,} ({tokens['input']:,} input, {tokens['output']:,} output)  \n"
    elif messages:
        tokens = _calculate_token_usage(messages)
        if tokens["total"] > 0:
            token_info = f"**Tokens**: {tokens['total']:,} ({tokens['input']:,} input, {tokens['output']:,} output)  \n"
    
    # Git information
    git_info = ""
    if metadata.git_branch or metadata.git_commit:
        git_parts = []
        if metadata.git_branch:
            git_parts.append(f"Branch: `{metadata.git_branch}`")
        if metadata.git_commit:
            git_parts.append(f"Commit: `{metadata.git_commit[:8]}`")
        git_info = f"**Git**: {', '.join(git_parts)}  \n"
    
    # Model information
    model_info = ""
    if metadata.model:
        model_info = f"**Model**: {metadata.model}  \n"
    
    # Workspace information
    workspace_info = ""
    if metadata.workspace:
        workspace_info = f"**Workspace**: `{metadata.workspace}`  \n"

    summary = f"""# Chat Summary: {metadata.topic_raw[:60]}

**UUID**: `{metadata.uuid}`  
**Date**: {metadata.start_time.strftime("%Y-%m-%d %H:%M")}  
**Duration**: {duration_str}  
**Messages**: {metadata.message_count} (User: {metadata.user_messages}, Assistant: {metadata.assistant_messages})  
{model_info}{token_info}{git_info}{workspace_info}
---

## Overview

This chat session covered: *{metadata.topic_raw}*

"""

    # Add injected metadata section if available
    if metadata.injected_role or metadata.injected_goal or metadata.injected_files:
        summary += "## Session Details\n\n"

        if metadata.injected_role:
            summary += f"**Role**: {metadata.injected_role}  \n"
        if metadata.injected_goal:
            summary += f"**Goal**: {metadata.injected_goal}  \n"
        if metadata.injected_status:
            summary += f"**Status**: {metadata.injected_status}  \n"

        if metadata.injected_files:
            summary += "\n**Files Modified**:\n"
            for file in metadata.injected_files:
                summary += f"- `{file}`\n"

        summary += "\n"
    
    # Add tool calls summary if available
    if metadata.tool_calls:
        tool_summary = _format_tool_calls_summary(metadata.tool_calls)
        summary += f"{tool_summary}\n"
    
    # Add files touched if available
    if metadata.files_touched:
        summary += "## Files Touched\n\n"
        for file in metadata.files_touched[:20]:  # Limit to first 20
            summary += f"- `{file}`\n"
        if len(metadata.files_touched) > 20:
            summary += f"\n*...and {len(metadata.files_touched) - 20} more files*\n"
        summary += "\n"
    
    # Add thinking blocks summary if available
    if metadata.thinking_blocks:
        summary += "## Extended Thinking\n\n"
        summary += f"This session included {len(metadata.thinking_blocks)} extended thinking block(s) for complex reasoning.\n\n"
    
    # Add subagents info if available
    if metadata.subagents_spawned > 0:
        summary += "## Subagents\n\n"
        summary += f"{metadata.subagents_spawned} subagent(s) were spawned during this session.\n\n"
    
    # Add languages if detected
    if metadata.languages:
        summary += "## Languages\n\n"
        summary += ", ".join(f"`{lang}`" for lang in metadata.languages)
        summary += "\n\n"

    summary += """---

_Generated automatically by cursor-org_
"""

    return summary


def _format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}m"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"


def _calculate_token_usage(messages: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Calculate token usage from messages if available.

    Args:
        messages: List of message dictionaries from .jsonl file

    Returns:
        Dictionary with input, output, and total token counts
    """
    total_input = 0
    total_output = 0

    for msg in messages:
        # Check for tokenUsage field in message
        token_usage = msg.get("tokenUsage")
        if token_usage:
            total_input += token_usage.get("input", 0)
            total_output += token_usage.get("output", 0)

    return {"input": total_input, "output": total_output, "total": total_input + total_output}


def save_summary(summary_content: str, output_path: Path) -> None:
    """
    Save summary to a markdown file.

    Args:
        summary_content: Markdown content to save
        output_path: Path to output file (typically folder/summary.md)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary_content, encoding="utf-8")


def _format_tool_calls_summary(tool_calls: list) -> str:
    """Format tool calls into a summary section.
    
    Args:
        tool_calls: List of ToolCall objects
    
    Returns:
        Formatted markdown string
    """
    if not tool_calls:
        return ""
    
    # Count tools by type
    tool_counts = {}
    for tc in tool_calls:
        tool_name = tc.tool
        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
    
    # Sort by count descending
    sorted_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)
    
    summary = "## Tool Calls\n\n"
    summary += f"Total tool calls: {len(tool_calls)}\n\n"
    
    for tool_name, count in sorted_tools:
        summary += f"- **{tool_name}**: {count} call(s)\n"
    
    return summary
