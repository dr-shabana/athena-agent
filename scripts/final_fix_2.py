#!/usr/bin/env python3
"""Final targeted fixes for remaining hermes references."""
from pathlib import Path
import re

repo = Path(r"C:\Users\USER\athena-agent")

files = list(repo.rglob("*.py"))
files = [f for f in files if all(p not in str(f) for p in [
    ".git", "__pycache__", "node_modules", ".egg-info", "venv"
])]

replacements = [
    # Logger names
    (r'getLogger\("hermes\.', 'getLogger("cortex.'),
    (r'getLogger\("hermes_', 'getLogger("cortex_'),
    # CLI command refs in f-strings
    (r"'athena config set", "'athena config set"),
    (r"'athena skills install", "'athena skills install"),
    (r"'athena curator", "'athena curator"),
    (r"'athena model", "'athena model"),
    (r"'athena setup", "'athena setup"),
    (r"'athena auth", "'athena auth"),
    (r"athena config set", "athena config set"),
    (r"athena skills install", "athena skills install"),
    (r"athena curator", "athena curator"),
    (r"athena-lcm", "athena-lcm"),
    (r"\bhermes-acp\b", "athena-acp"),
    # Docstring refs
    (r'a cortex tool', 'a cortex tool'),
    (r'a cortex tool', 'a cortex tool'),
    (r'cortex tool invocation', 'cortex tool invocation'),
    (r'cortex tool', 'cortex tool'),
    (r'cortex compressor', 'cortex compressor'),
    # Comment refs
    (r'cortex tools', 'cortex tools'),
    (r'A second cortex', 'A second cortex'),
    (r'cortex state', 'cortex state'),
    # remaining backtick refs
    (r'`athena `', '`athena `'),
    (r"`athena `", "`athena `"),
    (r'`athena`', '`athena`'),
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

print(f"Fixed {changed} more files")

# Count remaining bare 'hermes' (excluding test files, model names)
remaining_files = set()
for filepath in files:
    text = filepath.read_text(encoding="utf-8", errors="ignore")
    for m in re.finditer(r'\bhermes\b', text.lower()):
        ctx = text[max(0, m.start()-20):m.end()+30]
        # Skip model names
        if re.search(r'hermes\s+\d', ctx, re.I):
            continue
        # Skip protocol identifiers  
        if '_meta.hermes' in ctx or 'athena-acp' in ctx:
            continue
        if 'hermes_' in ctx or '_hermes' in ctx:
            continue
        # Skip if it's a Python import path (but we should have renamed these)
        if 'import hermes' in ctx:
            continue
        remaining_files.add(str(filepath))

print(f"Files with remaining 'hermes' refs (excluding tests, models, protocol): {len(remaining_files)}")
for f in sorted(remaining_files)[:20]:
    print(f"  {f}")
