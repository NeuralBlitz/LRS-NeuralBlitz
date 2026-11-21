#!/usr/bin/env python3
"""Read every checked-out tracked file blob and produce an inspectable static audit.

This inventories *all* Git-index entries. Gitlinks are recorded as unresolved
submodules; generated HTML/binary data is read but not treated as source code.
It does NOT execute arbitrary repository scripts or validate research claims.
"""
import argparse
import ast
from collections import Counter
import csv
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CLAIM_WORDS = (
    "production-ready", "production ready", "fully functional", "100% coverage",
    "95% test coverage", "quantum supremacy", "quantum-resistant",
    "validated quantum", "world's most advanced", "unlimited scalability",
    "complete implementation", "fully integrated", "10,000+",
    "0.000s", "sub-millisecond inference",
)
GENERATED_PREFIXES = (
    "htmlcov/", ".pytest_cache/", ".ruff_cache/", "demo_cache/"
)
GENERATED_FILES = {".coverage", "neuralblitz-v50/python/neuralblitz_v50.db"}
MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdx"}
SIMPLE_LINK_RE = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)")
SUSPECT_SECRET_RE = re.compile(
    r"(?im)^\s*(?:api_key|secret_key|access_token|password|private_key)\s*"
    r"(?:=|:)\s*['\"]?([^\s#'\"]{8,})"
)

def git_entries(root):
    result = subprocess.run(
        ["git", "ls-files", "--stage", "-z"], cwd=root,
        capture_output=True, check=True
    )
    entries = []
    for entry in result.stdout.split(b"\0"):
        if not entry:
            continue
        header, raw_path = entry.split(b"\t", 1)
        mode, sha, stage = header.decode("ascii").split(" ")
        entries.append({
            "path": raw_path.decode("utf-8", "surrogateescape"),
            "mode": mode, "sha": sha, "stage": stage
        })
    return entries

def local_link_issues(path, content, all_paths):
    problems = []
    base = Path(path).parent
    for m in SIMPLE_LINK_RE.finditer(content):
        target = m.group(1).strip().split("#", 1)[0].split("?", 1)[0]
        if not target or target.startswith(("https://", "http://", "mailto:", "data:")):
            continue
        if target.startswith("/"):
            problems.append("absolute-path-link")
            continue
        parts = []
        for p in (base / target).parts:
            if p == "..":
                if parts:
                    parts.pop()
                else:
                    problems.append("link-escapes-repository")
                    parts = []
                    break
            elif p != ".":
                parts.append(p)
        if parts and "/".join(parts) not in all_paths:
            # A Markdown link can target a directory, not necessarily a blob.
            if not any(x.startswith("/".join(parts) + "/") for x in all_paths):
                problems.append("missing-local-link")
    return problems

def inspect_blob(path, data, all_paths):
    row = {
        "path": path, "bytes": len(data), "kind": "text",
        "lines": 0, "claim_markers": 0, "broken_local_links": 0,
        "validation_error": "", "flags": [],
    }
    if path.startswith(GENERATED_PREFIXES) or path in GENERATED_FILES:
        row["flags"].append("tracked-generated-or-cache")
    if b"\0" in data[:8192]:
        row["kind"] = "binary"
        return row
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        row["kind"] = "binary-or-non-utf8"
        return row
    row["lines"] = text.count("\n") + int(bool(text) and not text.endswith("\n"))
    low = text.lower()
    if path.lower().endswith(tuple(MARKDOWN_EXTENSIONS)):
        row["kind"] = "markdown"
        row["claim_markers"] = sum(low.count(marker) for marker in CLAIM_WORDS)
        issues = local_link_issues(path, text, all_paths)
        row["broken_local_links"] = len(issues)
        if issues:
            row["flags"].append("check-markdown-links")
        if row["claim_markers"]:
            row["flags"].append("unverified-marketing-term-review")
        if len(text.strip()) < 240:
            row["flags"].append("placeholder-or-brief-document")
    elif path.endswith(".py"):
        row["kind"] = "python"
        try:
            ast.parse(text, filename=path)
        except (SyntaxError, ValueError) as exc:
            row["validation_error"] = "python-syntax:" + str(getattr(exc, "lineno", "?"))
    elif path.endswith((".json", ".ipynb")):
        row["kind"] = "json"
        try:
            json.loads(text)
        except ValueError:
            row["validation_error"] = "invalid-json"
    elif path.endswith((".html", ".htm")):
        row["kind"] = "html"
    elif path.endswith((".ts", ".tsx", ".js", ".cjs")):
        row["kind"] = "javascript-or-typescript"
    elif path.endswith((".yml", ".yaml", ".toml", ".sh", ".sql", ".rs", ".go")):
        row["kind"] = "config-or-source"
    if path == "AGENTS.md":
        row["flags"].append("large-agent-instructions-not-executable-policy")
    if SUSPECT_SECRET_RE.search(text):
        row["flags"].append("possible-embedded-credential-review-privately")
    return row

def audit_repo(root=ROOT):
    entries = git_entries(root)
    all_paths = {x["path"] for x in entries}
    rows = []
    for item in entries:
        path = item["path"]
        if item["mode"] == "160000":
            rows.append({
                "path": path, "bytes": 0, "kind": "gitlink-unreadable",
                "lines": 0, "claim_markers": 0, "broken_local_links": 0,
                "validation_error": "",
                "flags": ["uninitialized-submodule-reference"],
            })
            continue
        try:
            data = (root / path).read_bytes()
            rows.append(inspect_blob(path, data, all_paths))
        except OSError:
            rows.append({
                "path": path, "bytes": 0, "kind": "unreadable",
                "lines": 0, "claim_markers": 0, "broken_local_links": 0,
                "validation_error": "tracked-file-not-readable",
                "flags": ["investigate-index-file-mismatch"],
            })
    return rows

def build_summary(rows):
    kinds = Counter(x["kind"] for x in rows)
    flag_counts = Counter(flag for r in rows for flag in r["flags"])
    return {
        "tracked_entries": len(rows),
        "kinds": dict(sorted(kinds.items())),
        "flags": dict(sorted(flag_counts.items())),
        "unreadable_files": [x["path"] for x in rows if x["kind"] == "unreadable"],
        "gitlinks": [x["path"] for x in rows if x["kind"] == "gitlink-unreadable"],
        "syntactic_errors": [
            {"path": x["path"], "error": x["validation_error"]}
            for x in rows if x["validation_error"]
        ],
        "markdown_link_issues": sum(r["broken_local_links"] for r in rows),
        "unverified_claim_marker_occurrences": sum(r["claim_markers"] for r in rows),
        "tracked_generated_or_cache_count": flag_counts["tracked-generated-or-cache"],
        "scope": (
            "Reads every tracked checkout blob and classifies all Git-index entries. "
            "Does not recursively read gitlinks, execute programs, validate third-party "
            "links, prove correctness, or test physical/scientific claims."
        ),
    }

def write_report(rows, output):
    output.mkdir(parents=True, exist_ok=True)
    fields = (
        "path", "bytes", "kind", "lines", "claim_markers",
        "broken_local_links", "validation_error", "flags"
    )
    with (output / "tracked-files.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                **r, "flags": ";".join(r["flags"])
            })
    summary = build_summary(rows)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("audit-output"))
    args = parser.parse_args()
    try:
        rows = audit_repo()
        summary = write_report(rows, args.out)
    except (OSError, subprocess.CalledProcessError) as exc:
        print("FAIL: Repository inventory could not be read: " + str(exc), file=sys.stderr)
        return 1
    print("Read/classified", summary["tracked_entries"], "tracked entries")
    print("Types:", summary["kinds"])
    print("Markdown link findings:", summary["markdown_link_issues"])
    print("Flagged claim markers:", summary["unverified_claim_marker_occurrences"])
    print("Embedded Git submodules not recursively inspected:", len(summary["gitlinks"]))
    print("Static syntax findings:", len(summary["syntactic_errors"]))
    if summary["unreadable_files"]:
        print("FAIL: tracked blobs were not readable", file=sys.stderr)
        return 1
    print("PASS: every checked-out tracked file was read and inventoried; static findings require review")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
