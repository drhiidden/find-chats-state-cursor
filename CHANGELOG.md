# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### 🚧 Pre-Release Testing
- Current version undergoing personal validation
- Public release pending successful testing

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
