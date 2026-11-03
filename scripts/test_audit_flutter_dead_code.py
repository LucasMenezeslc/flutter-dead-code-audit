#!/usr/bin/env python3
"""Behavior tests for audit_flutter_dead_code.py."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_flutter_dead_code.py")


class AuditTest(unittest.TestCase):
    def test_combines_machine_diagnostics_and_file_graph(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lib").mkdir()
            (root / "pubspec.yaml").write_text("name: audit_app\n", encoding="utf-8")
            (root / "lib/main.dart").write_text("void main() {}\n", encoding="utf-8")
            (root / "lib/orphan.dart").write_text("class Orphan {}\n", encoding="utf-8")
            fake_dart = root / "fake-dart"
            fake_dart.write_text(
                "#!/bin/sh\n"
                f"printf '%s\\n' 'INFO|HINT|UNUSED_ELEMENT|{root}/lib/main.dart|1|1|4|Unused element'\n"
                "exit 2\n",
                encoding="utf-8",
            )
            fake_dart.chmod(0o755)

            completed = subprocess.run(
                ["python3", str(SCRIPT), str(root), "--dart", str(fake_dart)],
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            result = json.loads(completed.stdout)
            self.assertNotIn("project_root", result)
            self.assertNotIn(str(root), completed.stdout)
            self.assertEqual(
                ["dart", "analyze", "--format=machine", "."],
                result["analyzer"]["command"],
            )
            self.assertEqual("UNUSED_ELEMENT", result["analyzer"]["candidates"][0]["code"])
            self.assertEqual(2, result["analyzer"]["exit_code"])
            self.assertIn(
                "lib/orphan.dart",
                result["file_graph"]["candidates"]["unreachable_from_known_roots"],
            )
            self.assertIn(
                "file:unreachable_from_known_roots:lib/orphan.dart",
                result["review"]["unreviewed_keys"],
            )

    def test_runs_inventory_when_dart_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lib").mkdir()
            (root / "pubspec.yaml").write_text("name: no_dart_app\n", encoding="utf-8")
            (root / "lib/main.dart").write_text("void main() {}\n", encoding="utf-8")
            completed = subprocess.run(
                ["/usr/bin/python3", str(SCRIPT), str(root)],
                check=True,
                capture_output=True,
                text=True,
                env={"PATH": "/usr/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            )
            result = json.loads(completed.stdout)
            self.assertFalse(result["analyzer"]["available"])
            self.assertEqual(1, result["file_graph"]["summary"]["dart_files"])

    def test_joins_retained_and_stale_review_decisions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lib").mkdir()
            (root / "pubspec.yaml").write_text("name: review_app\n", encoding="utf-8")
            (root / "lib/main.dart").write_text("void main() {}\n", encoding="utf-8")
            (root / "lib/legacy.dart").write_text("class Legacy {}\n", encoding="utf-8")
            candidate_key = "file:unreachable_from_known_roots:lib/legacy.dart"
            decisions = root / "decisions.json"
            decisions.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "decisions": [
                            {
                                "key": candidate_key,
                                "disposition": "retain",
                                "reason": "Rollback path",
                                "review_after": "2000-01-01",
                            },
                            {
                                "key": "file:no_inbound_directive:lib/gone.dart",
                                "disposition": "defer",
                                "reason": "Waiting for owner",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                ["/usr/bin/python3", str(SCRIPT), str(root), "--decisions", str(decisions)],
                check=True,
                capture_output=True,
                text=True,
                env={"PATH": "/usr/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            )
            review = json.loads(completed.stdout)["review"]
            self.assertEqual("decisions.json", review["decisions_file"])
            self.assertNotIn(str(root), completed.stdout)
            self.assertEqual(candidate_key, review["matched"][0]["key"])
            self.assertTrue(review["matched"][0]["review_due"])
            self.assertEqual(1, len(review["due_for_review"]))
            self.assertEqual(1, len(review["stale_decisions"]))
            self.assertNotIn(candidate_key, review["unreviewed_keys"])

    def test_rejects_retention_without_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lib").mkdir()
            (root / "pubspec.yaml").write_text("name: invalid_review_app\n", encoding="utf-8")
            (root / "lib/main.dart").write_text("void main() {}\n", encoding="utf-8")
            decisions = root / "decisions.json"
            decisions.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "decisions": [
                            {
                                "key": "file:no_inbound_directive:lib/example.dart",
                                "disposition": "retain",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                ["/usr/bin/python3", str(SCRIPT), str(root), "--decisions", str(decisions)],
                capture_output=True,
                text=True,
                env={"PATH": "/usr/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            )
            self.assertNotEqual(0, completed.returncode)
            self.assertIn("retain decision requires a reason", completed.stderr)


if __name__ == "__main__":
    unittest.main()
