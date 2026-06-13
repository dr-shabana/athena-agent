#!/usr/bin/env python3
"""
Athena Rebranding Engine
========================
Systematically transforms Athena Agent → Athena Agent (by Dr. Shabana).

Renames every file, directory, import, constant, config key, env var,
and user-facing string.  Two passes:
  1. Content substitutions across all text files.
  2. Filesystem renames (files + directories).

Usage:
    python scripts/rebrand_to_athena.py

Run from the repo root (athena-agent/).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.chdir(REPO)

# ── Mapping tables ────────────────────────────────────────────────────

# (old_package_name, new_package_name)  — used for import rewrites
PACKAGE_NAMES: list[tuple[str, str, str]] = [
    # (old_import, new_import, safe_substring_check)
    ("cortex_state",    "cortex_state",    "cortex_state"),
    ("cortex_logging",  "cortex_logging",  "cortex_logging"),
    ("cortex_constants","cortex_constants","cortex_constants"),
    ("cortex_time",     "cortex_time",     "cortex_time"),
    ("cortex_bootstrap","cortex_bootstrap","cortex_bootstrap"),
    ("cortex_cli",      "cortex_cli",      "cortex_cli"),
]

# Content replacements — ordered so longer/more-specific matches go first
# (old_text, new_text)
CONTENT_REPLACEMENTS: list[tuple[str, str]] = [
    # ── Package identity ──
    ('name="athena-agent"',            'name="athena-agent"'),
    ('name="athena-agent"',            'name="athena-agent"'),
    ("'athena-agent'",                 "'athena-agent'"),
    ('"athena-agent"',                 '"athena-agent"'),
    ("athena-agent",                   "athena-agent"),
    ("cortex_agent.",                  "cortex_agent."),
    ("cortex_agent",                   "cortex_agent"),

    # ── CLI command ──
    ('"athena"',                       '"athena"'),
    ("'athena'",                       "'athena'"),

    # ── Env vars (all-caps) ──
    ("CORTEX_HOME",                    "CORTEX_HOME"),
    ("CORTEX_YOLO_MODE",               "CORTEX_YOLO_MODE"),
    ("CORTEX_REDACT_SECRETS",          "CORTEX_REDACT_SECRETS"),
    ("CORTEX_KANBAN_TASK",             "CORTEX_KANBAN_TASK"),
    ("CORTEX_KANBAN_BOARD",            "CORTEX_KANBAN_BOARD"),

    # ── Config paths ──
    ("~/.cortex/",                     "~/.cortex/"),
    ("~/.cortex/",                     "~/.cortex/"),  # no-op guard
    ("$CORTEX_HOME",                   "$CORTEX_HOME"),
    ("get_cortex_home()",              "get_cortex_home()"),
    ("CORTEX_HOME =",                  "CORTEX_HOME ="),
    ("cortex_home",                    "cortex_home"),

    # ── Constants and sentinels ──
    ("cortex.constants",               "cortex.constants"),
    ("cortex.state",                   "cortex.state"),
    ("cortex.logging",                 "cortex.logging"),
    ("cortex.time",                    "cortex.time"),
    ("cortex.bootstrap",               "cortex.bootstrap"),

    # ── User-facing branding ──
    ("Athena Agent",                   "Athena Agent"),
    ("Athena agent",                   "Athena agent"),
    ("athena agent",                   "athena agent"),
    ("!Athena",                        "!Athena"),
    ("\"Athena\"",                     "\"Athena\""),
    ("'Athena'",                       "'Athena'"),
    ("Athena Agent",           "Athena Agent"),
    ("dr-shabana/athena-agent",      "dr-shabana/athena-agent"),
    ("dr-shabana/",                  "dr-shabana/"),  # careful — keep for attribution
    ("github.com/dr-shabana/athena-agent", "github.com/dr-shabana/athena-agent"),

    # ── Internal references ──
    ("cortex.constants",               "cortex.constants"),
    ("cortex.state",                   "cortex.state"),
    ("cortex.logging",                 "cortex.logging"),
    ("cortex.time",                    "cortex.time"),
    ("cortex.bootstrap",               "cortex.bootstrap"),
]

# Files / dirs to rename (old_name, new_name)
FILESYSTEM_RENAMES: list[tuple[str, str]] = [
    ("cortex_constants.py",   "cortex_constants.py"),
    ("cortex_state.py",       "cortex_state.py"),
    ("cortex_logging.py",     "cortex_logging.py"),
    ("cortex_time.py",        "cortex_time.py"),
    ("cortex_bootstrap.py",   "cortex_bootstrap.py"),
    ("cortex_cli",            "cortex_cli"),
    ("cortex_agent.egg-info", "cortex_agent.egg-info"),
    ("hermes-already-has-routines.md", "athena-already-has-routines.md"),
]

# Directories to exclude from content search
EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv",
                ".egg-info", "cortex_agent.egg-info", "cortex_agent.egg-info"}

# File extensions to process for content replacements
TEXT_EXTENSIONS = {".py", ".md", ".yaml", ".yml", ".toml", ".cfg", ".ini",
                   ".json", ".html", ".css", ".js", ".ts", ".tsx", ".sh",
                   ".bat", ".ps1", ".txt", ".env", ".sample", ".example",
                   ".dockerignore", ".gitignore", ".gitattributes"}


# ── Helpers ───────────────────────────────────────────────────────────

def _is_text_file(path: Path) -> bool:
    return path.suffix in TEXT_EXTENSIONS


def _should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
        # Skip hidden dirs under site-packages / egg-info
        if part.startswith(".") and part != ".env" and part != ".github":
            if path.is_dir():
                return True
    return False


def content_replace(file_path: Path, dry_run: bool = False) -> int:
    """Apply CONTENT_REPLACEMENTS to a file. Returns number of changes."""
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 0

    original = text
    for old, new in CONTENT_REPLACEMENTS:
        # Use word-boundary-aware replacement for short tokens
        if len(old) <= 8 and old.isidentifier():
            text = re.sub(r'\b' + re.escape(old) + r'\b', new, text)
        else:
            text = re.sub(re.escape(old), new, text)

    if text != original:
        if not dry_run:
            file_path.write_text(text, encoding="utf-8")
        return 1
    return 0


def rename_imports(file_path: Path, dry_run: bool = False) -> int:
    """Rename Python import paths (hermes_xxx → cortex_xxx)."""
    if file_path.suffix != ".py":
        return 0

    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 0

    original = text
    for old_import, new_import, _ in PACKAGE_NAMES:
        # Match import statements and from-imports
        text = re.sub(
            r'\b' + re.escape(old_import) + r'\b',
            new_import,
            text,
        )

    if text != original:
        if not dry_run:
            file_path.write_text(text, encoding="utf-8")
        return 1
    return 0


def rename_filesystem(dry_run: bool = False) -> list[tuple[str, str, bool]]:
    """Rename files and directories. Returns [(old, new, success)]."""
    results: list[tuple[str, str, bool]] = []
    for old_name, new_name in FILESYSTEM_RENAMES:
        # Search whole repo for matching leaf names
        for path in REPO.rglob(old_name):
            if _should_skip(path):
                continue
            new_path = path.parent / new_name
            if path.exists() and not new_path.exists():
                if dry_run:
                    results.append((str(path), str(new_path), True))
                else:
                    try:
                        path.rename(new_path)
                        results.append((str(path), str(new_path), True))
                    except OSError as e:
                        results.append((str(path), str(new_path), False))
                        print(f"  ⚠  Rename failed: {e}", file=sys.stderr)
    return results


def update_setup_files(dry_run: bool = False) -> None:
    """Special handling for setup.py / pyproject.toml metadata."""
    for fname in ("setup.py", "pyproject.toml"):
        path = REPO / fname
        if not path.exists():
            continue
        content_replace(path, dry_run=dry_run)
        rename_imports(path, dry_run=dry_run)


def write_attribution(dry_run: bool = False) -> None:
    """Add attribution header to README.md."""
    readme = REPO / "README.md"
    if not readme.exists():
        return

    text = readme.read_text(encoding="utf-8", errors="ignore")
    attribution = (
        "\n---\n\n"
        "*Athena Agent is based on [Athena Agent](https://github.com/dr-shabana/athena-agent) "
        "by Nous Research, modified and maintained by Dr. Shabana "
        "([Neurova AI](https://github.com/dr-shabana/Neurova)).*\n"
    )
    if "based on" not in text.lower():
        text += attribution
        if not dry_run:
            readme.write_text(text, encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────

def main(dry_run: bool = False) -> None:
    print("═" * 60)
    print("  Athena Rebranding Engine")
    print(f"  {'[DRY RUN]' if dry_run else '[LIVE]'}")
    print("═" * 60)
    print(f"  Repo: {REPO}")
    print()

    # Phase 1: Content replacements in all text files
    print("Phase 1 — Content replacements ...")
    content_changed = 0
    import_changed = 0
    file_count = 0

    for path in sorted(REPO.rglob("*")):
        if not path.is_file():
            continue
        if _should_skip(path):
            continue

        file_count += 1
        if _is_text_file(path):
            c = content_replace(path, dry_run=dry_run)
            i = rename_imports(path, dry_run=dry_run)
            if c:
                content_changed += 1
            if i:
                import_changed += 1

        # Progress indicator every 500 files
        if file_count % 500 == 0:
            print(f"  ... {file_count} files scanned")

    print(f"  Content replacements: {content_changed} files modified")
    print(f"  Import rewrites:      {import_changed} files modified")
    print(f"  Total files scanned:  {file_count}")
    print()

    # Phase 2: Filesystem renames
    print("Phase 2 — File / directory renames ...")
    results = rename_filesystem(dry_run=dry_run)
    success = [r for r in results if r[2]]
    failed = [r for r in results if not r[2]]
    print(f"  {len(success)} renamed, {len(failed)} failed")
    if failed:
        for old, new, _ in failed:
            print(f"    ✗ {old} → {new}")

    # Phase 3: Special files
    print("Phase 3 — Special metadata ...")
    update_setup_files(dry_run=dry_run)
    write_attribution(dry_run=dry_run)
    print("  setup.py / pyproject.toml updated")
    print("  Attribution added to README.md")
    print()

    # Phase 4: Git operations
    print("Phase 4 — Git setup ...")
    if not dry_run:
        # Rename origin remote
        subprocess.run(
            ["git", "remote", "rename", "origin", "upstream"],
            cwd=REPO, capture_output=True,
        )
        # Add new origin pointing to Dr. Shabana's fork
        subprocess.run(
            ["git", "remote", "add", "origin",
             "https://github.com/dr-shabana/athena-agent.git"],
            cwd=REPO, capture_output=True,
        )
        print("  Remote 'upstream' → dr-shabana/athena-agent")
        print("  Remote 'origin'   → dr-shabana/athena-agent")
    else:
        print("  (dry run — skipped)")
    print()

    print("═" * 60)
    print("  Done.")
    if dry_run:
        print("  Run without --dry-run to apply changes.")
    print("═" * 60)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    main(dry_run=dry_run)
