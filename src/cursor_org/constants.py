"""
Constants for cursor_org package.

Centralized constants to avoid magic strings and enable easy configuration.
"""

# AITS Schema
AITS_SCHEMA_VERSION = "1.0.0"

# Default values
DEFAULT_IDE = "cursor"
DEFAULT_MODEL = "claude-sonnet-4"
DEFAULT_STATUS = "active"
DEFAULT_MODE = "agent"
DEFAULT_EMPTY_TITLE = "Empty Transcript"
DEFAULT_UNKNOWN_TOPIC = "Unknown Topic"

# Message roles
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_SYSTEM = "system"

# Content types
CONTENT_TYPE_TEXT = "text"

# Injected metadata blocks (prompt engineering)
INJECTED_METADATA_START = "<session_metadata>"
INJECTED_METADATA_END = "</session_metadata>"
INJECTED_SUMMARY_START = "<session_summary>"
INJECTED_SUMMARY_END = "</session_summary>"

# Injected metadata fields
INJECTED_FIELD_ROLE = "ROLE"
INJECTED_FIELD_GOAL = "GOAL"
INJECTED_FIELD_STATUS = "STATUS"
INJECTED_FIELD_FILES = "FILES_MODIFIED"

# Tool names (for detection)
TOOL_NAMES_FILE_OPS = ["Read", "Write", "StrReplace", "read", "write"]
TOOL_NAMES_TASK = ["task", "spawn", "subagent"]
TOOL_NAMES_ALL = TOOL_NAMES_FILE_OPS + TOOL_NAMES_TASK

# Token usage field names (multiple formats)
TOKEN_FIELD_TOKENS = "tokens"
TOKEN_FIELD_TOKEN_USAGE = "tokenUsage"
TOKEN_FIELD_USAGE = "usage"
TOKEN_FIELD_INPUT = "input"
TOKEN_FIELD_OUTPUT = "output"
TOKEN_FIELD_PROMPT_TOKENS = "prompt_tokens"
TOKEN_FIELD_COMPLETION_TOKENS = "completion_tokens"

# Model detection patterns
MODEL_PATTERNS = [
    r"(claude-sonnet-[\d.]+)",
    r"(gpt-[0-9][-\w]*)",
    r"(gemini-[\w-]+)",
]

# Git patterns
GIT_COMMIT_PATTERN = r"\b([0-9a-f]{7,40})\b"
GIT_COMMIT_MIN_LENGTH = 7
GIT_BRANCH_PATTERNS = [
    r"branch[:\s]+([a-zA-Z0-9._/-]+)",
    r"on\s+branch\s+([a-zA-Z0-9._/-]+)",
    r"git checkout\s+([a-zA-Z0-9._/-]+)",
]

# File path patterns
FILE_PATH_PATTERN = r'(?:path|file):\s*([a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9]+)'

# Code block pattern (for language detection)
CODE_BLOCK_PATTERN = r"```(\w+)"

# File extension to language mapping
FILE_EXTENSION_TO_LANGUAGE = {
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

# Languages recognized in code blocks
RECOGNIZED_LANGUAGES = {
    "python", "javascript", "typescript", "java", "cpp",
    "c", "go", "rust", "ruby", "php", "sql", "shell", "bash"
}

# Mode detection keywords
MODE_KEYWORDS_DEBUG = ["debug"]
MODE_KEYWORDS_ASK = ["ask mode", "read-only"]
MODE_KEYWORDS_PLAN = ["plan mode", "planning"]

# Status tags
TAG_COMPLETED = "completed"
TAG_IN_PROGRESS = "in-progress"
TAG_BUG_FIX = "bug-fix"
TAG_FEATURE = "feature"
TAG_REFACTOR = "refactor"

# Subagent detection patterns
SUBAGENT_PATTERNS = [
    r"launching (?:a )?subagent",
    r"spawning (?:a )?task agent",
    r"created (?:a )?task",
]

# Limits
TOPIC_MAX_LENGTH = 80
MESSAGE_CHECK_LIMIT_MODEL = 10
MESSAGE_CHECK_LIMIT_GIT = 20
MESSAGE_CHECK_LIMIT_MODE = 5

# IDE Paths (for auto-detection)
IDE_PATH_PATTERNS = {
    "cursor": [".cursor", "cursor"],
    "claude": ["claude"],
    "continue": [".continue", "continue"],
    "cline": ["claude-dev", "cline"],
}

# IDE Default Paths (for configuration)
IDE_DEFAULT_PATHS = {
    "cursor": [
        "~/.cursor/projects/{project}/agent-transcripts",
        "~/Library/Application Support/Cursor/User/projects/{project}/agent-transcripts",
        "%APPDATA%/Cursor/User/projects/{project}/agent-transcripts",
    ],
    "claude": [
        "~/.claude/projects/{project}/sessions",
        "%USERPROFILE%/.claude/projects/{project}/sessions",
    ],
    "continue": [
        "~/.continue/sessions",
    ],
    "cline": [
        "~/.vscode/extensions/saoudrizwan.claude-dev-*/chats",
        "~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/chats",
    ],
}

# IDE Descriptions
IDE_DESCRIPTIONS = {
    "cursor": "Cursor AI IDE - stores chats in UUID folders with JSONL format",
    "claude": "Claude Code - Anthropic's AI IDE with built-in /rename and /export",
    "continue": "Continue.dev - Open-source AI code assistant extension",
    "cline": "Cline (ex Claude-dev) - Autonomous coding agent for VSCode",
}

# CLI Messages
CLI_MSG_AUTO_DETECTED = "Auto-detected IDE: {}"
CLI_MSG_DEFAULT_IDE = "Using default IDE: {}"
CLI_MSG_DRY_RUN = "DRY RUN MODE - No changes will be made"
CLI_MSG_SKIPPING_ORGANIZED = "Skipping (already organized): {}"
CLI_MSG_RENAMED = "Renamed"
CLI_MSG_WOULD_RENAME = "Would rename"
CLI_MSG_GENERATED_SUMMARY = "Generated: summary.md"
CLI_MSG_WARNING_PARSE_FAILED = "Warning: Failed to parse {}: {}"

# UUID validation
UUID_LENGTH = 36
UUID_DASH_COUNT = 4
