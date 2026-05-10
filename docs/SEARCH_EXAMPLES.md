# Search Command Examples

## Basic Usage

```bash
# Simple text search (uses current directory)
cursor-org search "authentication"

# Search in specific directory
cursor-org search "JWT" ~/.cursor/projects/myproject/agent-transcripts
```

## Filtering

```bash
# Filter by date range
cursor-org search "bug" --date-from 2026-03-01 --date-to 2026-03-14

# Filter by tags
cursor-org search "api" --tags security,authentication

# Search only organized transcripts (skip UUID folders)
cursor-org search "database" --organized-only

# Case-sensitive search
cursor-org search "JWT" --case-sensitive
```

## Output Options

```bash
# Show detailed snippets with highlights
cursor-org search "error" --verbose

# Limit number of results
cursor-org search "feature" --limit 10

# Show context around matches
cursor-org search "bug" --context 2 --verbose
```

## Combined Filters

```bash
# Complex query: search for "authentication" in last 2 weeks, case-sensitive, show snippets
cursor-org search "Authentication" \
  --date-from 2026-03-01 \
  --date-to 2026-03-14 \
  --case-sensitive \
  --verbose \
  --limit 5

# Search organized transcripts for specific tags and topic
cursor-org search "API endpoints" \
  --tags security,backend \
  --organized-only \
  --verbose
```

## Performance Examples

```bash
# Quick search in large dataset
cursor-org search "error" /path/with/1000/transcripts

# Expected performance:
# - 100 transcripts: < 0.2s
# - 1000 transcripts: < 2s
```

## Output Format

```
Found 3 matches in 2 transcripts

┌──────────────┬────────────────────────────┬─────────┬──────────────────────┐
│ Date         │ Topic                      │ Matches │ Path                 │
├──────────────┼────────────────────────────┼─────────┼──────────────────────┤
│ 2026-03-12   │ Implement auth             │ 2       │ 2026-03-12_10h30_... │
│ 2026-03-13   │ Fix auth bug               │ 1       │ 2026-03-13_14h15_... │
└──────────────┴────────────────────────────┴─────────┴──────────────────────┘
```

With `--verbose`:

```
Snippets:

Implement auth (2026-03-12)
  ...need to implement JWT authentication for the API...
  ...authentication checks to all protected routes...

Fix auth bug (2026-03-13)
  ...bug in the authentication middleware when...
```

## Edge Cases

```bash
# No matches
cursor-org search "nonexistent_keyword"
# Output: "No matches found."

# Empty directory
cursor-org search "anything" /empty/path
# Output: "No matches found."

# Corrupted files (handled gracefully)
cursor-org search "test" /path/with/corrupted/files
# Skips corrupted files with warning
```

## Tips

1. **Use quotes** for multi-word queries: `"implement authentication"`
2. **Use --verbose** to see context and verify matches
3. **Use --organized-only** to skip messy UUID folders
4. **Use --limit** for quick previews of large result sets
5. **Combine filters** for precise searches

## Common Patterns

```bash
# Find all sessions about a specific topic
cursor-org search "database migration" --verbose

# Find recent errors
cursor-org search "error" --date-from $(date -d '7 days ago' +%Y-%m-%d)

# Find all auth-related work
cursor-org search "auth" --tags security,authentication

# Review specific time period
cursor-org search "" --date-from 2026-03-01 --date-to 2026-03-31
```
