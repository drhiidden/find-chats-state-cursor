# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### 🚧 Pre-Release Testing
- Current version undergoing personal validation
- Public release pending successful testing

### 🎉 Added (2026-03-15)
- **Backup & Undo System**: Full backup/restore functionality for safety
  - Automatic backup before destructive operations (`organize --apply`, `clean --apply`)
  - New `undo` command to restore from backups
  - New `backups` command to manage backup history
  - Backup metadata with operation details
  - Smart cleanup of old backups (keeps last 10 by default)
  - Disk space checking before backup creation
  - Atomic operations (backup completes or fails entirely)
  - `--no-backup` flag to skip backup for advanced users
  - Backups stored in `.cursor-org-backups/` with timestamp format

### 🧪 Testing (2026-03-15)
- Added 26 comprehensive backup tests (`tests/test_backup.py`)
- All tests passing (26/26)
- Tests cover:
  - Backup creation with single/multiple items
  - Metadata serialization
  - Restore operations
  - Automatic cleanup of old backups
  - Large file handling (1MB+)
  - Concurrent backup operations
  - Error handling and edge cases

### 📚 Documentation (2026-03-15)
- Updated README with backup/undo usage
- Added safety notes to organize and clean commands
- Documented backup structure and management

### 🎉 Added (2026-03-14)
- **Cleanup Command**: New `clean` command to remove empty/irrelevant folders
  - Identifies empty folders, MCP folders, agent-tools folders
  - Removes folders with only hidden/system files
  - Protected folders list to prevent accidental deletion
  - Dry-run by default with `--apply` option
  - Batch cleanup with `--all` flag for all projects
  - Depth control with `--max-depth` option
  - Rich table output showing what will be deleted
  
- **PowerShell Helper**: New `ctc` function for quick cleanup
  - `ctc [project]` - Preview cleanup
  - `ctc [project] -Apply` - Apply cleanup
  - `ctc -All` - Preview cleanup for all projects
  - `ctc -All -Apply` - Clean all projects

### 📚 Documentation (2026-03-14)
- Added comprehensive cleanup guide (`.procontext/docs/CLEANUP-GUIDE.md`)
- Added cleanup implementation details (`.procontext/implementation/CLEANUP-IMPLEMENTATION.md`)
- Updated README with cleanup command
- Updated PowerShell helpers with cleanup function

### 🧪 Testing (2026-03-14)
- Added 14 comprehensive cleanup tests (`tests/test_cleanup.py`)
- All 120 tests passing
- 100% test coverage for cleanup module

---

## [0.3.0-beta] - 2026-03-14

### 🎉 Added
- **CLI Commands**: 10 commands total
  - `inspect` - Preview transcript metadata
  - `organize` - Batch rename with dry-run safety
  - `stats` - Comprehensive statistics
  - `search` - Full-text search with filters
  - `export` - Multiple format support (MD, JSON, HTML, CJSON)
  - `clean` - Archive old transcripts
  - `index` - Fast search indexing
  - `validate` - AITS v1.0 compliance check
  - `version` - Version information
  
- **Auto Summaries**: Generated `summary.md` for each transcript
  - Duration, message count, token usage
  - Files modified tracking
  - Status and outcome
  
- **Advanced Metadata**: Following AITS v1.0 standard
  - Model tracking
  - Git integration (branch, commit)
  - Language detection
  - Tag auto-generation
  
- **Search & Indexing**: 
  - Full-text search across all transcripts
  - Filter by date, tags, language, model
  - Fast indexing system
  
- **Statistics Dashboard**:
  - Token usage breakdown
  - Activity heatmap (ASCII)
  - Top topics
  - Files frequently modified
  
- **Export Formats**:
  - Markdown (enhanced)
  - JSON (AITS v1.0)
  - HTML (styled)
  - CJSON (cross-tool compatibility)

### 🔧 Changed
- Improved naming format: `YYYY-MM-DD_HHhMM_topic-slug_uuid8`
- Enhanced parser with automatic metadata extraction
- Better error handling and user feedback

### 🐛 Fixed
- Unicode compatibility issues on Windows
- Path length validation for Windows MAX_PATH
- Edge cases in topic extraction

### 📚 Documentation
- Complete README with examples
- Command reference
- Optional metadata markers guide
- Development setup guide

---

## [0.2.0] - 2026-03-12

### Added
- Summary generation system
- Integration with custom workflow tools
- Daily summary aggregation

---

## [0.1.0] - 2026-03-12

### Added
- Initial release
- Core parsing functionality
- Basic renaming system
- Dry-run mode
- CLI interface with `inspect` and `organize` commands

---

## Version History

- **0.3.0-beta** (Current) - Advanced features, AITS compliance
- **0.2.0** - Summaries and integrations
- **0.1.0** - Initial implementation

---

**Note**: Versions prior to 1.0.0 are considered pre-release and API may change.
