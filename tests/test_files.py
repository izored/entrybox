"""Security tests for the sandboxed path resolver (app/files.py).

The whole local file-read surface trusts resolve_in_root() to refuse escapes.
If any of these fail, a request could read outside the project root.
"""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

_FILES_PY = Path(__file__).resolve().parent.parent / "app" / "files.py"
_spec = importlib.util.spec_from_file_location("eb_files_under_test", _FILES_PY)
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)


class TestResolveInRoot(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
        (self.root / "secret.txt").write_text("top", encoding="utf-8")

    def test_allows_file_in_root(self):
        self.assertIsNotNone(F.resolve_in_root(self.root, "secret.txt"))

    def test_allows_nested_file(self):
        r = F.resolve_in_root(self.root, "src/app.py")
        self.assertIsNotNone(r)
        self.assertEqual(r.read_text(encoding="utf-8"), "x = 1\n")

    def test_rejects_dotdot_escape(self):
        self.assertIsNone(F.resolve_in_root(self.root, "../../etc/passwd"))
        self.assertIsNone(F.resolve_in_root(self.root, "src/../../outside.txt"))

    def test_rejects_absolute(self):
        self.assertIsNone(F.resolve_in_root(self.root, "/etc/passwd"))

    def test_rejects_drive_qualified(self):
        # Windows drive paths must not slip through on any platform.
        self.assertIsNone(F.resolve_in_root(self.root, "C:\\Windows\\system.ini"))

    def test_rejects_none(self):
        self.assertIsNone(F.resolve_in_root(self.root, None))

    def test_rejects_nonexistent_root(self):
        self.assertIsNone(F.resolve_in_root(self.root / "nope", "x"))

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unsupported")
    def test_rejects_symlink_escape(self):
        outside = Path(tempfile.mkdtemp())
        (outside / "loot.txt").write_text("loot", encoding="utf-8")
        link = self.root / "link"
        try:
            os.symlink(outside, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("cannot create symlink in this environment")
        self.assertIsNone(F.resolve_in_root(self.root, "link/loot.txt"))


class TestBuildTree(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("x", encoding="utf-8")
        (self.root / "node_modules").mkdir()
        (self.root / "node_modules" / "junk.js").write_text("y", encoding="utf-8")
        (self.root / ".git").mkdir()
        (self.root / ".env").write_text("SECRET=1", encoding="utf-8")
        (self.root / "README.md").write_text("hi", encoding="utf-8")

    def _names(self, node):
        out = {node["name"]}
        for c in node.get("children", []):
            out |= self._names(c)
        return out

    def test_skips_ignored_and_dotfiles(self):
        tree = F.build_tree(self.root)
        names = self._names(tree)
        self.assertIn("README.md", names)
        self.assertIn("app.py", names)
        self.assertNotIn("node_modules", names)
        self.assertNotIn(".git", names)
        self.assertNotIn(".env", names)

    def test_paths_are_relposix(self):
        tree = F.build_tree(self.root)
        src = next(c for c in tree["children"] if c["name"] == "src")
        appf = next(c for c in src["children"] if c["name"] == "app.py")
        self.assertEqual(appf["path"], "src/app.py")


if __name__ == "__main__":
    unittest.main(verbosity=2)
