#!/usr/bin/env python3
"""Fail closed when a tracked gitlink lacks a matching safe upstream mapping.

This is a LOCAL static index/provenance check only. It does not clone or run
submodule code, check content safety, or prove that a remote remains online.
Current upstream repositories and exact pinned Git SHAs were independently
verified through GitHub's commit API on 2026-11-22.
"""
import configparser
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

# Approved URL mappings for the existing dependency paths. Any new mapping or
# upstream change requires an intentional policy update and review.
APPROVED = {
    "lrs_agents": "https://github.com/NeuralBlitz/lrs-agents",
    "neuralblitz-v50/Advanced-Research/Advanced-Research":
        "https://github.com/NeuralBlitz/Advanced-Research.git",
    "neuralblitz-v50/ComputationalAxioms/ComputationalAxioms":
        "https://github.com/NeuralBlitz/ComputationalAxioms.git",
    "neuralblitz-v50/Emergent-Prompt-Architecture/Emergent-Prompt-Architecture":
        "https://github.com/NeuralBlitz/Emergent-Prompt-Architecture.git",
}


def gitlinks_from_index(root=ROOT):
    result = subprocess.run(
        ["git", "ls-files", "--stage", "-z"], cwd=root, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    found = {}
    for entry in result.stdout.split(b"\0"):
        if not entry:
            continue
        meta, raw_path = entry.split(b"\t", 1)
        mode, sha, stage = meta.decode("ascii").split(" ")
        if mode != "160000":
            continue
        path = raw_path.decode("utf-8", errors="strict")
        if stage != "0":
            raise ValueError("Unmerged gitlink in the index: " + path)
        if path in found:
            raise ValueError("Repeated gitlink in the index: " + path)
        found[path] = sha
    return found


def parse_gitmodules(source):
    parser = configparser.RawConfigParser(strict=True)
    parser.read_string(source)
    records = {}
    for section in parser.sections():
        if not (section.startswith('submodule "') and section.endswith('"')):
            raise ValueError("Unexpected .gitmodules section: " + section)
        name = section[len('submodule "'):-1]
        if not parser.has_option(section, "path") or not parser.has_option(section, "url"):
            raise ValueError("Incomplete submodule entry: " + name)
        path = parser.get(section, "path")
        url = parser.get(section, "url")
        if not path or path in records or name != path:
            raise ValueError("Duplicate or mismatched submodule path/name: " + name)
        records[path] = url
    return records


def validate(records, gitlinks):
    errors = []
    declared = set(records)
    indexed = set(gitlinks)
    expected = set(APPROVED)

    for path in sorted(indexed - declared):
        errors.append("Gitlink has no .gitmodules mapping: " + path)
    for path in sorted(declared - indexed):
        errors.append(".gitmodules maps a path without a tracked gitlink: " + path)
    for path in sorted(indexed - expected):
        errors.append("Unapproved new Gitlink requires provenance review: " + path)
    for path in sorted(expected - indexed):
        errors.append("Approved Gitlink unexpectedly missing: " + path)

    for path, url in sorted(records.items()):
        pure = PurePosixPath(path)
        if pure.is_absolute() or '..' in pure.parts or '.' in pure.parts or not path:
            errors.append("Unsafe Gitlink path: " + path)
        if path not in APPROVED or url != APPROVED[path]:
            errors.append("Gitlink upstream must be an explicitly verified HTTPS URL: " + path)
    for path, sha in sorted(gitlinks.items()):
        if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
            errors.append("Invalid pinned Git object SHA for: " + path)
        if sha == "0" * 40:
            errors.append("Unset Gitlink pin: " + path)
    return errors


def check(root=ROOT):
    errors = []
    try:
        mapping = parse_gitmodules(
            (root / ".gitmodules").read_text(encoding="utf-8")
        )
        links = gitlinks_from_index(root)
        errors.extend(validate(mapping, links))
    except (OSError, ValueError, configparser.Error, subprocess.CalledProcessError) as exc:
        errors.append("Cannot verify .gitmodules against Git index: " + str(exc))
    return errors


def main():
    errors = check()
    for error in errors:
        print("FAIL:", error, file=sys.stderr)
    if errors:
        return 1
    print("PASS: all four pinned Gitlink paths have approved, explicit upstream mappings")
    print("LIMIT: submodule contents are not initialized, cloned, audited or executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
