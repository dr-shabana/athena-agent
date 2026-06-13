#!/usr/bin/env python3
"""Final fix for remaining hermes references in CLI help text and paths."""
from pathlib import Path
import re

repo = Path(r"C:\Users\USER\athena-agent")

# Files with remaining hermes references (non-test, non-protocol)
files = list(repo.rglob("*.py"))
files = [f for f in files if all(p not in str(f) for p in [
    ".git", "__pycache__", "node_modules", ".egg-info", "venv",
    "test_", "tests/"
])]

replacements = [
    # CLI command refs in help text / error messages
    (r'`athena update`', '`athena update`'),
    (r'`athena postinstall`', '`athena postinstall`'),
    (r'`athena acp`', '`athena acp`'),
    (r'`athena model`', '`athena model`'),
    (r'`athena setup`', '`athena setup`'),
    (r'`athena config', '`athena config'),
    (r'`athena auth`', '`athena auth`'),
    (r'`athena auth`', '`athena auth`'),
    (r'`athena auth\.', '`athena auth.'),
    (r'`athena `', '`athena `'),
    # Double backtick variants
    (r'``athena update``', '``athena update``'),
    (r'``athena postinstall``', '``athena postinstall``'),
    (r'``athena acp``', '``athena acp``'),
    (r'``athena model``', '``athena model``'),
    (r'``athena setup``', '``athena setup``'),
    (r'``athena config', '``athena config'),
    (r'``athena auth``', '``athena auth``'),
    # Quoted
    (r'`athena`', '`athena`'),
    (r'\'hermes \'', "'athena '"),
    # Path refs
    (r'~/.cortex', '~/.cortex'),
    # In-string CLI refs
    (r'Run: athena ', 'Run: athena '),
    (r'run: athena ', 'run: athena '),
    (r'with `athena ', "with `athena "),
    (r'via `athena ', "via `athena "),
    (r'with ``athena ', "with ``athena "),
    # f-string refs
    (r'\`athena ', '`athena '),
    (r"`athena `", "`athena `"),
    # Code references
    (r'athena tools', 'athena tools'),
    (r'athena setup', 'athena setup'),
    (r'athena model', 'athena model'),
]

changed = 0
for filepath in files:
    try:
        text = filepath.read_text(encoding="utf-8", errors="ignore")
    except:
        continue
    original = text
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    if text != original:
        filepath.write_text(text, encoding="utf-8")
        changed += 1

print(f"Fixed {changed} files with remaining hermes CLI/path references")

# Verify
remaining = 0
for filepath in files:
    text = filepath.read_text(encoding="utf-8", errors="ignore")
    # Count hermes as standalone word (not in module names we've already renamed)
    matches = re.findall(r'\bhermes\b', text)
    # Filter out module imports that have been renamed
    filtered = [m for m in matches 
                if 'hermes_' not in text[text.find(m)-10:text.find(m)+20]
                and 'hermes.' not in text[text.find(m)-5:text.find(m)+15]
                and '_hermes' not in text[text.find(m)-15:text.find(m)+10]]
    remaining += len(filtered)

print(f"Remaining bare 'hermes' refs: {remaining}")
