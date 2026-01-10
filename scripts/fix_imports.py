#!/usr/bin/env python3
"""
Automatically fix import statements in project files
----------------------------------------------------

Run this from the project root directory.
"""

import re
from pathlib import Path


def fix_imports_in_file(filepath):
    """Fix imports in a single file."""

    print(f"Checking {filepath}...")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Fix patterns
    fixes = [
        # from tools.xxx import -> from src.tools.xxx import
        (r"from tools\.(\w+) import", r"from src.tools.\1 import"),
        # from agent.xxx import -> from src.agent.xxx import
        (r"from agent\.(\w+) import", r"from src.agent.\1 import"),
        # import tools.xxx -> import src.tools.xxx
        (r"import tools\.(\w+)", r"import src.tools.\1"),
        # import agent.xxx -> import src.agent.xxx
        (r"import agent\.(\w+)", r"import src.agent.\1"),
    ]

    changes_made = False

    for pattern, replacement in fixes:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            changes_made = True
            print(f"  ✓ Fixed: {pattern}")
        content = new_content

    if changes_made:
        # Backup original file
        backup_path = filepath.with_suffix(".py.backup")
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(original_content)
        print(f"  📦 Backed up to {backup_path}")

        # Write fixed content
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✅ Fixed imports in {filepath}")

        return True
    else:
        print(f"  ℹ️  No changes needed")
        return False


def main():
    """Main execution."""

    print("=" * 70)
    print("AUTO-FIX IMPORT STATEMENTS")
    print("=" * 70)
    print()

    # Files to check
    files_to_check = [
        "src/agent/planner.py",
        "src/agent/executor.py",
        "src/agent/orchestrator.py",
        "src/tools/tool_mapping.py",
        "src/tools/analysis.py",
        "src/tools/visualization.py",
    ]

    # Also check mapping.py if it exists
    if Path("src/tools/mapping.py").exists():
        files_to_check.append("src/tools/mapping.py")

    total_fixed = 0

    for file_path in files_to_check:
        path = Path(file_path)

        if not path.exists():
            print(f"⚠️  {file_path} not found, skipping...")
            continue

        if fix_imports_in_file(path):
            total_fixed += 1

        print()

    print("=" * 70)

    if total_fixed > 0:
        print(f"✅ Fixed imports in {total_fixed} file(s)")
        print()
        print("Original files backed up with .backup extension")
        print()
        print("Now try running your app:")
        print("  streamlit run app.py")
    else:
        print("ℹ️  No import fixes needed")

    print("=" * 70)


if __name__ == "__main__":
    main()
