import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from .models import TranscriptMetadata


class TranscriptParser:
    """Parses .jsonl transcript files to extract metadata.
    
    Enhanced to extract AITS v1.0 compliant fields including model,
    tokens, git information, and programming languages.
    """

    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Transcript file not found: {self.file_path}")

    def parse(self) -> TranscriptMetadata:
        """Main entry point to parse the file and return AITS-compliant metadata."""
        # 1. Get basic stats from FileSystem
        fs_stats = self._get_fs_stats()

        # 2. Read content
        messages = self._read_messages()

        if not messages:
            # Empty file fallback
            return TranscriptMetadata(
                uuid=self.file_path.stem,
                file_path=self.file_path,
                created_at=fs_stats["created"],
                updated_at=fs_stats["modified"],
                start_time=fs_stats["created"],
                end_time=fs_stats["modified"],
                title="Empty Transcript",
                topic_raw="Empty Transcript",
            )

        # 3. Analyze content
        content_stats = self._analyze_content(messages)

        # 4. Extract Topic (Heuristic: first user message)
        topic = self._extract_topic(messages)

        # 5. Look for Injected Metadata (Headers/Footers)
        injected = self._extract_injected_metadata(messages)
        
        # 6. Extract AITS v1.0 fields
        model_info = self._extract_model_info(messages)
        token_usage = self._calculate_token_usage(messages)
        git_info = self._extract_git_info(messages)
        languages = self._detect_languages(messages)
        files = self._extract_files_touched(messages)
        mode = self._detect_mode(messages)
        
        # 7. Extract M4 Advanced fields
        tool_calls = self._extract_tool_calls(messages)
        thinking_blocks = self._extract_thinking_blocks(messages)
        subagents = self._count_subagents(messages)

        # 8. Construct Metadata Object (AITS v1.0 compliant)
        return TranscriptMetadata(
            # AITS Tier 1: Essential
            schema_version="1.0.0",
            uuid=self.file_path.stem,
            created_at=fs_stats["created"],
            
            # AITS Tier 2: Common
            title=injected.get("goal") or topic,
            updated_at=fs_stats["modified"],
            model=model_info.get("model"),
            workspace=self._detect_workspace(),
            status="active",  # Default, could be enhanced
            tool="cursor",
            tool_version=model_info.get("tool_version"),
            
            # AITS Tier 3: Extended
            tags=self._generate_tags(injected, languages),
            languages=languages,
            files_touched=files,
            tokens=token_usage,
            git_commit=git_info.get("commit"),
            git_branch=git_info.get("branch"),
            mode=mode,
            
            # Legacy fields (backward compatibility)
            file_path=self.file_path,
            start_time=fs_stats["created"],
            end_time=fs_stats["modified"],
            message_count=len(messages),
            user_messages=content_stats["user_count"],
            assistant_messages=content_stats["assistant_count"],
            topic_raw=injected.get("goal") or topic,
            injected_role=injected.get("role"),
            injected_goal=injected.get("goal"),
            injected_status=injected.get("status"),
            injected_files=injected.get("files", []),
            
            # M4: Advanced metadata
            tool_calls=tool_calls,
            thinking_blocks=thinking_blocks,
            subagents_spawned=subagents,
        )

    def _get_fs_stats(self) -> Dict[str, datetime]:
        stat = self.file_path.stat()
        return {
            "created": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        }

    def _read_messages(self) -> List[Dict[str, Any]]:
        messages = []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        if line.strip():
                            messages.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading {self.file_path}: {e}")
        return messages

    def _analyze_content(self, messages: List[Dict]) -> Dict[str, int]:
        user_count = sum(1 for m in messages if m.get("role") == "user")
        assistant_count = sum(1 for m in messages if m.get("role") == "assistant")
        return {"user_count": user_count, "assistant_count": assistant_count}

    def _extract_topic(self, messages: List[Dict]) -> str:
        """Heuristic: First 50 chars of first user message."""
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("message", {}).get("content", [])
                # Handle text content
                if isinstance(content, list):
                    for item in content:
                        if item.get("type") == "text":
                            text = item.get("text", "").strip()
                            if text:
                                return text[:80].replace("\n", " ")
                # Handle string content (legacy format?)
                elif isinstance(content, str):
                    return content[:80].replace("\n", " ")
        return "Unknown Topic"

    def _extract_injected_metadata(self, messages: List[Dict]) -> Dict[str, Any]:
        """Looks for <session_metadata> and <session_summary> blocks."""
        result = {}

        # Combine all text to search via regex (might be inefficient for huge files,
        # but transcripts are usually small text < 1MB)
        full_text = ""
        for msg in messages:
            # Extract text from message
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                for item in content:
                    if item.get("type") == "text":
                        full_text += item.get("text", "") + "\n"

        # Regex Patterns
        # <session_metadata>
        # DATE: ...
        # ROLE: ...
        # GOAL: ...
        # </session_metadata>
        metadata_match = re.search(
            r"<session_metadata>(.*?)</session_metadata>",
            full_text,
            re.DOTALL | re.IGNORECASE,
        )
        if metadata_match:
            block = metadata_match.group(1)
            # Simple line parsing
            role_match = re.search(r"ROLE:\s*(.+)", block, re.IGNORECASE)
            goal_match = re.search(r"GOAL:\s*(.+)", block, re.IGNORECASE)

            if role_match:
                result["role"] = role_match.group(1).strip()
            if goal_match:
                result["goal"] = goal_match.group(1).strip()

        # <session_summary>
        # STATUS: ...
        # FILES_MODIFIED:
        #   - file1
        # </session_summary>
        summary_match = re.search(
            r"<session_summary>(.*?)</session_summary>",
            full_text,
            re.DOTALL | re.IGNORECASE,
        )
        if summary_match:
            block = summary_match.group(1)
            status_match = re.search(r"STATUS:\s*(.+)", block, re.IGNORECASE)
            if status_match:
                result["status"] = status_match.group(1).strip()

            # Extract files list (bullet points under FILES_MODIFIED)
            files_section = re.search(
                r"FILES_MODIFIED:(.*?)(?:[A-Z_]+:|$)", block, re.DOTALL | re.IGNORECASE
            )
            if files_section:
                files_text = files_section.group(1)
                # Find lines starting with - or *
                files = re.findall(r"^\s*[-*]\s*(.+)$", files_text, re.MULTILINE)
                result["files"] = [f.strip() for f in files]

        return result
    
    def _extract_model_info(self, messages: List[Dict]) -> Dict[str, Optional[str]]:
        """Extract AI model and tool version from messages.
        
        Cursor typically includes model info in assistant messages or tool calls.
        Common models: claude-sonnet-4, claude-sonnet-4.5, gpt-4, etc.
        """
        result = {"model": None, "tool_version": None}
        
        # Check first few messages for model hints
        for msg in messages[:10]:
            # Look in message metadata
            if "model" in msg:
                result["model"] = msg["model"]
                break
            
            # Check if there's a system message with version info
            if msg.get("role") == "system":
                content = self._extract_text_content(msg)
                # Try to find model mentions
                model_match = re.search(
                    r"(claude-sonnet-[\d.]+|gpt-[0-9][-\w]*|gemini-[\w-]+)",
                    content,
                    re.IGNORECASE
                )
                if model_match:
                    result["model"] = model_match.group(1).lower()
                    
        # Default to claude-sonnet-4 if Cursor and no model found (common fallback)
        if result["model"] is None:
            result["model"] = "claude-sonnet-4"
            
        return result
    
    def _calculate_token_usage(self, messages: List[Dict]) -> Optional[Dict[str, int]]:
        """Calculate token usage from messages if available.
        
        Returns dict with {input, output, total} or None if not available.
        """
        total_input = 0
        total_output = 0
        found_any = False
        
        for msg in messages:
            # Check if message has token usage data (multiple possible keys)
            if "tokens" in msg:
                tokens = msg["tokens"]
                if isinstance(tokens, dict):
                    total_input += tokens.get("input", 0)
                    total_output += tokens.get("output", 0)
                    found_any = True
            
            # Also check tokenUsage field (camelCase variant)
            if "tokenUsage" in msg:
                tokens = msg["tokenUsage"]
                if isinstance(tokens, dict):
                    total_input += tokens.get("input", 0)
                    total_output += tokens.get("output", 0)
                    found_any = True
            
            # Check usage field (alternative format with different keys)
            if "usage" in msg:
                usage = msg["usage"]
                if isinstance(usage, dict):
                    total_input += usage.get("prompt_tokens", 0)
                    total_output += usage.get("completion_tokens", 0)
                    found_any = True
        
        if found_any:
            return {
                "input": total_input,
                "output": total_output,
                "total": total_input + total_output
            }
        
        return None
    
    def _extract_git_info(self, messages: List[Dict]) -> Dict[str, Optional[str]]:
        """Extract git commit and branch information from messages.
        
        Looks for git-related content in messages or tool calls.
        """
        result = {"commit": None, "branch": None}
        
        # Combine all text to search for git info
        full_text = ""
        for msg in messages[:20]:  # Check first 20 messages
            full_text += self._extract_text_content(msg) + "\n"
        
        # Look for commit SHA (7-40 hex chars)
        commit_match = re.search(r"\b([0-9a-f]{7,40})\b", full_text)
        if commit_match:
            potential_sha = commit_match.group(1)
            # Validate it looks like a git SHA (not just any hex string)
            if len(potential_sha) >= 7 and "git" in full_text.lower():
                result["commit"] = potential_sha
        
        # Look for branch name
        branch_patterns = [
            r"branch[:\s]+([a-zA-Z0-9._/-]+)",
            r"on\s+branch\s+([a-zA-Z0-9._/-]+)",
            r"git checkout\s+([a-zA-Z0-9._/-]+)"
        ]
        for pattern in branch_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                result["branch"] = match.group(1)
                break
        
        return result
    
    def _detect_languages(self, messages: List[Dict]) -> List[str]:
        """Detect programming languages mentioned or used in the conversation.
        
        Looks for file extensions, language mentions, and code blocks.
        """
        languages = set()
        
        # File extension to language mapping
        ext_to_lang = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".cs": "csharp",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".sql": "sql",
            ".sh": "shell",
            ".bash": "shell",
            ".html": "html",
            ".css": "css",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
        }
        
        for msg in messages:
            content = self._extract_text_content(msg)
            
            # Look for file paths with extensions
            for ext, lang in ext_to_lang.items():
                if ext in content:
                    languages.add(lang)
            
            # Look for code block markers (```language)
            code_blocks = re.findall(r"```(\w+)", content)
            for lang in code_blocks:
                lang_lower = lang.lower()
                if lang_lower in ["python", "javascript", "typescript", "java", "cpp", 
                                 "c", "go", "rust", "ruby", "php", "sql", "shell", "bash"]:
                    languages.add(lang_lower)
        
        return sorted(list(languages))
    
    def _extract_files_touched(self, messages: List[Dict]) -> List[str]:
        """Extract list of files that were read/written during the conversation.
        
        Looks for tool calls and file path mentions.
        """
        files = set()
        
        for msg in messages:
            # Check tool_calls field
            if "tool_calls" in msg:
                tool_calls = msg.get("tool_calls", [])
                if isinstance(tool_calls, list):
                    for call in tool_calls:
                        if isinstance(call, dict):
                            tool = call.get("tool", "")
                            params = call.get("parameters", {})
                            
                            # Read, Write, StrReplace tools have path parameter
                            if tool in ["Read", "Write", "StrReplace"] and "path" in params:
                                files.add(params["path"])
            
            # Also check toolUses field (Cursor format)
            if "toolUses" in msg:
                tool_uses = msg.get("toolUses", [])
                if isinstance(tool_uses, list):
                    for tool_use in tool_uses:
                        if isinstance(tool_use, dict):
                            tool = tool_use.get("tool", "")
                            input_data = tool_use.get("input", {})
                            
                            # Read, Write, StrReplace tools have path parameter
                            if tool in ["Read", "Write", "StrReplace", "read", "write"] and "path" in input_data:
                                files.add(input_data["path"])
            
            # Also check injected files (from prompt engineering)
            content = self._extract_text_content(msg)
            # Look for common file path patterns
            file_matches = re.findall(
                r'(?:path|file):\s*([a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9]+)',
                content,
                re.IGNORECASE
            )
            files.update(file_matches)
        
        return sorted(list(files))
    
    def _detect_workspace(self) -> Optional[Path]:
        """Detect workspace path from file location.
        
        Assumes transcript is in .cursor/projects/<workspace-hash>/agent-transcripts/
        """
        # Try to find workspace by going up from transcript file
        parts = self.file_path.parts
        
        # Look for "agent-transcripts" in path
        if "agent-transcripts" in parts:
            idx = parts.index("agent-transcripts")
            # Go up to workspace root (typically 2 levels: projects/<hash>/)
            if idx >= 2:
                # This gives us the hash, but we want the actual workspace
                # For now, return None as we can't reliably determine actual workspace
                pass
        
        # Could also check for common workspace indicators
        # For now, return None and let user configure if needed
        return None
    
    def _detect_mode(self, messages: List[Dict]) -> Optional[str]:
        """Detect agent mode (agent, debug, ask, plan) from messages.
        
        Looks for mode indicators in system messages or metadata.
        """
        for msg in messages[:5]:  # Check first few messages
            if msg.get("role") == "system":
                content = self._extract_text_content(msg).lower()
                if "debug" in content:
                    return "debug"
                elif "ask mode" in content or "read-only" in content:
                    return "ask"
                elif "plan mode" in content or "planning" in content:
                    return "plan"
        
        # Default to agent mode
        return "agent"
    
    def _generate_tags(self, injected: Dict, languages: List[str]) -> List[str]:
        """Generate tags based on content analysis.
        
        Combines injected metadata, detected languages, and heuristics.
        """
        tags = set()
        
        # Add language tags
        tags.update(languages)
        
        # Add status-based tags
        if injected.get("status"):
            status = injected["status"].lower()
            if "complete" in status:
                tags.add("completed")
            elif "progress" in status:
                tags.add("in-progress")
        
        # Add role-based tags
        if injected.get("role"):
            role = injected["role"].lower()
            if "bug" in role or "fix" in role:
                tags.add("bug-fix")
            elif "feature" in role or "implement" in role:
                tags.add("feature")
            elif "refactor" in role:
                tags.add("refactor")
        
        return sorted(list(tags))
    
    def _extract_text_content(self, msg: Dict) -> str:
        """Extract text content from a message (handles different formats)."""
        content = msg.get("message", {}).get("content", [])
        
        text_parts = []
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
        elif isinstance(content, str):
            text_parts.append(content)
        
        return " ".join(text_parts)
    
    def _extract_tool_calls(self, messages: List[Dict]) -> List:
        """Extract all tool calls made during the session.
        
        Returns list of ToolCall objects with tool name, input, and timestamp.
        """
        from .models import ToolCall
        
        tool_calls = []
        
        for msg in messages:
            if msg.get("role") != "assistant":
                continue
            
            # Check for toolUses field (Cursor format)
            tool_uses = msg.get("toolUses", [])
            if isinstance(tool_uses, list):
                for tool_use in tool_uses:
                    if isinstance(tool_use, dict):
                        tool_call = ToolCall(
                            tool=tool_use.get("tool", "unknown"),
                            input_data=tool_use.get("input", {}),
                            output=tool_use.get("output"),
                            timestamp=msg.get("timestamp"),
                        )
                        tool_calls.append(tool_call)
            
            # Also check tool_calls field (alternative format)
            alt_tool_calls = msg.get("tool_calls", [])
            if isinstance(alt_tool_calls, list):
                for tool_call_data in alt_tool_calls:
                    if isinstance(tool_call_data, dict):
                        tool_call = ToolCall(
                            tool=tool_call_data.get("function", {}).get("name", "unknown"),
                            input_data=tool_call_data.get("function", {}).get("arguments", {}),
                            timestamp=msg.get("timestamp"),
                        )
                        tool_calls.append(tool_call)
        
        return tool_calls
    
    def _extract_thinking_blocks(self, messages: List[Dict]) -> List[str]:
        """Extract all extended thinking blocks from messages.
        
        Returns list of thinking block contents.
        """
        thinking_blocks = []
        
        for msg in messages:
            # Check for thinking field
            thinking = msg.get("thinking", {})
            if thinking:
                # Handle different thinking formats
                if isinstance(thinking, dict):
                    blocks = thinking.get("blocks", [])
                    for block in blocks:
                        if isinstance(block, dict):
                            content = block.get("content", "")
                            if content:
                                thinking_blocks.append(content)
                        elif isinstance(block, str):
                            thinking_blocks.append(block)
                elif isinstance(thinking, str):
                    thinking_blocks.append(thinking)
        
        return thinking_blocks
    
    def _count_subagents(self, messages: List[Dict]) -> int:
        """Count how many subagents were spawned during the session.
        
        Looks for Task tool calls or subagent-related patterns.
        """
        subagent_count = 0
        
        for msg in messages:
            if msg.get("role") != "assistant":
                continue
            
            # Check toolUses for Task tool
            tool_uses = msg.get("toolUses", [])
            if isinstance(tool_uses, list):
                for tool_use in tool_uses:
                    if isinstance(tool_use, dict):
                        tool_name = tool_use.get("tool", "").lower()
                        if tool_name in ["task", "spawn", "subagent"]:
                            subagent_count += 1
            
            # Also look in message content for subagent mentions
            content = self._extract_text_content(msg)
            # Look for patterns like "Launching subagent" or "Task agent"
            subagent_patterns = [
                r"launching (?:a )?subagent",
                r"spawning (?:a )?task agent",
                r"created (?:a )?task",
            ]
            for pattern in subagent_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                subagent_count += len(matches)
        
        return subagent_count
