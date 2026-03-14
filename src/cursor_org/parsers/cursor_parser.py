"""Cursor-specific transcript parser.

Handles Cursor's JSONL format with AITS v1.0 compliance.
"""
import json
import logging
import re
from typing import Dict, Any, List, Optional

from .base import BaseTranscriptParser, FileStats
from ..models import TranscriptMetadata
from ..constants import (
    AITS_SCHEMA_VERSION, DEFAULT_STATUS, DEFAULT_EMPTY_TITLE,
    DEFAULT_UNKNOWN_TOPIC, INJECTED_METADATA_START, INJECTED_METADATA_END,
    INJECTED_SUMMARY_START, INJECTED_SUMMARY_END,
    INJECTED_FIELD_ROLE, INJECTED_FIELD_GOAL,
    INJECTED_FIELD_STATUS, INJECTED_FIELD_FILES,
    CONTENT_TYPE_TEXT,
)
from ..parser_utils import (
    analyze_message_counts, extract_topic_from_messages,
    extract_model_info, calculate_token_usage, extract_git_info,
    detect_languages, extract_files_touched, detect_mode,
    generate_tags, extract_tool_calls, extract_thinking_blocks, count_subagents,
)


class CursorParser(BaseTranscriptParser):
    """Parser for Cursor AI IDE transcripts.
    
    Cursor stores transcripts as JSONL files in UUID-named folders.
    Format: .cursor/projects/<workspace-hash>/agent-transcripts/<uuid>/<uuid>.jsonl
    """
    
    @classmethod
    def get_ide_name(cls) -> str:
        return "cursor"
    
    def parse(self) -> TranscriptMetadata:
        """Main entry point to parse Cursor JSONL file and return AITS-compliant metadata."""
        fs_stats = self._get_fs_stats()
        messages = self._read_messages()

        if not messages:
            return self._create_empty_metadata(fs_stats)

        content_stats = analyze_message_counts(messages)
        topic = extract_topic_from_messages(messages) or DEFAULT_UNKNOWN_TOPIC
        injected = self._extract_injected_metadata(messages)
        
        # Cache repeated injected field access
        injected_goal = injected.get(INJECTED_FIELD_GOAL.lower())
        injected_role = injected.get(INJECTED_FIELD_ROLE.lower())
        injected_status = injected.get(INJECTED_FIELD_STATUS.lower())
        injected_files = injected.get(INJECTED_FIELD_FILES.lower(), [])
        
        # Compute title once
        title = injected_goal or topic
        
        # Extract AITS v1.0 fields using utils
        model_info = extract_model_info(messages)
        token_usage = calculate_token_usage(messages)
        git_info = extract_git_info(messages)
        languages = detect_languages(messages)
        files = extract_files_touched(messages)
        mode = detect_mode(messages)
        
        # Extract advanced fields
        tool_calls_list = extract_tool_calls(messages)
        thinking_blocks = extract_thinking_blocks(messages)
        subagents = count_subagents(messages)

        return TranscriptMetadata(
            # AITS Tier 1: Essential
            schema_version=AITS_SCHEMA_VERSION,
            uuid=self.file_path.stem,
            created_at=fs_stats.created,
            
            # AITS Tier 2: Common
            title=title,
            updated_at=fs_stats.modified,
            model=model_info.get("model"),
            workspace=self._detect_workspace(),
            status=DEFAULT_STATUS,
            tool="cursor",
            tool_version=model_info.get("tool_version"),
            
            # AITS Tier 3: Extended
            tags=generate_tags(injected, languages),
            languages=languages,
            files_touched=files,
            tokens=token_usage,
            git_commit=git_info.get("commit"),
            git_branch=git_info.get("branch"),
            mode=mode,
            
            # Legacy fields (backward compatibility)
            file_path=self.file_path,
            start_time=fs_stats.created,
            end_time=fs_stats.modified,
            message_count=len(messages),
            user_messages=content_stats["user_count"],
            assistant_messages=content_stats["assistant_count"],
            topic_raw=title,
            injected_role=injected_role,
            injected_goal=injected_goal,
            injected_status=injected_status,
            injected_files=injected_files,
            
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
        )

    def _read_messages(self) -> List[Dict[str, Any]]:
        """Read JSONL file and return list of message dicts.
        
        Returns:
            List of parsed message dictionaries
            
        Raises:
            FileNotFoundError: If transcript file doesn't exist
            IOError: If file cannot be read
            ValueError: If too many parse errors encountered
        """
        messages = []
        errors = []
        max_errors = 10
        
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        messages.append(json.loads(line))
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
        
        return messages

    def _extract_injected_metadata(self, messages: List[Dict]) -> Dict[str, Any]:
        """Look for <session_metadata> and <session_summary> blocks.
        
        Uses efficient list comprehension + join instead of string concatenation.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Dict with extracted injected metadata fields
        """
        result = {}

        # Efficiently build full text using list comprehension + join (O(n) instead of O(n²))
        text_parts = []
        for msg in messages:
            message_data = msg.get("message")
            if not message_data:
                continue
                
            content = message_data.get("content", [])
            if isinstance(content, list):
                text_parts.extend(
                    item.get("text", "")
                    for item in content
                    if item.get("type") == CONTENT_TYPE_TEXT
                )
        
        full_text = "\n".join(text_parts)

        # Extract session_metadata block
        metadata_match = re.search(
            rf"{INJECTED_METADATA_START}(.*?){INJECTED_METADATA_END}",
            full_text,
            re.DOTALL | re.IGNORECASE,
        )
        if metadata_match:
            block = metadata_match.group(1)
            role_match = re.search(rf"{INJECTED_FIELD_ROLE}:\s*(.+)", block, re.IGNORECASE)
            goal_match = re.search(rf"{INJECTED_FIELD_GOAL}:\s*(.+)", block, re.IGNORECASE)

            if role_match:
                result[INJECTED_FIELD_ROLE.lower()] = role_match.group(1).strip()
            if goal_match:
                result[INJECTED_FIELD_GOAL.lower()] = goal_match.group(1).strip()

        # Extract session_summary block
        summary_match = re.search(
            rf"{INJECTED_SUMMARY_START}(.*?){INJECTED_SUMMARY_END}",
            full_text,
            re.DOTALL | re.IGNORECASE,
        )
        if summary_match:
            block = summary_match.group(1)
            status_match = re.search(rf"{INJECTED_FIELD_STATUS}:\s*(.+)", block, re.IGNORECASE)
            if status_match:
                result[INJECTED_FIELD_STATUS.lower()] = status_match.group(1).strip()

            files_section = re.search(
                rf"{INJECTED_FIELD_FILES}:(.*?)(?:[A-Z_]+:|$)", 
                block, 
                re.DOTALL | re.IGNORECASE
            )
            if files_section:
                files_text = files_section.group(1)
                files = re.findall(r"^\s*[-*]\s*(.+)$", files_text, re.MULTILINE)
                result[INJECTED_FIELD_FILES.lower()] = [f.strip() for f in files]

        return result
    
    def _detect_workspace(self) -> Optional[str]:
        """Detect workspace path from file location."""
        # For now return None, can be enhanced later
        return None
