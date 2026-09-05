# Privacy & local data — cursor-org

**Audience:** all users of `cursor-transcript-organizer` / `cursor-org`.

This repository ships **only the CLI**. It does **not** upload transcripts anywhere.

---

## What stays on your machine

| Path | Contents |
|------|----------|
| `~/.cursor/projects/*/agent-transcripts/` | Full chat JSONL (Cursor) |
| `~/.claude/projects/*/sessions/` | Claude Code sessions |
| `.cursor-org-backups/` (under transcript dirs) | Local rename backups |

Never commit these paths to git or paste exports into public repos without review.

---

## Safe vs sensitive outputs

| Output | Risk | Guidance |
|--------|------|----------|
| Renamed folders `YYYY-MM-DD_*_uuid/` | Low (local only) | Machine-specific |
| `cursor-org search` stdout | Medium | May contain code snippets — review before sharing |
| `cursor-org export` JSON/HTML | **High** | Full conversation — grep for secrets before sharing |
| Session journal (`.session-journal/`) | Medium | Summaries only if you opt in with `--sync-sessions` |

---

## Before sharing any export

1. Search for API keys (`sk-`), tokens, emails, internal URLs.
2. Redact absolute home paths if posting publicly.
3. Prefer search snippets over full JSON/HTML exports.

---

## Workspace fragmentation (Cursor)

Cursor creates **one transcript store per workspace root path**. Opening the same repo via different paths (folder vs `.code-workspace`, WSL vs Windows) creates **separate buckets**.

**Recommended workflow:**

```bash
cursor-org projects                    # list buckets
cursor-org search "my topic" --all-cursor   # search every Cursor bucket
```

Use **`search`** for cross-bucket recall. Use **`organize`** only inside a single bucket when you want readable folder names (optional; does not merge buckets).

---

## Optional session journal

Export summaries locally (never required):

```bash
mkdir -p .session-journal
export CURSOR_ORG_JOURNAL_ROOT="$PWD/.session-journal"   # optional explicit root
cursor-org organize path/to/transcripts --apply --sync-sessions
```

Layout: `.session-journal/sessions/YYYY-MM-DD/HHhMM_topic_uuid.md`

---

## Related

- Tool: https://github.com/drhiidden/find-chats-state-cursor
- Issues: https://github.com/drhiidden/find-chats-state-cursor/issues
