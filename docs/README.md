# Documentation Folder

This folder contains all documentation files that are **not** part of the main codebase.

## Purpose

Prevent LLMs from polluting the root directory with `.md` files.

## What goes here

- ✅ Draft documents
- ✅ Audit reports  
- ✅ Design documents
- ✅ Architecture diagrams
- ✅ Meeting notes
- ✅ Temporary documentation

## What stays in root

Only these `.md` files are allowed in root (enforced by pre-commit hook):

- `README.md` - Main project documentation
- `CHANGELOG.md` - Version history
- `AGENTS.md` - AI agent metadata
- `LICENSE` - License file

## Pre-commit Hook

A pre-commit hook automatically **blocks** any attempt to add `.md` files in root that aren't in the whitelist.

If you try to commit a forbidden `.md`:

```bash
❌ ERROR: Attempting to commit .md files in root directory

Files blocked:
  - MY-DOC.md ❌

⚠️  LLMs love to generate .md files in root!
   Move them to docs/ or another subdirectory.
```

## How to move files

```bash
# If you accidentally staged a .md in root
git reset HEAD <file>
mv <file> docs/
git add docs/<file>
```

---

**Enforced by**: `.git/hooks/pre-commit`  
**Reason**: LLMs tend to generate `.md` files in root, polluting the repository structure.
