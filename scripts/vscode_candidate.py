#!/usr/bin/env python3
"""Stage and audit a minimal VS Code VSIX candidate.

This is a packaging safety check, not an Extension Host integration test.
Only the explicitly permitted extension runtime and assets enter the stage.
"""

import argparse
import json
from pathlib import Path
import shutil
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIRS = ("syntaxes", "snippets", "language-configurations")
ASSET_FILES = ("generated-icon.png", "LICENSE")
ALLOWED_EXTENSION_TOPLEVEL = set(ASSET_DIRS) | {
    "dist", "generated-icon.png", "LICENSE", "LICENSE.txt",
    "README.md", "readme.md", "package.json"
}


def stage_extension(destination: Path) -> None:
    destination = destination.resolve()
    if destination == ROOT or ROOT in destination.parents:
        raise ValueError("Stage must be outside the repository checkout")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Refusing to overwrite a non-empty stage")
    destination.mkdir(parents=True, exist_ok=True)
    for name in ASSET_DIRS:
        source = ROOT / name
        if not source.is_dir():
            raise ValueError(f"Missing extension asset directory: {name}")
        shutil.copytree(source, destination / name)
    for name in ASSET_FILES:
        source = ROOT / name
        if not source.is_file():
            raise ValueError(f"Missing extension asset: {name}")
        shutil.copy2(source, destination / name)
    readme = ROOT / "docs" / "vscode-candidate-readme.md"
    if not readme.is_file():
        raise ValueError("Missing curated VSIX README")
    shutil.copy2(readme, destination / "README.md")

    manifest = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    # The source package remains unchanged. The actual candidate uses a
    # self-contained Bun bundle, not root-relative unbundled out/ modules.
    manifest["main"] = "./dist/extension.js"
    manifest.pop("scripts", None)  # Prevent vsce from invoking prepublish in stage
    manifest.pop("devDependencies", None)
    manifest.pop("dependencies", None)  # All runtime dependencies are bundled
    manifest["license"] = "MIT"
    manifest["repository"] = {
        "type": "git",
        "url": "https://github.com/NeuralBlitz/LRS-NeuralBlitz",
    }
    (destination / "package.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def verify_candidate(vsix: Path) -> None:
    if not vsix.is_file():
        raise ValueError("VSIX candidate missing")
    with zipfile.ZipFile(vsix) as archive:
        names = set(archive.namelist())
        if archive.testzip() is not None:
            raise ValueError("VSIX contains a corrupt archive entry")

        required = {
            "extension/package.json",
            "extension/dist/extension.js",
            "extension/readme.md",
            "extension/LICENSE.txt",
            "extension/generated-icon.png",
            "extension.vsixmanifest",
        }
        missing = required - names
        if missing:
            raise ValueError(f"Candidate is missing essential files: {sorted(missing)}")

        for item in names:
            if item.endswith("/"):
                continue
            if not item.startswith("extension/"):
                if item not in {"extension.vsixmanifest", "[Content_Types].xml"}:
                    raise ValueError(f"Unexpected VSIX archive metadata: {item}")
                continue
            rel = item.removeprefix("extension/")
            head = rel.split("/")[0]
            if head not in ALLOWED_EXTENSION_TOPLEVEL:
                raise ValueError(f"Unapproved VSIX content: {rel}")
            if head == "dist":
                if rel != "dist/extension.js":
                    raise ValueError(f"Unexpected compiled asset: {rel}")
            elif head in {"syntaxes", "snippets", "language-configurations"}:
                if len(rel.split("/")) < 2:
                    raise ValueError(f"Unexpected asset folder entry: {rel}")
            elif rel not in ALLOWED_EXTENSION_TOPLEVEL:
                raise ValueError(f"Unapproved extension-root asset: {rel}")

        manifest = json.loads(archive.read("extension/package.json"))
        if manifest.get("main") != "./dist/extension.js":
            raise ValueError("Candidate entrypoint does not match the bundled runtime")
        if manifest.get("dependencies") or manifest.get("devDependencies"):
            raise ValueError("Candidate unexpectedly requires external Node dependencies")
        if len(archive.read("extension/dist/extension.js")) < 100:
            raise ValueError("Bundled runtime is unexpectedly small")
        contributions = manifest.get("contributes", {})
        referenced_paths = [
            manifest.get("main"),
            *[item.get("path") for item in contributions.get("grammars", [])],
            *[item.get("configuration") for item in contributions.get("languages", [])],
            *[item.get("path") for item in contributions.get("snippets", [])],
            *[item.get("icon") for container in contributions.get("viewsContainers", {}).values()
              for item in container],
        ]
        for path in referenced_paths:
            if not isinstance(path, str) or not path:
                raise ValueError("Manifest contains an invalid asset reference")
            normalized = path.removeprefix("./")
            member = "extension/" + normalized
            if member not in names:
                raise ValueError(f"Manifest references missing packaged asset: {normalized}")
            if normalized.endswith(".json"):
                try:
                    json.loads(archive.read(member))
                except (ValueError, UnicodeDecodeError) as exc:
                    raise ValueError(
                        f"Invalid JSON content in packaged extension asset: {normalized}"
                    ) from exc
        if len([x for x in names if x.startswith("extension/")]) > 150:
            raise ValueError("Too many files in this minimal VSIX candidate")
    print(f"VSIX archive validated: {vsix.name} (minimal declared assets only)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("stage", "verify"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        if args.operation == "stage":
            stage_extension(args.path)
            print("Prepared minimal VSIX staging directory")
        else:
            verify_candidate(args.path)
    except (ValueError, OSError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"VSIX candidate check failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
