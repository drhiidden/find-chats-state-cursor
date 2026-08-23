# OPSEC — find-chats-state-cursor (cursor-org)

**Audience:** maintainers and HCP adopters using [cursor-sessions-review](https://github.com/haletheia/hcp-skills) skill.

This repository contains **only the CLI**. It does **not** ship user transcripts.

---

## What stays local (never commit)

| Path | Why |
|------|-----|
| `~/.cursor/projects/*/agent-transcripts/*.jsonl` | Full chat content |
| `agent-transcripts/.cursor-org-backups/` | Raw backups |
| Generated digests with unreviewed excerpts | May contain secrets |

---

## Safe outputs

| Output | Where | Notes |
|--------|-------|-------|
| Renamed folders `YYYY-MM-DD_*_uuid/` | Local `~/.cursor/` | Machine-specific |
| `cursor-digest.md` | Private `.procontext/` | Use bundled digest script — paths redacted |
| `cursor-org search` stdout | Terminal | Review before sharing |

---

## Export commands

`cursor-org export` (JSON/HTML) is for **local review**. Before publishing any export:

1. Run layered grep (paths, keys, emails) — same spirit as [oss-safe-publish](https://github.com/haletheia/hcp-skills).
2. Never add exports to OSS repos under `apps/` or public GitHub.

---

## Digest script guarantees (v2026-08-23+)

`scripts/build-daily-cursor-digest.py`:

- Redacts `/home/<user>/…` → `~/…`
- Strips email / `sk-` patterns from excerpts
- Omits absolute filesystem paths from markdown
- Indexes by bucket label + folder name + short UUID only

---

## Workspace fragmentation

Cursor creates **separate transcript stores per workspace root**. The digest script **auto-discovers** all `~/.cursor/projects/home-drugo-projects-HALETHEIA*` buckets — one multi-root checkout may still span multiple buckets.

List resolved dirs:

```bash
python3 scripts/build-daily-cursor-digest.py --workspace HALETHEIA --list-buckets
```

---

## Related

- Tool: `github.com/drhiidden/find-chats-state-cursor`
- HCP skill: `@skill 06-meta/ecosystem-governance/cursor-sessions-review` (hcp-skills)
- Laboratorio SSoT: Domain-FindChats (watermark, delegación — private)
