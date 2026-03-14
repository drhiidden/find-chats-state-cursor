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

- **IDE-Agnostic**: Works with Cursor (implemented), Claude Code & Continue.dev (planned)
- **Smart Renaming**: Date + time + topic + short UUID for easy browsing
- **Recursive Organization**: Automatically finds and organizes nested transcripts (subagents)
- **Cleanup Tools**: Remove empty folders (MCP, agent-tools, etc.) to keep workspace tidy
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
| **Claude Code** | 🚧 Planned | Path documented, parser coming soon |
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
git clone https://github.com/yourusername/cursor-transcript-organizer.git
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

**Claude Code** (macOS):
```
~/Library/Application Support/Claude/chats
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

**Note**: By default, the tool will recursively process nested transcripts (like subagents). Use `--no-recursive` to organize only top-level folders:

```bash
# Disable recursive processing
cursor-org organize /path/to/transcripts --apply --no-recursive
```

### 4. Clean Up Empty Folders

```bash
# Preview cleanup
cursor-org clean /path/to/transcripts

# Apply cleanup
cursor-org clean /path/to/transcripts --apply

# Clean all projects
cursor-org clean . --all --apply
```

### 5. Generate Summaries

Summaries are generated automatically when organizing. Each transcript gets a `summary.md` file with:
- Duration, message count, token usage
- Key topics discussed
- Files modified (when available)
- Outcome status

### 5. View Statistics

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
| `clean` | Remove empty folders (MCP, agent-tools, etc.) | `cursor-org clean path/to/transcripts --apply` |
| `clean --all` | Clean all projects at once | `cursor-org clean . --all --apply` |
| `stats` | Show statistics | `cursor-org stats path/to/transcripts` |
| `search` | Search by content | `cursor-org search path/to/transcripts -q "authentication"` |
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
