# Cursor Transcript Organizer

A Python CLI tool to organize, rename, and summarize Cursor AI chat transcripts with human-readable names.

## 🎯 Problem

Cursor stores AI chat transcripts in folders with cryptic UUIDs like `b104cc43-a667-4487-9a6c-c5973777592a/`, making it impossible to find past conversations without opening each one.

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

- **Smart Renaming**: Date + time + topic + short UUID for easy browsing
- **Auto Summaries**: Generates markdown summaries with statistics
- **Batch Processing**: Organize hundreds of transcripts in seconds
- **Safe by Default**: Dry-run mode prevents accidental changes
- **Rich Statistics**: Analyze token usage, activity patterns, and more
- **Multiple Export Formats**: Markdown, JSON, HTML, CJSON
- **Search**: Find conversations by content, date, or metadata
- **Standards Compliant**: Follows AITS v1.0 (AI Transcript Standard)

## 📦 Installation

### Prerequisites
- Python 3.10+
- Cursor IDE (or compatible AI coding assistant)

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

### 1. Preview Changes (Dry-Run)

```bash
cursor-org organize C:\Users\YourName\.cursor\projects\your-project\agent-transcripts
```

This shows what would be renamed without making changes.

### 2. Apply Changes

```bash
cursor-org organize C:\Users\YourName\.cursor\projects\your-project\agent-transcripts --apply
```

### 3. Generate Summaries

Summaries are generated automatically when organizing. Each transcript gets a `summary.md` file with:
- Duration, message count, token usage
- Key topics discussed
- Files modified (when available)
- Outcome status

### 4. View Statistics

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
| `inspect` | Preview metadata of a single transcript | `cursor-org inspect path/to/chat.jsonl` |
| `organize` | Batch rename transcripts | `cursor-org organize path/to/transcripts --apply` |
| `stats` | Show statistics | `cursor-org stats path/to/transcripts` |
| `search` | Search by content | `cursor-org search path/to/transcripts -q "authentication"` |
| `export` | Export to different formats | `cursor-org export chat.jsonl --format html` |
| `clean` | Archive old transcripts | `cursor-org clean path/to/transcripts --older-than-days 90` |
| `version` | Show version | `cursor-org version` |

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
│   └── summary.md
├── 2026-03-14_15h45_fix-bug-in-parser_e5f6g7h8/
│   ├── e5f6g7h8-full-uuid.jsonl
│   └── summary.md
└── 2026-03-13_09h00_refactor-database-layer_i9j0k1l2/
    ├── i9j0k1l2-full-uuid.jsonl
    └── summary.md
```

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
│   ├── cli.py          # CLI interface
│   ├── parser.py       # JSONL parser
│   ├── models.py       # Data models
│   ├── renamer.py      # Renaming logic
│   ├── summary.py      # Summary generation
│   ├── stats.py        # Statistics
│   ├── exporters.py    # Export formats
│   └── indexer.py      # Search indexing
├── tests/              # Test suite
├── pyproject.toml      # Project config
└── README.md
```

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
