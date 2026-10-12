# Contributing

Thanks for helping improve **cursor-transcript-organizer** (`cursor-org`).

## Setup

```bash
git clone https://github.com/drhiidden/find-chats-state-cursor.git
cd find-chats-state-cursor
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## Pull requests

- One logical change per PR.
- Include tests for behavior changes.
- Update `CHANGELOG.md` under **Unreleased** when user-facing.
- Do not commit `.venv/`, local paths, or private workflow dumps.

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
