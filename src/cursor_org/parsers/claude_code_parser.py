"""Claude Code specific transcript parser.

Handles Claude Code's JSONL format with AITS v1.0 compliance.
Claude Code stores sessions in ~/.claude/projects/<url-encoded-project-path>/sessions/<uuid>.jsonl
"""
import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .base import BaseTranscriptParser, FileStats
from ..models import TranscriptMetadata, ToolCall
from ..constants import (
    AITS_SCHEMA_VERSION, DEFAULT_STATUS, DEFAULT_EMPTY_TITLE,
    DEFAULT_UNKNOWN_TOPIC,
)


class ClaudeCodeParser(BaseTranscriptParser):
    """Parser for Claude Code IDE transcripts.
    
    Claude Code stores transcripts as JSONL files in:
    - macOS/Linux: ~/.claude/projects/<url-encoded-path>/sessions/<uuid>.jsonl
    - Windows: %USERPROFILE%/.claude/projects/<url-encoded-path>/sessions/<uuid>.jsonl
    
    Format: Each line is a JSON record with envelope:
    {
        "type": "user"|"assistant"|"tool_result"|"system"|"summary"|"result",
        "uuid": "...",
        "parentUuid": "...",
        "timestamp": "ISO8601",
        "sessionId": "...",
        "cwd": "/path/...",
        "message": {...}
    }
    """
    
    @classmethod
    def get_ide_name(cls) -> str:
        return "claude"
    
    def parse(self) -> TranscriptMetadata:
        """Main entry point to parse Claude Code JSONL file and return AITS-compliant metadata."""
        fs_stats = self._get_fs_stats()
        records = self._read_records()

        if not records:
            return self._create_empty_metadata(fs_stats)

        # Extract metadata from records
        user_messages = [r for r in records if r.get("type") == "user"]
        assistant_messages = [r for r in records if r.get("type") == "assistant"]
        tool_results = [r for r in records if r.get("type") == "tool_result"]
        
        # Extract timestamps from records (more accurate than filesystem)
        timestamps = [
            self._parse_timestamp(r.get("timestamp"))
            for r in records
            if r.get("timestamp")
        ]
        created_at = min(timestamps) if timestamps else fs_stats.created
        updated_at = max(timestamps) if timestamps else fs_stats.modified
        
        # Extract title from first user message or session metadata
        title = self._extract_title(records)
        
        # Extract model info from assistant messages
        model_info = self._extract_model_info(assistant_messages)
        
        # Extract token usage
        token_usage = self._calculate_token_usage(assistant_messages)
        
        # Extract workspace from records
        workspace = self._extract_workspace(records)
        
        # Extract languages and files
        languages = self._detect_languages(records)
        files = self._extract_files_touched(records)
        
        # Extract tool calls
        tool_calls_list = self._extract_tool_calls(assistant_messages)
        
        # Extract thinking blocks
        thinking_blocks = self._extract_thinking_blocks(assistant_messages)
        
        # Count subagents
        subagents = self._count_subagents(tool_calls_list)
        
        return TranscriptMetadata(
            # AITS Tier 1: Essential
            schema_version=AITS_SCHEMA_VERSION,
            uuid=self.file_path.stem,
            created_at=created_at,
            
            # AITS Tier 2: Common
            title=title,
            updated_at=updated_at,
            model=model_info.get("model"),
            workspace=workspace,
            status=DEFAULT_STATUS,
            tool="claude",  # Claude Code
            tool_version=model_info.get("tool_version"),
            
            # AITS Tier 3: Extended
            tags=self._generate_tags(languages),
            languages=languages,
            files_touched=files,
            tokens=token_usage,
            mode="agent",  # Claude Code is always agent mode
            
            # Legacy fields (backward compatibility)
            file_path=self.file_path,
            start_time=created_at,
            end_time=updated_at,
            message_count=len(records),
            user_messages=len(user_messages),
            assistant_messages=len(assistant_messages),
            topic_raw=title,
            
            # Advanced metadata
            tool_calls=tool_calls_list,
            thinking_blocks=thinking_blocks,
            subagents_spawned=subagents,
        )

    def _create_empty_metadata(self, fs_stats: FileStats) -> TranscriptMetadata:
        """Create metadata for empty transcript file."""
        return TranscriptMetadata(
            uuid=self.file_path.stem,
            file_path=self.file_path,
            created_at=fs_stats.created,
            updated_at=fs_stats.modified,
            start_time=fs_stats.created,
            end_time=fs_stats.modified,
            title=DEFAULT_EMPTY_TITLE,
            topic_raw=DEFAULT_EMPTY_TITLE,
            tool="claude",
        )

    def _read_records(self) -> List[Dict[str, Any]]:
        """Read JSONL file and return list of record dicts.
        
        Returns:
            List of parsed record dictionaries
            
        Raises:
            FileNotFoundError: If transcript file doesn't exist
            IOError: If file cannot be read
            ValueError: If too many parse errors encountered
        """
        records = []
        errors = []
        max_errors = 10
        
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        error_msg = f"Line {line_num}: {str(e)}"
                        errors.append(error_msg)
                        
                        if len(errors) > max_errors:
                            logging.error(f"Too many parse errors in {self.file_path}: {errors}")
                            raise ValueError(f"Too many parse errors (>{max_errors}) in {self.file_path}")
                            
        except FileNotFoundError:
            logging.error(f"Transcript file not found: {self.file_path}")
            raise FileNotFoundError(f"Transcript file not found: {self.file_path}")
        except IOError as e:
            logging.error(f"IO error reading {self.file_path}: {e}")
            raise IOError(f"Error reading {self.file_path}: {e}")
        
        if errors:
            logging.warning(f"Parse errors in {self.file_path} ({len(errors)} lines): {errors[:5]}")
        
        return records

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse ISO8601 timestamp string to datetime."""
        try:
            # Claude Code uses ISO8601 format: "2025-02-20T09:14:32.441Z"
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    def _extract_title(self, records: List[Dict]) -> str:
        """Extract title from first user message."""
        for record in records:
            if record.get("type") == "user":
                message = record.get("message", {})
                content = message.get("content", "")
                
                # Content can be string or list
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    # Join text from all content items
                    text = " ".join(
                        item.get("text", "") 
                        for item in content 
                        if isinstance(item, dict) and item.get("type") == "text"
                    )
                else:
                    continue
                
                # Take first 80 chars as title
                if text:
                    return text[:80].strip()
        
        return DEFAULT_UNKNOWN_TOPIC

    def _extract_model_info(self, assistant_messages: List[Dict]) -> Dict[str, str]:
        """Extract model name from assistant messages."""
        for record in assistant_messages[:5]:  # Check first 5 messages
            message = record.get("message", {})
            model = message.get("model")
            if model:
                return {
                    "model": model,
                    "tool_version": None  # Claude Code doesn't expose version
                }
        
        return {"model": "claude-sonnet-4", "tool_version": None}

    def _calculate_token_usage(self, assistant_messages: List[Dict]) -> Dict[str, int]:
        """Calculate total token usage from assistant messages."""
        total_input = 0
        total_output = 0
        
        for record in assistant_messages:
            message = record.get("message", {})
            usage = message.get("usage", {})
            
            if usage:
                total_input += usage.get("input_tokens", 0)
                total_output += usage.get("output_tokens", 0)
                
                # Add cache reads (counted at 10% cost)
                total_input += usage.get("cache_read_input_tokens", 0)
        
        return {
            "input": total_input,
            "output": total_output,
            "total": total_input + total_output
        }

    def _extract_workspace(self, records: List[Dict]) -> Optional[str]:
        """Extract workspace path from cwd field in records."""
        for record in records[:10]:  # Check first 10 records
            cwd = record.get("cwd")
            if cwd:
                return cwd
        return None

    def _detect_languages(self, records: List[Dict]) -> List[str]:
        """Detect programming languages from tool calls and content."""
        languages = set()
        
        for record in records:
            if record.get("type") == "assistant":
                message = record.get("message", {})
                content = message.get("content", [])
                
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            # Check for tool use with file paths
                            if item.get("type") == "tool_use":
                                tool_input = item.get("input", {})
                                file_path = tool_input.get("file_path") or tool_input.get("path")
                                if file_path:
                                    ext = self._get_file_extension(file_path)
                                    lang = self._extension_to_language(ext)
                                    if lang:
                                        languages.add(lang)
                            
                            # Check for code blocks in text
                            if item.get("type") == "text":
                                text = item.get("text", "")
                                code_langs = re.findall(r"```(\w+)", text)
                                languages.update(code_langs)
        
        return sorted(list(languages))

    def _extract_files_touched(self, records: List[Dict]) -> List[str]:
        """Extract list of files touched from tool calls."""
        files = set()
        
        for record in records:
            if record.get("type") == "assistant":
                message = record.get("message", {})
                content = message.get("content", [])
                
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_use":
                            tool_name = item.get("name", "")
                            tool_input = item.get("input", {})
                            
                            # Extract file paths from various tools
                            if tool_name in ["Read", "Write", "StrReplace"]:
                                path = tool_input.get("file_path") or tool_input.get("path")
                                if path:
                                    files.add(path)
        
        return sorted(list(files))

    def _extract_tool_calls(self, assistant_messages: List[Dict]) -> List[ToolCall]:
        """Extract tool calls from assistant messages."""
        tool_calls = []
        
        for record in assistant_messages:
            message = record.get("message", {})
            content = message.get("content", [])
            timestamp = record.get("timestamp")
            
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        tool_calls.append(ToolCall(
                            tool=item.get("name", "unknown"),
                            input_data=item.get("input", {}),
                            output=None,  # Output is in separate tool_result records
                            timestamp=timestamp
                        ))
        
        return tool_calls

    def _extract_thinking_blocks(self, assistant_messages: List[Dict]) -> List[str]:
        """Extract extended thinking blocks from assistant messages."""
        thinking_blocks = []
        
        for record in assistant_messages:
            message = record.get("message", {})
            content = message.get("content", [])
            
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "thinking":
                        thinking_text = item.get("thinking", "")
                        if thinking_text:
                            thinking_blocks.append(thinking_text)
        
        return thinking_blocks

    def _count_subagents(self, tool_calls: List[ToolCall]) -> int:
        """Count subagent spawns from tool calls."""
        count = 0
        for tc in tool_calls:
            if tc.tool.lower() in ["task", "spawn"]:
                count += 1
        return count

    def _generate_tags(self, languages: List[str]) -> List[str]:
        """Generate tags from languages and other metadata."""
        tags = []
        
        # Add language tags
        for lang in languages[:3]:  # Top 3 languages
            tags.append(lang)
        
        return tags

    def _get_file_extension(self, file_path: str) -> str:
        """Get file extension from path."""
        if "." in file_path:
            return file_path.rsplit(".", 1)[-1].lower()
        return ""

    def _extension_to_language(self, ext: str) -> Optional[str]:
        """Map file extension to language name."""
        mapping = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "jsx": "javascript",
            "tsx": "typescript",
            "java": "java",
            "cpp": "cpp",
            "c": "c",
            "go": "go",
            "rs": "rust",
            "rb": "ruby",
            "php": "php",
            "sql": "sql",
            "sh": "shell",
            "bash": "shell",
        }
        return mapping.get(ext)
