#!/usr/bin/env python3
"""Collect dependency-free Dart dead-code candidates as JSON.

Combines the Dart SDK analyzer's machine output with the bundled Dart directive
graph. It never edits the target repository and does not claim candidates are
safe to delete.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
INVENTORY_SCRIPT = SCRIPT_DIR / "inventory_dart_graph.py"
DEAD_CODE_DIAGNOSTICS = {
    "DEAD_CODE",
    "DEAD_NULL_AWARE_EXPRESSION",
    "UNREACHABLE_SWITCH_CASE",
    "UNUSED_CATCH_CLAUSE",
    "UNUSED_CATCH_STACK",
    "UNUSED_ELEMENT",
    "UNUSED_FIELD",
    "UNUSED_IMPORT",
    "UNUSED_LABEL",
    "UNUSED_LOCAL_VARIABLE",
    "UNUSED_RESULT",
    "UNUSED_SHOWN_NAME",
}


def find_dart(root: Path, override: str | None) -> str | None:
    if override:
        candidate = Path(override).expanduser()
        return str(candidate.resolve()) if candidate.exists() else shutil.which(override)
    fvm_dart = root / ".fvm" / "flutter_sdk" / "bin" / "dart"
    if fvm_dart.is_file():
        return str(fvm_dart.resolve())
    return shutil.which("dart")


def run_inventory(root: Path) -> dict:
    completed = subprocess.run(
        [sys.executable, str(INVENTORY_SCRIPT), str(root)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def parse_machine_diagnostics(output: str, root: Path) -> tuple[list[dict], int]:
    candidates: list[dict] = []
    malformed = 0
    for raw_line in output.splitlines():
        if not raw_line.strip():
            continue
        fields = raw_line.split("|", 7)
        if len(fields) != 8:
            malformed += 1
            continue
        severity, diagnostic_type, code, file_name, line, column, length, message = fields
        if code.upper() not in DEAD_CODE_DIAGNOSTICS:
            continue
        path = Path(file_name)
        try:
            display_path = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            display_path = str(path)
        candidates.append(
            {
                "code": code.upper(),
                "severity": severity,
                "diagnostic_type": diagnostic_type,
                "path": display_path,
                "line": int(line) if line.isdigit() else line,
                "column": int(column) if column.isdigit() else column,
                "length": int(length) if length.isdigit() else length,
                "message": message.replace("\\|", "|"),
            }
        )
    candidates.sort(key=lambda item: (str(item["path"]), int(item["line"]), str(item["code"])))
    return candidates, malformed


def run_analyzer(root: Path, dart: str | None) -> dict:
    if not dart:
        return {
            "available": False,
            "reason": "Dart executable not found; graph inventory still ran.",
            "candidates": [],
        }
    command = [dart, "analyze", "--format=machine", str(root)]
    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    candidates, malformed = parse_machine_diagnostics(completed.stdout, root)
    return {
        "available": True,
        "command": ["dart", "analyze", "--format=machine", "."],
        "exit_code": completed.returncode,
        "candidates": candidates,
        "candidate_count": len(candidates),
        "unparsed_stdout_lines": malformed,
        "stderr": completed.stderr.replace(str(root), ".").strip(),
    }


def candidate_index(analyzer: dict, inventory: dict) -> list[dict]:
    index: list[dict] = []
    for item in analyzer.get("candidates", []):
        key = f"analyzer:{item['code']}:{item['path']}:{item['line']}:{item['column']}"
        index.append(
            {
                "key": key,
                "source": "analyzer",
                "kind": item["code"],
                "path": item["path"],
                "line": item["line"],
            }
        )
    for category, paths in inventory.get("candidates", {}).items():
        for path in paths:
            index.append(
                {
                    "key": f"file:{category}:{path}",
                    "source": "file_graph",
                    "kind": category,
                    "path": path,
                }
            )
    index.sort(key=lambda item: item["key"])
    return index


def load_review(decisions_path: Path | None, candidates: list[dict]) -> dict:
    candidate_keys = {item["key"] for item in candidates}
    if decisions_path is None:
        return {
            "decisions_file": None,
            "matched": [],
            "due_for_review": [],
            "stale_decisions": [],
            "unreviewed_keys": sorted(candidate_keys),
        }
    data = json.loads(decisions_path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("decisions"), list):
        raise ValueError("decisions file must contain version 1 and a decisions list")
    seen: set[str] = set()
    matched: list[dict] = []
    stale: list[dict] = []
    due: list[dict] = []
    today = date.today()
    for raw in data["decisions"]:
        if not isinstance(raw, dict):
            raise ValueError("each decision must be an object")
        key = raw.get("key")
        disposition = raw.get("disposition")
        reason = raw.get("reason", "")
        if not isinstance(key, str) or not key:
            raise ValueError("each decision requires a non-empty key")
        if key in seen:
            raise ValueError(f"duplicate decision key: {key}")
        seen.add(key)
        if disposition not in {"remove", "retain", "defer"}:
            raise ValueError(f"invalid disposition for {key}: {disposition}")
        if disposition in {"retain", "defer"} and (not isinstance(reason, str) or not reason.strip()):
            raise ValueError(f"{disposition} decision requires a reason: {key}")
        decision = dict(raw)
        review_after = decision.get("review_after")
        if review_after is not None:
            try:
                review_date = date.fromisoformat(review_after)
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid review_after for {key}: {review_after}") from error
            decision["review_due"] = review_date <= today
        else:
            decision["review_due"] = False
        if key in candidate_keys:
            matched.append(decision)
            if decision["review_due"]:
                due.append(decision)
        else:
            stale.append(decision)
    return {
        "decisions_file": decisions_path.name,
        "matched": sorted(matched, key=lambda item: item["key"]),
        "due_for_review": sorted(due, key=lambda item: item["key"]),
        "stale_decisions": sorted(stale, key=lambda item: item["key"]),
        "unreviewed_keys": sorted(candidate_keys - seen),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--dart", help="Dart executable path or command name")
    parser.add_argument("--decisions", type=Path, help="Optional JSON review decisions file")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    if not (root / "pubspec.yaml").is_file():
        parser.error("pubspec.yaml not found under project root")

    inventory = run_inventory(root)
    analyzer = run_analyzer(root, find_dart(root, args.dart))
    candidates = candidate_index(analyzer, inventory)
    try:
        review = load_review(args.decisions, candidates)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))
    result = {
        "notice": (
            "Candidate evidence only. Public APIs, dynamic registrations, generated code, "
            "flavors, platforms, and external consumers require manual checks before removal."
        ),
        "analyzer": analyzer,
        "file_graph": inventory,
        "candidate_index": candidates,
        "review": review,
    }
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
