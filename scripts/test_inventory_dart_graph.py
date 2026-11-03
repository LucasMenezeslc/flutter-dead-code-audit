#!/usr/bin/env python3
"""Behavior tests for inventory_dart_graph.py."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("inventory_dart_graph.py")


class InventoryTest(unittest.TestCase):
    def run_inventory(self, files: dict[str, str]):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        for name, content in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        completed = subprocess.run(
            ["python3", str(SCRIPT), str(root)],
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        self.assertNotIn("project_root", result)
        self.assertNotIn(str(root), completed.stdout)
        return result

    def test_classifies_orphan_test_only_and_generated_files(self):
        result = self.run_inventory(
            {
                "pubspec.yaml": "name: sample_app\n",
                "lib/main.dart": "import 'live.dart';\nvoid main() {}\n",
                "lib/live.dart": "part 'live.g.dart';\nclass Live {}\n",
                "lib/live.g.dart": "part of 'live.dart';\n",
                "lib/orphan.dart": "class Orphan {}\n",
                "lib/test_helper.dart": "class TestHelper {}\n",
                "test/main_test.dart": "import 'package:sample_app/test_helper.dart';\n",
            }
        )
        candidates = result["candidates"]
        self.assertIn("lib/orphan.dart", candidates["no_inbound_directive"])
        self.assertIn("lib/orphan.dart", candidates["unreachable_from_known_roots"])
        self.assertIn("lib/test_helper.dart", candidates["reachable_only_from_auxiliary_roots"])
        self.assertIn("lib/live.g.dart", result["generated_files_excluded_from_candidates"])
        self.assertNotIn("lib/live.dart", candidates["unreachable_from_known_roots"])

    def test_follows_all_conditional_import_targets(self):
        result = self.run_inventory(
            {
                "pubspec.yaml": "name: conditional_app\n",
                "lib/main.dart": (
                    "import 'src/stub.dart'\n"
                    "  if (dart.library.io) 'src/io.dart'\n"
                    "  if (dart.library.html) 'src/web.dart';\n"
                    "void main() {}\n"
                ),
                "lib/src/stub.dart": "class Backend {}\n",
                "lib/src/io.dart": "class Backend {}\n",
                "lib/src/web.dart": "class Backend {}\n",
            }
        )
        unreachable = result["candidates"]["unreachable_from_known_roots"]
        self.assertNotIn("lib/src/stub.dart", unreachable)
        self.assertNotIn("lib/src/io.dart", unreachable)
        self.assertNotIn("lib/src/web.dart", unreachable)

    def test_library_without_main_protects_top_level_public_libraries(self):
        result = self.run_inventory(
            {
                "pubspec.yaml": "name: public_package\n",
                "lib/public_package.dart": "export 'src/api.dart';\n",
                "lib/secondary.dart": "class SecondaryApi {}\n",
                "lib/src/api.dart": "class Api {}\n",
            }
        )
        self.assertEqual(
            ["lib/public_package.dart", "lib/secondary.dart"],
            result["roots"]["public_api"],
        )
        self.assertEqual([], result["candidates"]["unreachable_from_known_roots"])

    def test_ignores_directives_inside_comments(self):
        result = self.run_inventory(
            {
                "pubspec.yaml": "name: comments_app\n",
                "lib/main.dart": (
                    "// import 'line_comment.dart';\n"
                    "/*\n  import 'block_comment.dart';\n*/\n"
                    "const text = \"// import 'string.dart';\";\n"
                    "void main() {}\n"
                ),
                "lib/line_comment.dart": "class LineComment {}\n",
                "lib/block_comment.dart": "class BlockComment {}\n",
                "lib/string.dart": "class StringMention {}\n",
            }
        )
        candidates = result["candidates"]["unreachable_from_known_roots"]
        self.assertIn("lib/line_comment.dart", candidates)
        self.assertIn("lib/block_comment.dart", candidates)
        self.assertIn("lib/string.dart", candidates)


if __name__ == "__main__":
    unittest.main()
