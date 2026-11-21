#!/usr/bin/env python3
"""Require a traceable root-file review record for every tracked root path.

This checks inventory completeness only. It does not declare any reviewed file
functionally correct, free of vulnerabilities, or fully understood.
"""

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs" / "audits" / "root-file-review-register.md"
ROW_PATTERN = re.compile(r"^\| `([^`]+)` \|", re.MULTILINE)


def indexed_root_paths(root=ROOT):
    result = subprocess.run(
        ["git", "ls-files", "--stage", "-z"],
        cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    paths = set()
    for item in result.stdout.split(b"\0"):
        if not item:
            continue
        _, path = item.split(b"\t", 1)
        name = path.decode("utf-8", "surrogateescape")
        if "/" not in name:
            paths.add(name)
    return paths


def review_paths(text):
    names = ROW_PATTERN.findall(text)
    return set(names), len(names) - len(set(names))


def check(root=ROOT, register=REGISTER):
    if not register.is_file():
        return ["Root-file review register is missing"]
    content = register.read_text(encoding="utf-8")
    reviewed, duplicated = review_paths(content)
    tracked = indexed_root_paths(root)
    errors = []
    if duplicated:
        errors.append(f"Duplicate review register rows: {duplicated}")
    missing = sorted(tracked - reviewed)
    stale = sorted(reviewed - tracked)
    if missing:
        errors.append("Unreviewed tracked root paths: " + ", ".join(missing))
    if stale:
        errors.append("Stale review paths no longer tracked at root: " + ", ".join(stale))
    if "not a line-by-line correctness audit" not in content.lower():
        errors.append("Register must explicitly state its limited evidence tier")
    return errors


if __name__ == "__main__":
    failures = check()
    for failure in failures:
        print("FAIL:", failure, file=sys.stderr)
    if failures:
        raise SystemExit(1)
    print(f"PASS: root file review register matches {len(indexed_root_paths())} indexed root entries")
    print("LIMIT: inventory completeness is not semantic verification or integration testing")
