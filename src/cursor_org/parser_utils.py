"""Utility functions shared across parsers.

Common methods for extracting and analyzing transcript content.
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from .constants import (
    ROLE_USER, ROLE_ASSISTANT, ROLE_SYSTEM,
    CONTENT_TYPE_TEXT,
    TOKEN_FIELD_TOKENS, TOKEN_FIELD_TOKEN_USAGE, TOKEN_FIELD_USAGE,
    TOKEN_FIELD_INPUT, TOKEN_FIELD_OUTPUT,
    TOKEN_FIELD_PROMPT_TOKENS, TOKEN_FIELD_COMPLETION_TOKENS,
    MODEL_PATTERNS,
    GIT_COMMIT_PATTERN, GIT_COMMIT_MIN_LENGTH, GIT_BRANCH_PATTERNS,
    FILE_PATH_PATTERN, CODE_BLOCK_PATTERN,
    FILE_EXTENSION_TO_LANGUAGE, RECOGNIZED_LANGUAGES,
    MODE_KEYWORDS_DEBUG, MODE_KEYWORDS_ASK, MODE_KEYWORDS_PLAN,
    TAG_COMPLETED, TAG_IN_PROGRESS, TAG_BUG_FIX, TAG_FEATURE, TAG_REFACTOR,
    TOOL_NAMES_FILE_OPS, TOOL_NAMES_TASK,
    SUBAGENT_PATTERNS,
    TOPIC_MAX_LENGTH, DEFAULT_MODEL, DEFAULT_MODE,
)


@dataclass
class ExtractedMetadata:
    """Container for metadata extracted in a single pass through messages."""
    languages: List[str]
    files: List[str]
    tool_calls: List  # List[ToolCall] - avoiding circular import


def extract_text_content(msg: Dict) -> str:
    """Extract text content from a message (handles different formats).
    
    Args:
        msg: Message dictionary
        
    Returns:
        Extracted text content
    """
    # Validate input type
    if not isinstance(msg, dict):
        return ""
    
    message_data = msg.get("message")
    if not isinstance(message_data, dict):
        return ""
    
    content = message_data.get("content", [])
    
    text_parts = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == CONTENT_TYPE_TEXT:
                text_parts.append(item.get("text", ""))
    elif isinstance(content, str):
        text_parts.append(content)
    
    return " ".join(text_parts)


def analyze_message_counts(messages: List[Dict]) -> Dict[str, int]:
    """Count user and assistant messages.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        Dict with user_count and assistant_count
    """
    # Validate input
    if not isinstance(messages, list) or not messages:
        return {"user_count": 0, "assistant_count": 0}
    
    user_count = sum(1 for m in messages if isinstance(m, dict) and m.get("role") == ROLE_USER)
    assistant_count = sum(1 for m in messages if isinstance(m, dict) and m.get("role") == ROLE_ASSISTANT)
    return {"user_count": user_count, "assistant_count": assistant_count}


def extract_topic_from_messages(messages: List[Dict], max_length: int = TOPIC_MAX_LENGTH) -> str:
    """Extract topic from first user message.
    
    Args:
        messages: List of message dictionaries
        max_length: Maximum length for topic
        
    Returns:
        Extracted topic string
    """
    for msg in messages:
        if msg.get("role") == ROLE_USER:
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                for item in content:
                    if item.get("type") == CONTENT_TYPE_TEXT:
                        text = item.get("text", "").strip()
                        if text:
                            return text[:max_length].replace("\n", " ")
            elif isinstance(content, str):
                return content[:max_length].replace("\n", " ")
    return ""


def extract_model_info(messages: List[Dict], limit: int = 10) -> Dict[str, Optional[str]]:
    """Extract AI model and tool version from messages.
    
    Args:
        messages: List of message dictionaries
        limit: Number of messages to check
        
    Returns:
        Dict with model and tool_version
    """
    result = {"model": None, "tool_version": None}
    
    for msg in messages[:limit]:
        if "model" in msg:
            result["model"] = msg["model"]
            break
        
        if msg.get("role") == ROLE_SYSTEM:
            content = extract_text_content(msg)
            for pattern in MODEL_PATTERNS:
                model_match = re.search(pattern, content, re.IGNORECASE)
                if model_match:
                    result["model"] = model_match.group(1).lower()
                    break
            if result["model"]:
                break
    
    if result["model"] is None:
        result["model"] = DEFAULT_MODEL
    
    return result


def calculate_token_usage(messages: List[Dict]) -> Optional[Dict[str, int]]:
    """Calculate token usage from messages if available.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        Dict with input, output, total or None if not available
    """
    total_input = 0
    total_output = 0
    found_any = False
    
    for msg in messages:
        if TOKEN_FIELD_TOKENS in msg:
            tokens = msg[TOKEN_FIELD_TOKENS]
            if isinstance(tokens, dict):
                total_input += tokens.get(TOKEN_FIELD_INPUT, 0)
                total_output += tokens.get(TOKEN_FIELD_OUTPUT, 0)
                found_any = True
        
        if TOKEN_FIELD_TOKEN_USAGE in msg:
            tokens = msg[TOKEN_FIELD_TOKEN_USAGE]
            if isinstance(tokens, dict):
                total_input += tokens.get(TOKEN_FIELD_INPUT, 0)
                total_output += tokens.get(TOKEN_FIELD_OUTPUT, 0)
                found_any = True
        
        if TOKEN_FIELD_USAGE in msg:
            usage = msg[TOKEN_FIELD_USAGE]
            if isinstance(usage, dict):
                total_input += usage.get(TOKEN_FIELD_PROMPT_TOKENS, 0)
                total_output += usage.get(TOKEN_FIELD_COMPLETION_TOKENS, 0)
                found_any = True
    
    if found_any:
        return {
            TOKEN_FIELD_INPUT: total_input,
            TOKEN_FIELD_OUTPUT: total_output,
            "total": total_input + total_output
        }
    
    return None


def extract_git_info(messages: List[Dict], limit: int = 20) -> Dict[str, Optional[str]]:
    """Extract git commit and branch information from messages.
    
    Args:
        messages: List of message dictionaries
        limit: Number of messages to check
        
    Returns:
        Dict with commit and branch
    """
    result = {"commit": None, "branch": None}
    
    full_text = ""
    for msg in messages[:limit]:
        full_text += extract_text_content(msg) + "\n"
    
    commit_match = re.search(GIT_COMMIT_PATTERN, full_text)
    if commit_match:
        potential_sha = commit_match.group(1)
        if len(potential_sha) >= GIT_COMMIT_MIN_LENGTH and "git" in full_text.lower():
            result["commit"] = potential_sha
    
    for pattern in GIT_BRANCH_PATTERNS:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            result["branch"] = match.group(1)
            break
    
    return result


def detect_mode(messages: List[Dict], limit: int = 5) -> Optional[str]:
    """Detect agent mode (agent, debug, ask, plan) from messages.
    
    Args:
        messages: List of message dictionaries
        limit: Number of messages to check
        
    Returns:
        Detected mode or default
    """
    for msg in messages[:limit]:
        if msg.get("role") == ROLE_SYSTEM:
            content = extract_text_content(msg).lower()
            if any(kw in content for kw in MODE_KEYWORDS_DEBUG):
                return "debug"
            elif any(kw in content for kw in MODE_KEYWORDS_ASK):
                return "ask"
            elif any(kw in content for kw in MODE_KEYWORDS_PLAN):
                return "plan"
    
    return DEFAULT_MODE


def generate_tags(injected: Dict, languages: List[str]) -> List[str]:
    """Generate tags based on content analysis.
    
    Args:
        injected: Injected metadata dict
        languages: List of detected languages
        
    Returns:
        Sorted list of tags
    """
    tags = set()
    tags.update(languages)
    
    if injected.get("status"):
        status = injected["status"].lower()
        if "complete" in status:
            tags.add(TAG_COMPLETED)
        elif "progress" in status:
            tags.add(TAG_IN_PROGRESS)
    
    if injected.get("role"):
        role = injected["role"].lower()
        if "bug" in role or "fix" in role:
            tags.add(TAG_BUG_FIX)
        elif "feature" in role or "implement" in role:
            tags.add(TAG_FEATURE)
        elif "refactor" in role:
            tags.add(TAG_REFACTOR)
    
    return sorted(list(tags))


def extract_multiple_metadata(messages: List[Dict]) -> ExtractedMetadata:
    """Extract languages, files, and tool calls in a single pass through messages.
    
    This optimized function replaces calling detect_languages(), extract_files_touched(),
    and extract_tool_calls() separately, reducing iterations from 3+ to 1.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        ExtractedMetadata object with languages, files, and tool_calls
    """
    from .models import ToolCall
    
    languages = set()
    files = set()
    tool_calls = []
    
    for msg in messages:
        content = extract_text_content(msg)
        
        # Extract languages from file extensions
        for ext, lang in FILE_EXTENSION_TO_LANGUAGE.items():
            if ext in content:
                languages.add(lang)
        
        # Extract languages from code blocks
        code_blocks = re.findall(CODE_BLOCK_PATTERN, content)
        for lang in code_blocks:
            lang_lower = lang.lower()
            if lang_lower in RECOGNIZED_LANGUAGES:
                languages.add(lang_lower)
        
        # Extract files from tool_calls structure
        if "tool_calls" in msg:
            tool_calls_list = msg.get("tool_calls", [])
            if isinstance(tool_calls_list, list):
                for call in tool_calls_list:
                    if isinstance(call, dict):
                        tool = call.get("tool", "")
                        params = call.get("parameters", {})
                        if tool in TOOL_NAMES_FILE_OPS and "path" in params:
                            files.add(params["path"])
        
        # Extract files from toolUses structure
        if "toolUses" in msg:
            tool_uses = msg.get("toolUses", [])
            if isinstance(tool_uses, list):
                for tool_use in tool_uses:
                    if isinstance(tool_use, dict):
                        tool = tool_use.get("tool", "")
                        input_data = tool_use.get("input", {})
                        if tool in TOOL_NAMES_FILE_OPS and "path" in input_data:
                            files.add(input_data["path"])
        
        # Extract files from file path patterns in content
        file_matches = re.findall(FILE_PATH_PATTERN, content, re.IGNORECASE)
        files.update(file_matches)
        
        # Extract tool calls (only from assistant messages)
        if msg.get("role") == ROLE_ASSISTANT:
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
    
    return ExtractedMetadata(
        languages=sorted(list(languages)),
        files=sorted(list(files)),
        tool_calls=tool_calls,
    )


def detect_languages(messages: List[Dict]) -> List[str]:
    """Detect programming languages from file extensions and code blocks.
    
    This is now a wrapper around extract_multiple_metadata() for backward compatibility.
    Consider using extract_multiple_metadata() directly if you need multiple metadata types.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        Sorted list of detected languages
    """
    return extract_multiple_metadata(messages).languages


def extract_files_touched(messages: List[Dict]) -> List[str]:
    """Extract list of files that were read/written during the conversation.
    
    This is now a wrapper around extract_multiple_metadata() for backward compatibility.
    Consider using extract_multiple_metadata() directly if you need multiple metadata types.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        Sorted list of file paths
    """
    return extract_multiple_metadata(messages).files


def extract_tool_calls(messages: List[Dict]):
    """Extract all tool calls made during the session.
    
    This is now a wrapper around extract_multiple_metadata() for backward compatibility.
    Consider using extract_multiple_metadata() directly if you need multiple metadata types.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        List of ToolCall objects
    """
    return extract_multiple_metadata(messages).tool_calls


def extract_thinking_blocks(messages: List[Dict]) -> List[str]:
    """Extract all extended thinking blocks from messages.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        List of thinking block contents
    """
    thinking_blocks = []
    
    for msg in messages:
        thinking = msg.get("thinking", {})
        if thinking:
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


def count_subagents(messages: List[Dict]) -> int:
    """Count how many subagents were spawned during the session.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        Count of subagents
    """
    subagent_count = 0
    
    for msg in messages:
        if msg.get("role") != ROLE_ASSISTANT:
            continue
        
        tool_uses = msg.get("toolUses", [])
        if isinstance(tool_uses, list):
            for tool_use in tool_uses:
                if isinstance(tool_use, dict):
                    tool_name = tool_use.get("tool", "").lower()
                    if tool_name in TOOL_NAMES_TASK:
                        subagent_count += 1
        
        content = extract_text_content(msg)
        for pattern in SUBAGENT_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            subagent_count += len(matches)
    
    return subagent_count
