#!/usr/bin/env python3
"""Check active documentation claims against tracked source, without importing applications."""
import ast
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ROUTES = {
    ("GET", "/"), ("GET", "/api/integration/status"),
    ("GET", "/api/cognitive/status"), ("POST", "/api/cognitive/analyze"),
    ("GET", "/api/multi-agent/status"), ("POST", "/api/multi-agent/execute-workflow"),
}
EXPECTED_COMMANDS = {
    "neuralblitz.boot", "neuralblitz.execute", "neuralblitz.status",
    "neuralblitz.debug.start", "neuralblitz.debug.step",
    "neuralblitz.debug.continue", "neuralblitz.introspect",
    "neuralblitz.ck.search", "neuralblitz.ck.documentation",
    "neuralblitz.credentials.set", "neuralblitz.credentials.clear",
}
DANGEROUS_CLAIMS = (
    "world's most comprehensive", "24.11s → 0.000s", "95% test coverage",
    "quantum supremacy", "quantum-resistant security", "10,000+ devices",
    "sub-millisecond inference", "256+ reality simulation",
)

def read(root, path):
    return (root / path).read_text(encoding="utf-8")

def check_links(root, path, body):
    issues = []
    for match in re.finditer(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", body):
        target = match.group(1).split("#")[0].split("?")[0].strip()
        if not target or target.startswith(("https://", "http://", "mailto:")):
            continue
        absolute = (root / path).parent.joinpath(target).resolve()
        if not absolute.is_relative_to(root.resolve()) or not absolute.exists():
            issues.append(path + ": broken local link: " + target)
    return issues

def check(root=ROOT):
    issues = []
    docs = {}
    for filename in ("README.md", "README_SIMPLE.md", "docs/README.md", "docs/readme-claim-audit.md", "docs/API_REFERENCE.md"):
        try:
            docs[filename] = read(root, filename)
            issues.extend(check_links(root, filename, docs[filename]))
        except OSError as exc:
            issues.append("Missing evidence document: " + str(exc))
    main = docs.get("README.md", "")
    index = docs.get("docs/README.md", "")
    for name, text in (("Root README", main), ("Documentation index", index), ("Quick start", docs.get("README_SIMPLE.md", "")), ("API reference", docs.get("docs/API_REFERENCE.md", ""))):
        if "pre-production" not in text[:800].lower():
            issues.append(name + " must declare pre-production status near top")
        for phrase in DANGEROUS_CLAIMS:
            if phrase in text.lower():
                issues.append(name + " includes unsupported product claim: " + phrase)
    try:
        manifest = json.loads(read(root, "package.json"))["contributes"]
        if {x["id"] for x in manifest["languages"]} != {"nbcl", "reflexaellang", "lon"}:
            issues.append("Language manifest changed; README must be revalidated")
        if {x["command"] for x in manifest["commands"]} != EXPECTED_COMMANDS:
            issues.append("Command manifest changed; README must be revalidated")
        if {x["id"] for group in manifest["views"].values() for x in group} != {
            "neuralblitzGoldenDAG", "neuralblitzCKRegistry"
        }:
            issues.append("View manifest changed; README must be revalidated")
        for snippet in ("three language", "eleven commands", "two contributed tree views"):
            if snippet not in main:
                issues.append("Missing supported extension claim: " + snippet)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        issues.append("Manifest inspection failed: " + str(exc))
    try:
        module = ast.parse(read(root, "main.py"))
        routes = set()
        backend_fail_closed = False
        for fn in ast.walk(module):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in fn.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                    owner = decorator.func.value
                    if isinstance(owner, ast.Name) and owner.id == "app":
                        method = decorator.func.attr.upper()
                        if method in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
                            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                                routes.add((method, decorator.args[0].value))
            if fn.name == "execute_multi_agent_workflow":
                backend_fail_closed = any(
                    isinstance(node, ast.Call) and any(
                        kw.arg == "status_code" and isinstance(kw.value, ast.Constant)
                        and kw.value.value == 501 for kw in node.keywords
                    ) for node in ast.walk(fn)
                )
        documented = set(re.findall(
            r"^\|\s*(GET|POST)\s*\|\s*\x60([^\x60]+)\x60\s*\|$", main, re.M
        ))
        if routes != EXPECTED_ROUTES or documented != routes:
            issues.append("README API route table differs from main.py")
        if not backend_fail_closed:
            issues.append("Workflow endpoint no longer has explicit HTTP 501 guard")
        documented_api = re.findall(r"^\|\s*(GET|POST)\s*\|\s*`([^`]+)`\s*\|", docs.get("docs/API_REFERENCE.md", ""), re.M)
        if set(documented_api) != routes or len(documented_api) != len(routes):
            issues.append("Current API reference route table differs from main.py")
    except (OSError, SyntaxError) as exc:
        issues.append("Gateway inspection failed: " + str(exc))
    try:
        compose = read(root, "docker-compose.yml")
        for name in ("INFLUXDB", "TIMESCALEDB", "PROMETHEUS", "GRAFANA", "NODE_EXPORTER", "CADVISOR"):
            expected = chr(36) + "{" + name + "_BIND_ADDRESS:-127.0.0.1}"
            if expected not in compose:
                issues.append("Root Compose localhost bind drift: " + name)
        if "privileged: true" not in compose:
            issues.append("cAdvisor privilege warning must be reassessed")
    except OSError as exc:
        issues.append("Compose inspection failed: " + str(exc))
    for workflow, markers in {
        ".github/workflows/production-gates.yml": (
            "bun run compile", "bun run lint", "bun run test", "unittest discover"
        ),
        ".github/workflows/vscode-vsix-candidate.yml": (
            "bun build", "vscode_candidate.py verify", "sha256sum", "upload-artifact"
        ),
    }.items():
        try:
            text = read(root, workflow)
            for marker in markers:
                if marker not in text:
                    issues.append("Workflow has no documented check: " + workflow + ": " + marker)
        except OSError as exc:
            issues.append("Workflow missing: " + str(exc))
    try:
        archive = read(root, "docs/history/README-legacy-2026-11-21.md")
        original_title = "# 🚀 OpenCode LRS - The Ultimate AI Development Ecosystem"
        if not archive.startswith("> **ARCHIVED, UNVERIFIED") or original_title not in archive:
            issues.append("Original README not preserved with truthful warning")
        else:
            original_lines = archive[archive.index(original_title):].split("\n")
            with (root / "docs/audits/readme-legacy-claim-inventory.tsv").open(encoding="utf-8") as file:
                rows = list(csv.DictReader(
                    (line for line in file if not line.startswith("#")), delimiter="\t"
                ))
            if len(original_lines) != 2941 or len(rows) != 239:
                issues.append("Original claim register changed; rescan required")
            for row in rows:
                n = int(row["legacy_line"])
                if not (1 <= n <= len(original_lines)):
                    issues.append("Invalid original line: " + str(n))
                    continue
                actual = original_lines[n-1].strip().replace("|", " ").replace("\t", " ")[:280]
                if actual != row["text"]:
                    issues.append("Original claim mismatch at line: " + str(n))
                if row["verification_status"] != "not-verified-as-product":
                    issues.append("Historical claim promoted without audited evidence")
    except (OSError, ValueError, csv.Error, KeyError) as exc:
        issues.append("Claim provenance inspection failed: " + str(exc))
    return issues

if __name__ == "__main__":
    results = check()
    for failure in results:
        print("FAIL: " + failure, file=sys.stderr)
    if results:
        sys.exit(1)
    print("PASS: README links, source contracts, CI boundaries, and legacy provenance")
    print("LIMIT: this is not a production, scientific, or benchmark certification")
