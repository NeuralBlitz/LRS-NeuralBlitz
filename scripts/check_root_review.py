#!/usr/bin/env python3
"""Require an explicit evidence entry for every tracked root-level file.

The recorded blob hashes must match the checked-out revision. This forces
root-level source changes to update their review entry rather than silently
reuse stale inspection evidence. This is not a functional correctness proof.
"""
import csv
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "audits" / "root-file-review.csv"

def tracked_root():
    result = subprocess.run(
        ["git", "ls-files", "--stage", "-z"],
        cwd=ROOT, capture_output=True, check=True,
    )
    entries = {}
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        header, raw_path = raw.split(b"\t", 1)
        mode, sha, stage = header.decode("ascii").split(" ")
        path = raw_path.decode("utf-8", "surrogateescape")
        if "/" in path:
            continue
        if stage != "0":
            raise ValueError("Unmerged Git index entry: " + path)
        entries[path] = (mode, sha)
    return entries

def check_review():
    expected = tracked_root()
    with LEDGER.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    errors = []
    names = [row["path"] for row in rows]
    if len(names) != len(set(names)):
        errors.append("Duplicate root-file review entry")
    if set(names) != set(expected):
        errors.append(
            "Root review coverage drift — missing=" +
            repr(sorted(set(expected) - set(names))) +
            " unexpected=" + repr(sorted(set(names) - set(expected)))
        )
    for row in rows:
        path = row["path"]
        if path not in expected:
            continue
        mode, sha = expected[path]
        if row["git_mode"] != mode or row["blob_sha"] != sha:
            errors.append(
                "Root file has changed since its reviewed blob: " + path +
                "; update the evidence note and SHA after review"
            )
        if not row["observed_role_or_issue"].strip() or not row["inspection_scope"].strip():
            errors.append("Missing review explanation for " + path)
        if mode == "160000" and "not" not in row["inspection_scope"].lower():
            errors.append("Gitlink incorrectly marked as fully inspected: " + path)
        if mode == "120000" and "not" not in row["inspection_scope"].lower():
            errors.append("Symlink incorrectly marked as fully inspected: " + path)
    return errors, len(expected)

def main():
    try:
        problems, count = check_review()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print("Root review could not be checked:", str(exc), file=sys.stderr)
        return 1
    for issue in problems:
        print("FAIL: " + issue, file=sys.stderr)
    if problems:
        return 1
    print("PASS:", count, "root-level Git-tracked entries matched reviewed content hashes")
    print("LIMIT: a review ledger is not proof of runtime behavior or scientific validity")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
