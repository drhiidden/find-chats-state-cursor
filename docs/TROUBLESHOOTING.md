# Troubleshooting

## `cursor-org` not found

```bash
pip install cursor-transcript-organizer
# or editable install from this repo
```

## No transcripts detected

- Confirm IDE paths with `cursor-org list-ides`.
- Cursor stores data under `~/.cursor/projects/` (Linux/macOS) or `%USERPROFILE%\.cursor\projects\` (Windows).

## Windows MAX_PATH errors

The organizer truncates long paths automatically; if issues persist, enable long paths in Windows or run from a shorter base directory.

## Permission errors

Run without elevated admin unless your IDE data requires it. The tool only reads/renames local transcript folders.

## Still stuck?

Open an [issue](https://github.com/drhiidden/find-chats-state-cursor/issues) with OS, IDE version, and redacted command output.
