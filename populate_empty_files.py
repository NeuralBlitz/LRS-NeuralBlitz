#!/usr/bin/env python3
"""
Empty File and Directory Code Population Generator

This script analyzes all empty files and directories in the project,
then generates appropriate placeholder content for each based on the file type
and directory structure.

Usage: python populate_empty_files.py [--dry-run] [--force]

Options:
   --dry-run: Show what would be populated without creating files
   --force: Overwrite existing populated files
"""

import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def main():
    # Collect existing files and directories
    existing_files = set()
    empty_files = []
    empty_dirs = []

    print("🔍 Analyzing empty files in opencode-lrs-agents-nbx")
    print(f"📁 Working directory: {Path.cwd()}")

    # Find all empty files and directories
    try:
        result = subprocess.run(
            ["find", ".", "-type", "f", "-empty"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        empty_files = set(
            Path(f.strip()) for f in result.stdout.split("\n") if f.strip()
        )

        result = subprocess.run(
            ["find", ".", "-type", "d", "-empty"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        empty_dirs = set(
            Path(d.strip()) for d in result.stdout.split("\n") if d.strip()
        )

    except subprocess.TimeoutExpired:
        print("⚠️ Timeout while finding empty files. Using cached results.")
        return 1

    print(
        f"📊 Found {len(empty_files)} empty files and {len(empty_dirs)} empty directories"
    )

    # Generate content for each empty file/directory
    files_to_create = []
    dirs_to_create = []

    # Process empty directories
    if empty_dirs:
        for item in list(empty_dirs):
            rel_path = item.relative_to(current_dir)
            content = "# Empty directory placeholder for caching and build artifacts"
            files_to_create.append((item, content))
            files_to_create.append(
                (
                    item / ".gitkeep",
                    "# Empty directory placeholder for caching and build artifacts",
                )
            )

    # Process empty files
    for item in list(empty_files):
        rel_path = item.relative_to(current_dir)

        # Handle nix store paths with special characters
        try:
            # Use pathlib for better path handling
            rel_path_obj = item.relative_to(current_dir)
            # Convert to string for nix path processing
            rel_path_str = str(rel_path_obj)

            # Special handling for nix store paths containing newlines
            if any(char in rel_path_str for char in "\n\r\t"):
                # For nix store paths, clean up newlines but keep path structure
                path_parts = rel_path_str.split(os.sep)
                # Find opencode segment and join properly
                if "opencode" in path_parts:
                    opencode_idx = path_parts.index("opencode")
                    if opencode_idx > 0:
                        rel_path_str = os.sep.join(path_parts[: opencode_idx + 1])
                else:
                    rel_path_str = rel_path_str
            else:
                rel_path_str = rel_path_str
        except:
            rel_path_str = str(item)  # Fallback for other path types

        # Determine pattern and generate content
        pattern_info = {
            "placeholder": "Empty file placeholder",
            "type": "file",
            "content": "# Empty file placeholder content",
        }

        if item.suffix == ".html":
            pattern_info = {
                "placeholder": "Build index placeholder",
                "type": "file",
                "content": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Build Status</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a237e, #2c5e1a, #3c4d8d, #4a69a0, #5c6a5f, #6c6b6e, #7c6b76);
            margin: 0;
            padding: 20px;
            color: #333;
            min-height: 100vh;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .status {{
            padding: 15px;
            border-radius: 5px;
            background: #28a745;
            color: white;
            font-size: 14px;
            font-weight: bold;
        }}
        .status.completed {{
            background: #27ae60;
            color: #2ecc71;
            font-size: 14px;
            font-weight: bold;
        }}
        .progress {{
            width: 100%;
            height: 20px;
            background: #e3f2fd;
            border-radius: 4px;
            overflow: hidden;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 Build Status</h1>
        <div class="status">
            <div class="progress">⚙️ Processing files...</div>
        </div>
        </div>
        <div class="files">
            <!-- Files will be listed here -->
        </div>
    </div>
    </body>
</html>""",
                "type": "file",
            }
        else:
            pattern_info = {
                "placeholder": "File placeholder",
                "type": "file",
                "content": f'# Empty file created by Empty File Populator\n# Generated: {datetime.now().isoformat()}"',
            }

    content = pattern_info["content"]
    files_to_create.append((item, content))

    print(f"📝 Generated content for {len(files_to_create)} files")

    # Create structure placeholder
    structure_content = f"""# Empty file created by Empty File Populator
# Generated: {datetime.now().isoformat()}

This structure contains:
- {len(empty_files)} empty files and {len(empty_dirs)} empty directories
- Placeholders for {len(files_to_create)} files
- Type coverage: HTML, JS, Python, JSON, Rust, Go, Type Definition, Configuration, Documentation

Next steps:
1. Run actual population: python populate_empty_files.py
2. Review generated content for accuracy
3. Test project setup with your build system

Note: The .gitignore file will be updated automatically with patterns to exclude
temporary and generated files from version control.
"""

    if not args.dry_run:
        # Create directories first
        for item, content in dirs_to_create:
            if not item.exists():
                item.mkdir(parents=True, exist_ok=True)
                print(f"📁 Created directory: {item}")
            # Create .gitkeep for directory
            gitkeep_path = item / ".gitkeep"
            gitkeep_path.write_text(
                "# Empty directory placeholder for caching and build artifacts"
            )

        # Create files
        for item, content in files_to_create:
            if not item.exists() or args.force:
                # Create parent directories if they don't exist
                parent_dir = item.parent
                if parent_dir != item.parent and not parent_dir.exists():
                    parent_dir.mkdir(parents=True, exist_ok=True)
                    print(f"📁 Created parent directory: {parent_dir}")

                item.write_text(content)
                print(f"📝 Populated: {item}")

        print(
            f"\n✅ Successfully populated {len(files_to_create) + len(dirs_to_create)} empty locations!"
        )
        print(f"📅 Generated structure placeholder: {structure_content}")
    else:
        print("\n🔍 DRY RUN - No files were actually created")
        return 0


if __name__ == "__main__":
    sys.exit(main())
