# Cursor Transcript Organizer

**IDE-agnostic CLI** to organize, search, and analyze AI coding assistant transcripts. Transform cryptic UUID folders into human-readable names with rich metadata.

## 🎯 The Story

I initially tried building this as a Cursor extension, but hit a wall—VSCode Extension API can't access `.cursor/projects/` folders outside your workspace. 

**The pivot**: A CLI tool turned out to be *better*:
- Works with **any IDE** (Cursor, Claude Code, Continue.dev)
- Can be **automated** with scripts
- **No permission hassles**
- Cross-platform out of the box

Sometimes the less integrated solution is more powerful 🚀

## 🎯 Problem

AI IDEs store chat transcripts in folders with cryptic UUIDs like `b104cc43-a667-4487-9a6c-c5973777592a/`, making it impossible to find past conversations without opening each one.

## ✨ Solution

This tool transforms:
```
b104cc43-a667-4487-9a6c-c5973777592a/
```

Into:
```
2026-03-12_14h30_implement-auth-feature_b104cc43/
  chat.jsonl
  summary.md (auto-generated)
```

## 🚀 Features

- **IDE-Agnostic**: Works with Cursor & Claude Code (fully implemented), Continue.dev (planned)
- **Smart Renaming**: Date + time + topic + short UUID for easy browsing
- **Recursive Organization**: Automatically finds and organizes nested transcripts (subagents)
- **Cleanup Tools**: Remove empty folders (MCP, agent-tools, etc.) to keep workspace tidy
- **Backup & Undo**: Automatic backups before destructive operations with easy restore
- **Flexible Architecture**: Decoupled collection and organization strategies for extensibility
- **Auto Summaries**: Generates markdown summaries with statistics
- **Batch Processing**: Organize hundreds of transcripts in seconds
- **Safe by Default**: Dry-run mode prevents accidental changes
- **Path Length Handling**: Automatic truncation for Windows MAX_PATH compatibility
- **Rich Statistics**: Analyze token usage, activity patterns, and more
- **Multiple Export Formats**: Markdown, JSON, HTML, CJSON
- **Search**: Find conversations by content, date, or metadata
- **Smart Navigation**: Fuzzy search projects with context differentiation for workspaces
- **Standards Compliant**: Follows AITS v1.0 (AI Transcript Standard)

## 🔧 Supported IDEs

| IDE | Status | Notes |
|-----|--------|-------|
| **Cursor** | ✅ Fully supported | All features working |
| **Claude Code** | ✅ Fully supported | Parser implemented, all features working |
| **Continue.dev** | 🚧 Planned | Community contributions welcome |
| **Cline** | 🚧 Planned | Formerly Claude-dev |
| **Others** | 💡 Propose | [Open an issue](https://github.com/yourusername/cursor-transcript-organizer/issues) |

```bash
# List supported IDEs and their paths
cursor-org list-ides
```

## 📦 Installation

### Prerequisites
- Python 3.10+
- One of: Cursor IDE, Claude Code, Continue.dev, or compatible AI coding assistant

### Install from source

```bash
# Clone the repository
git clone https://github.com/drhiidden/cursor-transcript-organizer.git
cd cursor-transcript-organizer

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Unix/Mac)
source .venv/bin/activate

# Install in editable mode
pip install -e .
```

## 🎮 Quick Start

### 1. Find Your Transcript Path

**Cursor** (Windows):
```
C:\Users\YourName\.cursor\projects\your-project\agent-transcripts
```

**Cursor** (macOS/Linux):
```
~/.cursor/projects/your-project/agent-transcripts
```

**Claude Code** (macOS/Linux):
```
~/.claude/projects/<url-encoded-project-path>/sessions
```

**Claude Code** (Windows):
```
%USERPROFILE%\.claude\projects\<url-encoded-project-path>\sessions
```

**Continue.dev**:
```
~/.continue/sessions
```

Or let the tool auto-detect:
```bash
cursor-org list-ides
```

### 2. Preview Changes (Dry-Run)

```bash
# List all projects
cursor-org projects

# Navigate to a project
cursor-org goto myproject

# Preview organization changes
cursor-org organize /path/to/transcripts
```

This shows what would be renamed without making changes.

### 3. Apply Changes

```bash
cursor-org organize C:\Users\YourName\.cursor\projects\your-project\agent-transcripts --apply
```

**Safety Features**:
- Automatic backup created before renaming (stored in `.cursor-org-backups/`)
- Use `--no-backup` to skip backup creation (advanced users only)
- Backups are kept for the last 10 operations by default

**Note**: By default, the tool will recursively process nested transcripts (like subagents). Use `--no-recursive` to organize only top-level folders:

```bash
# Disable recursive processing
cursor-org organize /path/to/transcripts --apply --no-recursive
```

### 4. Clean Up Empty Folders

```bash
# Preview cleanup
cursor-org clean /path/to/transcripts

# Apply cleanup (with automatic backup)
cursor-org clean /path/to/transcripts --apply

# Skip backup (advanced)
cursor-org clean /path/to/transcripts --apply --no-backup

# Clean all projects
cursor-org clean . --all --apply
```

### 5. Undo Changes (NEW!)

If something goes wrong, restore from backup:

```bash
# List available backups
cursor-org undo

# Restore by index
cursor-org undo 1

# Restore by backup ID
cursor-org undo 2026-03-14_15h30h45_organize

# Manage backups
cursor-org backups                    # List all backups
cursor-org backups --delete 1         # Delete specific backup
cursor-org backups --cleanup          # Remove old backups
```

**Backup Structure**:
```
.cursor-org-backups/
  2026-03-14_15h30h45-123456_organize/
    backup.json      # Metadata
    data/            # Backed up files
```

### 6. Generate Summaries

Summaries are generated automatically when organizing. Each transcript gets a `summary.md` file with:
- Duration, message count, token usage
- Key topics discussed
- Files modified (when available)
- Outcome status

### 7. View Statistics

```bash
cursor-org stats C:\Users\YourName\.cursor\projects\your-project\agent-transcripts
```

Shows:
- Total sessions and messages
- Token usage breakdown
- Most frequent topics
- Activity by day

## 📚 Commands

| Command | Description | Example |
|---------|-------------|---------|
| `projects` | List all Cursor projects | `cursor-org projects` |
| `projects --pending` | Show projects needing organization | `cursor-org projects --pending` |
| `goto` | Navigate to project by name/index | `cursor-org goto myproject` |
| `inspect` | Preview metadata of a single transcript | `cursor-org inspect path/to/chat.jsonl` |
| `organize` | Batch rename transcripts (recursive by default) | `cursor-org organize path/to/transcripts --apply` |
| `organize --no-recursive` | Organize only top-level transcripts | `cursor-org organize path/to/transcripts --apply --no-recursive` |
| `organize --no-backup` | Skip backup creation | `cursor-org organize path/to/transcripts --apply --no-backup` |
| `clean` | Remove empty folders (MCP, agent-tools, etc.) | `cursor-org clean path/to/transcripts --apply` |
| `clean --all` | Clean all projects at once | `cursor-org clean . --all --apply` |
| `clean --no-backup` | Clean without backup | `cursor-org clean path/to/transcripts --apply --no-backup` |
| `undo` | List available backups | `cursor-org undo` |
| `undo <id>` | Restore a specific backup | `cursor-org undo 1` |
| `backups` | Manage backups | `cursor-org backups` |
| `backups --delete <id>` | Delete a backup | `cursor-org backups --delete 1` |
| `backups --cleanup` | Remove old backups | `cursor-org backups --cleanup` |
| `stats` | Show statistics | `cursor-org stats path/to/transcripts` |
| `search` | Search transcripts by text, date, or tags | `cursor-org search "authentication" /path/to/transcripts` |
| `export` | Export to different formats | `cursor-org export chat.jsonl --format html` |
| `list-ides` | List supported IDEs | `cursor-org list-ides` |
| `version` | Show version | `cursor-org version` |

### Recursive Organization

The `organize` command supports recursive processing of nested transcripts (such as subagents):

```bash
# Default: organize everything including nested transcripts
cursor-org organize /path/to/transcripts --apply

# Disable recursive processing (only top-level folders)
cursor-org organize /path/to/transcripts --apply --no-recursive
```

**What gets organized**:
- **Main transcripts**: UUID-named folders get renamed to `YYYY-MM-DD_HHhMM_topic_uuid/`
- **Nested transcripts** (recursive mode): Files in subdirectories (like subagents) get renamed to `YYYY-MM-DD_HHhMM_topic_uuid.jsonl`

**Path length handling**: On Windows, long paths are automatically truncated to avoid MAX_PATH (260 char) issues while preserving readability.

### Search Functionality

Find past conversations quickly by searching transcript content:

```bash
# Simple text search
cursor-org search "authentication"

# Search in specific directory
cursor-org search "JWT" /path/to/transcripts

# Search with date filter
cursor-org search "bug" --date-from 2026-03-01 --date-to 2026-03-14

# Search by tags
cursor-org search "api" --tags security,authentication

# Case-sensitive search
cursor-org search "JWT" --case-sensitive

# Show detailed snippets
cursor-org search "error" --verbose

# Search only organized transcripts
cursor-org search "database" --organized-only

# Limit results
cursor-org search "feature" --limit 10
```

**Search features**:
- **Text search**: Searches in message content and summary files
- **Date filtering**: Filter by date range (`--date-from`, `--date-to`)
- **Tag filtering**: Search by metadata tags (`--tags`)
- **Case sensitivity**: Optional case-sensitive matching (`--case-sensitive`)
- **Context**: Show surrounding text (`--context N`)
- **Snippets**: Highlighted matches with verbose mode (`--verbose`)

### Export Functionality

Export transcripts to multiple formats for sharing, archiving, or integration with other tools:

```bash
# Export to JSON (AITS v1.0 compliant)
cursor-org export /path/to/transcript.jsonl --format json

# Export to Markdown
cursor-org export /path/to/transcript.jsonl --format markdown

# Export to HTML (styled report)
cursor-org export /path/to/transcript.jsonl --format html

# Export to CJSON (Common JSON for interoperability)
cursor-org export /path/to/transcript.jsonl --format cjson

# Specify output path
cursor-org export /path/to/transcript.jsonl --format json -o export.json

# Auto-detects IDE from path
cursor-org export ~/.claude/projects/myapp/sessions/abc123.jsonl --format html

# Works with Claude Code transcripts
cursor-org export ~/.claude/projects/myapp/sessions/session.jsonl --format json --ide claude
```

**Export formats**:
- **JSON**: Structured export with full metadata (AITS v1.0 compliant) - perfect for processing
- **Markdown**: Enhanced markdown with metadata and full conversation - great for documentation
- **HTML**: Styled HTML report with syntax highlighting - ideal for sharing
- **CJSON**: Common JSON format for cross-tool interoperability

**Features**:
- **AITS v1.0 Compliance**: JSON exports follow AI Transcript Standard for maximum compatibility
- **Full Metadata**: All metadata (tokens, files touched, thinking blocks, tool calls) included
- **Unicode Support**: Proper handling of emojis and international characters
- **IDE Agnostic**: Works with Cursor, Claude Code, and other supported IDEs
- **Smart filtering**: Exclude unorganized transcripts (`--organized-only`)

**Output**:
- Rich table with date, topic, match count, and path
- Newest results first
- Highlighted snippets in verbose mode
- Performance optimized for large datasets

### Using with Claude Code

**Claude Code transcripts** are fully supported with the same features as Cursor:

```bash
# Organize Claude Code sessions
cursor-org organize ~/.claude/projects/-home-user-myproject/sessions --apply --ide claude

# Auto-detection works too (recognizes ~/.claude/ paths)
cursor-org organize ~/.claude/projects/-home-user-myproject/sessions --apply

# Export Claude Code session to HTML
cursor-org export ~/.claude/projects/-home-user-myproject/sessions/abc-123.jsonl --format html

# Search Claude Code transcripts
cursor-org search "authentication" ~/.claude/projects/
```

**Claude Code specific features**:
- **Extended Thinking**: Thinking blocks are extracted and included in exports
- **Tool Calls**: All tool uses (Read, Write, Task, etc.) are captured with full inputs
- **Token Usage**: Per-turn token accounting including cache reads
- **Subagents**: Team mode and subagent spawns are tracked
- **Workspace Detection**: Extracts workspace from `cwd` field in records

**Note**: Claude Code uses URL-encoded project paths (e.g., `/home/user/myproject` becomes `-home-user-myproject`).

## 🔧 Configuration

### Metadata Enhancement (Optional)

For richer metadata, you can add markers to your Cursor conversations:

**At the start** (optional):
```markdown
<session_metadata>
ROLE: Backend Developer
GOAL: Implement user authentication
CONTEXT: Sprint 23, following ADR-005
</session_metadata>
```

**Before closing** (optional):
```markdown
<session_summary>
STATUS: COMPLETED
OUTCOME: Auth module implemented and tested
FILES_MODIFIED:
  - src/auth/login.py
  - src/auth/utils.py
  - tests/test_auth.py
NEXT_STEPS:
  - Update documentation
  - Deploy to staging
</session_summary>
```

These markers are parsed automatically and enhance the generated summaries.

## 📊 Output Structure

After organizing, your transcripts will look like this:

```
agent-transcripts/
├── 2026-03-14_10h30_implement-auth-feature_a1b2c3d4/
│   ├── a1b2c3d4-full-uuid.jsonl
│   ├── summary.md
│   └── subagents/
│       ├── 2026-03-14_10h45_database-schema_e5f6g7h8.jsonl
│       └── 2026-03-14_11h00_api-endpoints_i9j0k1l2.jsonl
├── 2026-03-14_15h45_fix-bug-in-parser_e5f6g7h8/
│   ├── e5f6g7h8-full-uuid.jsonl
│   └── summary.md
└── 2026-03-13_09h00_refactor-database-layer_i9j0k1l2/
    ├── i9j0k1l2-full-uuid.jsonl
    └── summary.md
```

**Note**: When using recursive mode (enabled by default), nested transcripts like subagents are automatically renamed with the same format as main transcripts, making it easy to identify and browse through complex conversation hierarchies.

## 🧪 Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Linting
ruff check src/

# Formatting
ruff format src/
```

### Project Structure

```
cursor-transcript-organizer/
├── src/cursor_org/
│   ├── cli.py              # CLI interface
│   ├── collector.py        # Generic transcript collection
│   ├── organizer.py        # Organization strategies
│   ├── parser.py           # JSONL parser
│   ├── parser_utils.py     # Parser utilities
│   ├── parsers/            # Modular parser implementations
│   │   ├── __init__.py
│   │   ├── base.py         # Base parser interface
│   │   └── cursor_parser.py # Cursor-specific parser
│   ├── models.py           # Data models
│   ├── renamer.py          # Renaming logic
│   ├── summary.py          # Summary generation
│   ├── stats.py            # Statistics
│   ├── exporters.py        # Export formats
│   └── indexer.py          # Search indexing
├── tests/                  # Test suite
├── pyproject.toml          # Project config
└── README.md
```

**Architecture highlights**:
- **Decoupled collection**: `TranscriptCollector` finds files without knowing how they'll be organized
- **Strategy pattern**: Different `OrganizationStrategy` implementations for folders vs. files
- **Recursive processing**: Automatic discovery and organization of nested transcripts
- **Extensible parsers**: Easy to add support for new IDE formats

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for the [Cursor](https://cursor.com) community
- Follows AITS v1.0 (AI Transcript Standard) for interoperability
- Inspired by best practices from Claude Code, Amazon Q, and Tabnine

## 📧 Contact

- Issues: [GitHub Issues](https://github.com/yourusername/cursor-transcript-organizer/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/cursor-transcript-organizer/discussions)

---

**Status**: Pre-release (v0.3.0-beta)  
**Note**: Currently in testing phase. Public release pending validation.
