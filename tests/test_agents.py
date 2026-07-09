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
    valid_custom_annotation,
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


class TestBrokenMarkers(Base):
    """Damaged marker topology → EntryBox must not touch the file at all.
    (Previously: an orphan start marker + a later appended block made the next
    write swallow every user line between them.)"""

    def _assert_untouched(self, content: str):
        self.cfg.write_text(content, encoding="utf-8")
        before = self.cfg.read_bytes()
        status = write_annotation(MD_AGENT, PROJECT, self.cfg, build_annotation(MD_AGENT, PROJECT))
        self.assertEqual(status, "skipped_broken")
        self.assertEqual(self.cfg.read_bytes(), before, "file must be byte-identical")
        self.assertFalse(remove_annotation(MD_AGENT, self.cfg))
        self.assertEqual(self.cfg.read_bytes(), before)
        self.assertEqual(annotation_status(MD_AGENT, self.cfg), "broken")

    def test_orphan_start_marker(self):
        self._assert_untouched("# Mine\n\n<!-- EntryBox -->\n\nMy own precious instructions.\n")

    def test_orphan_end_marker(self):
        self._assert_untouched("# Mine\n\n<!-- /EntryBox -->\n\nMy own precious instructions.\n")

    def test_reversed_markers(self):
        self._assert_untouched("<!-- /EntryBox -->\nuser text\n<!-- EntryBox -->\n")

    def test_duplicate_blocks(self):
        block = build_annotation(MD_AGENT, PROJECT)
        self._assert_untouched(block + "\nBETWEEN — user text that must survive\n\n" + block)

    def test_orphan_plus_full_block_does_not_swallow(self):
        # The historical worst case: stray start marker, user text, then a
        # complete block. The old regex replaced from the stray marker through
        # the block's end marker — user text gone.
        content = ("<!-- EntryBox -->\n\nUser notes that used to get swallowed.\n\n"
                   + build_annotation(MD_AGENT, PROJECT))
        self._assert_untouched(content)

    def test_marker_inside_longer_line_is_not_a_marker(self):
        # Line-anchored matching: prose mentioning the marker text must not count.
        self.cfg.write_text("Docs: the block sits between <!-- EntryBox --> and "
                            "<!-- /EntryBox --> markers.\n", encoding="utf-8")
        self.assertEqual(annotation_status(MD_AGENT, self.cfg), "none")
        status = write_annotation(MD_AGENT, PROJECT, self.cfg, build_annotation(MD_AGENT, PROJECT))
        self.assertEqual(status, "appended")
        self.assertIn("Docs: the block sits", self.cfg.read_text(encoding="utf-8"))


class TestLegacyAdoptionHardened(Base):
    def test_legacy_with_subheadings_fully_adopted(self):
        # Old pattern stopped at ANY heading — an inner ### left fragments.
        self.cfg.write_text(
            "# My project\n\n## EntryBox Integration\n\nintro text\n\n"
            "### Setting state\n\nlegacy detail\n\n## Testing\n\nuser section kept\n",
            encoding="utf-8",
        )
        self.assertEqual(annotation_status(MD_AGENT, self.cfg), "legacy")
        status = write_annotation(MD_AGENT, PROJECT, self.cfg, build_annotation(MD_AGENT, PROJECT))
        self.assertEqual(status, "adopted")
        text = self.cfg.read_text(encoding="utf-8")
        self.assertNotIn("legacy detail", text, "inner ### fragment left behind")
        self.assertNotIn("intro text", text)
        self.assertIn("## Testing", text)
        self.assertIn("user section kept", text)
        self.assertEqual(annotation_status(MD_AGENT, self.cfg), "marked")

    def test_plain_entrybox_heading_detected_as_legacy(self):
        # The block EntryBox generates is titled '## EntryBox' — a hand-written
        # copy without markers must be adopted, not duplicated (README promise).
        self.cfg.write_text("# My project\n\n## EntryBox\n\nhand-written copy\n", encoding="utf-8")
        self.assertEqual(annotation_status(MD_AGENT, self.cfg), "legacy")
        status = write_annotation(MD_AGENT, PROJECT, self.cfg, build_annotation(MD_AGENT, PROJECT))
        self.assertEqual(status, "adopted")
        text = self.cfg.read_text(encoding="utf-8")
        self.assertEqual(text.count("## EntryBox\n"), 1)
        self.assertNotIn("hand-written copy", text)

    def test_unrelated_entrybox_heading_with_suffix_not_adopted(self):
        # '## EntryBox Theme Gallery' is the user's own section — leave it.
        self.cfg.write_text("## EntryBox Theme Gallery\n\nuser words\n", encoding="utf-8")
        self.assertEqual(annotation_status(MD_AGENT, self.cfg), "none")
        status = write_annotation(MD_AGENT, PROJECT, self.cfg, build_annotation(MD_AGENT, PROJECT))
        self.assertEqual(status, "appended")
        self.assertIn("user words", self.cfg.read_text(encoding="utf-8"))


class TestEncodingAndEol(Base):
    def test_non_utf8_file_never_rewritten(self):
        raw = "# Projet\n\ncaf\xe9 instructions\n".encode("latin-1")  # invalid UTF-8
        self.cfg.write_bytes(raw)
        status = write_annotation(MD_AGENT, PROJECT, self.cfg, build_annotation(MD_AGENT, PROJECT))
        self.assertEqual(status, "skipped_unreadable")
        self.assertEqual(self.cfg.read_bytes(), raw, "mojibake rewrite of a non-UTF-8 file")
        self.assertEqual(annotation_status(MD_AGENT, self.cfg), "unreadable")
        self.assertFalse(remove_annotation(MD_AGENT, self.cfg))
        self.assertEqual(self.cfg.read_bytes(), raw)

    def test_crlf_file_stays_crlf(self):
        self.cfg.write_bytes(b"# Mine\r\n\r\nKeep my endings.\r\n")
        status = write_annotation(MD_AGENT, PROJECT, self.cfg, build_annotation(MD_AGENT, PROJECT))
        self.assertEqual(status, "appended")
        raw = self.cfg.read_bytes()
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""), "mixed line endings introduced")
        self.assertIn(b"Keep my endings.\r\n", raw)

    def test_replace_leaves_bak_snapshot(self):
        self.cfg.write_text("# Mine\n\n", encoding="utf-8")
        write_annotation(MD_AGENT, PROJECT, self.cfg, build_annotation(MD_AGENT, PROJECT))
        before = self.cfg.read_text(encoding="utf-8")
        write_annotation(MD_AGENT, PROJECT, self.cfg, build_annotation(MD_AGENT, PROJECT))
        bak = self.cfg.with_name(self.cfg.name + ".bak")
        self.assertTrue(bak.exists(), "no .bak before rewriting the user's file")
        self.assertEqual(bak.read_bytes().replace(b"\r\n", b"\n"),
                         before.encode("utf-8"))


class TestCustomAnnotationAndPort(Base):
    def test_valid_custom_annotation(self):
        good = build_annotation(MD_AGENT, PROJECT) + "\nextra user line\n"
        self.assertTrue(valid_custom_annotation(MD_AGENT, "<!-- EntryBox -->\nhi\n<!-- /EntryBox -->\n"))
        self.assertTrue(valid_custom_annotation(MD_AGENT, good))
        self.assertFalse(valid_custom_annotation(MD_AGENT, "no markers at all"))
        self.assertFalse(valid_custom_annotation(MD_AGENT, "<!-- EntryBox -->\nonly start"))

    def test_build_annotation_port(self):
        self.assertIn(":3859", build_annotation(MD_AGENT, PROJECT))  # config default
        self.assertIn(":4001", build_annotation(MD_AGENT, PROJECT, port=4001))

    def test_replacing_other_projects_block_is_flagged(self):
        other = {"id": "oth", "name": "Other", "prefix": "OTH"}
        write_annotation(MD_AGENT, other, self.cfg, build_annotation(MD_AGENT, other))
        status = write_annotation(MD_AGENT, PROJECT, self.cfg, build_annotation(MD_AGENT, PROJECT))
        self.assertEqual(status, "replaced_other")
        text = self.cfg.read_text(encoding="utf-8")
        self.assertIn("Prefix: TST", text)
        self.assertNotIn("Prefix: OTH", text)


class TestConfigFileValidation(unittest.TestCase):
    """API-boundary check: a learned agent's config_file must stay a relative
    path inside the project root (it is joined as root / config_file, where an
    absolute right operand replaces the root entirely)."""

    def _err(self, value):
        from app.routes.agents import validate_config_file
        return validate_config_file(value)

    def test_absolute_and_traversal_rejected(self):
        for bad in ("C:\\x\\y.md", "c:/x/y.md", "/etc/rules", "\\\\server\\share\\f.md",
                    "../outside.md", "a/../../outside.md", "..", "", "x" * 201):
            self.assertIsNotNone(self._err(bad), f"{bad!r} must be rejected")

    def test_nested_relative_accepted(self):
        for good in ("CLAUDE.md", ".cursorrules", ".github/copilot-instructions.md",
                     ".aider.conf.yml", "docs/agent.md"):
            self.assertIsNone(self._err(good), f"{good!r} must be accepted")


if __name__ == "__main__":
    unittest.main(verbosity=2)
