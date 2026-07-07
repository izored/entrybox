"""Characterization tests for app/agents.py annotation read/write.

Run from github/:  python -m unittest discover -s tests -v

These pin the CURRENT behavior of the only code that writes into the user's
real agent config files. Test the pure block functions only — never the
learned-agent helpers, which mutate global state.
"""
import tempfile
import unittest
from pathlib import Path

from app.agents import (
    build_annotation, write_annotation, remove_annotation, annotation_status,
)

MD_AGENT = {
    "id": "claude-code", "name": "Claude Code", "config_file": "CLAUDE.md",
    "start_marker": "<!-- EntryBox -->", "end_marker": "<!-- /EntryBox -->",
    "template": "markdown", "built_in": True,
}
COMMENT_AGENT = {
    "id": "cursor", "name": "Cursor", "config_file": ".cursorrules",
    "start_marker": "# EntryBox", "end_marker": "# /EntryBox",
    "template": "comment", "built_in": True,
}
PROJECT = {"id": "tst", "name": "Test", "prefix": "TST"}


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.cfg = self.dir / "CLAUDE.md"


class TestWriteFresh(Base):
    def test_write_creates_file_with_markers(self):
        ann = build_annotation(MD_AGENT, PROJECT)
        write_annotation(MD_AGENT, PROJECT, self.cfg, ann)
        text = self.cfg.read_text(encoding="utf-8")
        self.assertIn("<!-- EntryBox -->", text)
        self.assertIn("<!-- /EntryBox -->", text)
        self.assertEqual(annotation_status(MD_AGENT, self.cfg), "marked")

    def test_status_none_when_absent(self):
        self.assertEqual(annotation_status(MD_AGENT, self.dir / "missing.md"), "none")

    def test_write_creates_nested_parent(self):
        nested = self.dir / ".github" / "copilot-instructions.md"
        agent = dict(MD_AGENT, config_file=".github/copilot-instructions.md")
        write_annotation(agent, PROJECT, nested, build_annotation(agent, PROJECT))
        self.assertTrue(nested.exists())


class TestReRegister(Base):
    def test_second_write_replaces_in_place(self):
        ann = build_annotation(MD_AGENT, PROJECT)
        self.cfg.write_text("# My project\n\nSome notes.\n", encoding="utf-8")
        write_annotation(MD_AGENT, PROJECT, self.cfg, ann)
        write_annotation(MD_AGENT, PROJECT, self.cfg, ann)  # again
        text = self.cfg.read_text(encoding="utf-8")
        self.assertEqual(text.count("<!-- EntryBox -->"), 1, "duplicate block written")
        self.assertEqual(text.count("<!-- /EntryBox -->"), 1)
        self.assertIn("Some notes.", text)  # user content preserved


class TestLegacyAdoption(Base):
    def test_legacy_block_is_adopted_not_duplicated(self):
        # Hand-written, marker-less block — note the heading text the pattern matches.
        self.cfg.write_text(
            "# My project\n\n## EntryBox Integration\n\nold hand-written notes\n",
            encoding="utf-8",
        )
        self.assertEqual(annotation_status(MD_AGENT, self.cfg), "legacy")
        write_annotation(MD_AGENT, PROJECT, self.cfg, build_annotation(MD_AGENT, PROJECT))
        text = self.cfg.read_text(encoding="utf-8")
        self.assertEqual(annotation_status(MD_AGENT, self.cfg), "marked")
        self.assertEqual(text.count("<!-- EntryBox -->"), 1)
        self.assertIn("# My project", text)  # content before the legacy block kept
        self.assertNotIn("old hand-written notes", text)  # legacy block replaced


class TestRemove(Base):
    def test_remove_marked_keeps_surrounding(self):
        self.cfg.write_text("# Top\n\n", encoding="utf-8")
        write_annotation(MD_AGENT, PROJECT, self.cfg, build_annotation(MD_AGENT, PROJECT))
        self.assertTrue(remove_annotation(MD_AGENT, self.cfg))
        text = self.cfg.read_text(encoding="utf-8")
        self.assertNotIn("<!-- EntryBox -->", text)
        self.assertIn("# Top", text)

    def test_remove_absent_file_returns_false(self):
        self.assertFalse(remove_annotation(MD_AGENT, self.dir / "nope.md"))

    def test_comment_agent_write_then_remove(self):
        cfg = self.dir / ".cursorrules"
        write_annotation(COMMENT_AGENT, PROJECT, cfg, build_annotation(COMMENT_AGENT, PROJECT))
        self.assertEqual(annotation_status(COMMENT_AGENT, cfg), "marked")
        self.assertTrue(remove_annotation(COMMENT_AGENT, cfg))
        self.assertEqual(annotation_status(COMMENT_AGENT, cfg), "none")


if __name__ == "__main__":
    unittest.main(verbosity=2)
