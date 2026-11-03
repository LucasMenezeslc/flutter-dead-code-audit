#!/usr/bin/env python3
"""Build read-only import/export/part reachability evidence for Dart repositories.

This intentionally reports candidates rather than declaring dead code. It uses
only the Python standard library and writes JSON to stdout.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path


DIRECTIVE_RE = re.compile(r"^[ \t]*(?:import|export|part)\s+(.+?);", re.DOTALL | re.MULTILINE)
URI_RE = re.compile(r"['\"]([^'\"]+\.dart(?:\?[^'\"]*)?)['\"]")
PART_OF_RE = re.compile(r"^[ \t]*part\s+of\b", re.MULTILINE)
PACKAGE_NAME_RE = re.compile(r"(?m)^name\s*:\s*([A-Za-z0-9_\-]+)\s*(?:#.*)?$")
GENERATED_SUFFIXES = (
    ".g.dart",
    ".freezed.dart",
    ".gr.dart",
    ".gen.dart",
    ".mocks.dart",
    ".config.dart",
    ".chopper.dart",
)
IGNORED_DIRS = {".dart_tool", ".git", "build", ".idea", ".vscode"}


def strip_comments(text: str) -> str:
    """Replace Dart comments with whitespace while preserving strings/newlines."""
    output: list[str] = []
    index = 0
    quote: str | None = None
    triple = False
    block_depth = 0
    line_comment = False
    while index < len(text):
        char = text[index]
        pair = text[index : index + 2]
        trio = text[index : index + 3]
        if line_comment:
            if char == "\n":
                line_comment = False
                output.append(char)
            else:
                output.append(" ")
            index += 1
            continue
        if block_depth:
            if pair == "/*":
                block_depth += 1
                output.extend("  ")
                index += 2
            elif pair == "*/":
                block_depth -= 1
                output.extend("  ")
                index += 2
            else:
                output.append("\n" if char == "\n" else " ")
                index += 1
            continue
        if quote:
            output.append(char)
            if triple and trio == quote * 3:
                output.extend(text[index + 1 : index + 3])
                index += 3
                quote = None
                triple = False
            elif not triple and char == "\\" and index + 1 < len(text):
                output.append(text[index + 1])
                index += 2
            elif not triple and char == quote:
                quote = None
                index += 1
            else:
                index += 1
            continue
        if pair == "//":
            line_comment = True
            output.extend("  ")
            index += 2
        elif pair == "/*":
            block_depth = 1
            output.extend("  ")
            index += 2
        elif char in {"'", '"'}:
            quote = char
            triple = trio == char * 3
            if triple:
                output.extend(trio)
                index += 3
            else:
                output.append(char)
                index += 1
        else:
            output.append(char)
            index += 1
    return "".join(output)


def relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def is_ignored(path: Path, root: Path) -> bool:
    rel_parts = path.resolve().relative_to(root.resolve()).parts
    return any(part in IGNORED_DIRS for part in rel_parts)


def collect_dart_files(root: Path) -> list[Path]:
    scan_roots = ["lib", "bin", "tool", "test", "integration_test", "example"]
    files: set[Path] = set()
    for name in scan_roots:
        base = root / name
        if not base.exists():
            continue
        for path in base.rglob("*.dart"):
            if path.is_file() and not is_ignored(path, root):
                files.add(path.resolve())
    return sorted(files)


def package_name(root: Path) -> str | None:
    pubspec = root / "pubspec.yaml"
    if not pubspec.is_file():
        return None
    match = PACKAGE_NAME_RE.search(pubspec.read_text(encoding="utf-8", errors="replace"))
    return match.group(1) if match else None


def resolve_uri(source: Path, uri: str, root: Path, package: str | None) -> Path | None:
    uri = uri.split("?", 1)[0]
    if uri.startswith("dart:"):
        return None
    if uri.startswith("package:"):
        body = uri[len("package:") :]
        pkg, sep, rest = body.partition("/")
        if sep and package and pkg == package:
            return (root / "lib" / rest).resolve()
        return None
    if ":" in uri:
        return None
    return (source.parent / uri).resolve()


def read_graph(files: list[Path], root: Path, package: str | None):
    known = set(files)
    edges: dict[Path, set[Path]] = {path: set() for path in files}
    unresolved: list[dict[str, str]] = []
    part_of: set[Path] = set()
    for source in files:
        text = strip_comments(source.read_text(encoding="utf-8", errors="replace"))
        if PART_OF_RE.search(text):
            part_of.add(source)
        for directive in DIRECTIVE_RE.findall(text):
            for uri in URI_RE.findall(directive):
                target = resolve_uri(source, uri, root, package)
                if target is None:
                    continue
                if target in known:
                    edges[source].add(target)
                else:
                    unresolved.append({"source": relative(source, root), "uri": uri})
    return edges, unresolved, part_of


def reachable(roots: set[Path], edges: dict[Path, set[Path]]) -> set[Path]:
    seen: set[Path] = set()
    queue = deque(path for path in roots if path in edges)
    while queue:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        queue.extend(edges[current] - seen)
    return seen


def classify_roots(files: list[Path], root: Path, package: str | None):
    runtime: set[Path] = set()
    top_level_lib: set[Path] = set()
    auxiliary: set[Path] = set()
    for path in files:
        rel = relative(path, root)
        if re.fullmatch(r"lib/main(?:_[^/]+)?\.dart", rel) or rel.startswith("bin/"):
            runtime.add(path)
        elif re.fullmatch(r"lib/[^/]+\.dart", rel):
            top_level_lib.add(path)
        elif rel.startswith(("tool/", "test/", "integration_test/", "example/")):
            auxiliary.add(path)
    # Packages without an executable entrypoint can expose multiple top-level
    # libraries. Applications normally expose only their conventional barrel,
    # when present; other top-level files remain candidates that require the
    # external-consumer check from the skill.
    if runtime:
        conventional_barrel = root / "lib" / f"{package}.dart" if package else None
        public = {path for path in top_level_lib if conventional_barrel and path == conventional_barrel.resolve()}
    else:
        public = set(top_level_lib)
        runtime = set(public)
    return runtime, public, auxiliary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    if not (root / "pubspec.yaml").is_file():
        parser.error("pubspec.yaml not found under project root")

    files = collect_dart_files(root)
    package = package_name(root)
    edges, unresolved, part_of = read_graph(files, root, package)
    runtime_roots, public_roots, auxiliary_roots = classify_roots(files, root, package)
    runtime_seen = reachable(runtime_roots, edges)
    public_seen = reachable(runtime_roots | public_roots, edges)
    auxiliary_seen = reachable(auxiliary_roots, edges)

    inbound: dict[Path, set[Path]] = defaultdict(set)
    for source, targets in edges.items():
        for target in targets:
            inbound[target].add(source)

    generated = {path for path in files if path.name.endswith(GENERATED_SUFFIXES)}
    roots = runtime_roots | public_roots | auxiliary_roots
    lib_files = {path for path in files if relative(path, root).startswith("lib/")}
    no_inbound = lib_files - set(inbound) - roots - part_of - generated
    test_only = (auxiliary_seen - public_seen) & lib_files
    unreachable = lib_files - public_seen - auxiliary_seen - roots - part_of - generated
    public_only = (public_seen - runtime_seen) & lib_files - public_roots

    def rels(paths: set[Path]) -> list[str]:
        return sorted(relative(path, root) for path in paths)

    result = {
        "package_name": package,
        "notice": "Graph evidence only. Every candidate requires false-positive checks.",
        "summary": {
            "dart_files": len(files),
            "graph_edges": sum(len(targets) for targets in edges.values()),
            "runtime_roots": len(runtime_roots),
            "public_roots": len(public_roots),
            "auxiliary_roots": len(auxiliary_roots),
            "unresolved_local_directives": len(unresolved),
        },
        "roots": {
            "runtime": rels(runtime_roots),
            "public_api": rels(public_roots),
            "auxiliary": rels(auxiliary_roots),
        },
        "candidates": {
            "no_inbound_directive": rels(no_inbound),
            "unreachable_from_known_roots": rels(unreachable),
            "reachable_only_from_auxiliary_roots": rels(test_only),
            "reachable_from_public_api_but_not_runtime": rels(public_only),
        },
        "generated_files_excluded_from_candidates": rels(generated),
        "unresolved_local_directives": sorted(unresolved, key=lambda item: (item["source"], item["uri"])),
    }
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
