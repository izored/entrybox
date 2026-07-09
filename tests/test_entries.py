"""Parser / storage safety net for app/entries.py.

Stdlib unittest — no third-party dependency. Run from the github/ dir:

    python -m unittest discover -s tests -v

Loads entries.py directly by path so it needs no package install and no
running server. Covers the duplicate-ID bug class (date-only stamps),
round-trip stability, edit isolation, and the new duplicate-ID repair.
"""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

_ENTRIES_PY = Path(__file__).resolve().parent.parent / "app" / "entries.py"
_spec = importlib.util.spec_from_file_location("eb_entries_under_test", _ENTRIES_PY)
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)

PFX = "TST"


def _write(tmp: Path, body: str) -> Path:
    f = tmp / "entries.md"
    f.write_text(
        f"# {PFX} — EntryBox\n\nEntry tracking for Test. Managed by EntryBox.\n\n" + body,
        encoding="utf-8",
    )
    return f


class ParserBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.f = self.tmp / "entries.md"
        E._cache.clear()


class TestHeaderFormats(ParserBase):
    def test_full_with_done_at(self):
        _write(self.tmp,
            "## TST-0001 · 2026-05-01 10:00 · fix · done · 2026-05-02 11:00 — title one\n\nbody\n")
        e = E.load_entries(self.f, PFX)[0]
        self.assertEqual(e["id"], "TST-0001")
        self.assertEqual(e["state"], "done")
        self.assertEqual(e["done_at"], "2026-05-02 11:00")

    def test_without_done_at(self):
        _write(self.tmp, "## TST-0001 · 2026-05-01 10:00 · idea · logged — t\n\nb\n")
        e = E.load_entries(self.f, PFX)[0]
        self.assertEqual(e["state"], "logged")
        self.assertIsNone(e["done_at"])

    def test_transitional_no_state(self):
        _write(self.tmp, "## TST-0001 · 2026-05-01 10:00 · idea — t\n\nb\n")
        e = E.load_entries(self.f, PFX)[0]
        self.assertEqual(e["state"], "logged")

    def test_old_format_no_id_gets_migrated(self):
        _write(self.tmp, "## 2026-05-01 10:00 — legacy title\n\nb\n")
        e = E.load_entries(self.f, PFX)[0]
        self.assertTrue(e["id"].startswith(PFX + "-"))


class TestDateOnlyStamps(ParserBase):
    """Regression: the duplicate-ID bug. Date-only stamps must NOT be dropped."""

    def test_date_only_done_at_parses(self):
        _write(self.tmp,
            "## TST-0006 · 2026-05-31 20:11 · improve · done · 2026-06-01 — minimal\n\nb\n")
        ids = [e["id"] for e in E.load_entries(self.f, PFX)]
        self.assertIn("TST-0006", ids)

    def test_date_only_created_parses(self):
        _write(self.tmp, "## TST-0008 · 2026-06-01 · fix · logged — blobs\n\nb\n")
        ids = [e["id"] for e in E.load_entries(self.f, PFX)]
        self.assertIn("TST-0008", ids)

    def test_next_id_not_recycled_when_date_only_present(self):
        _write(self.tmp,
            "## TST-0005 · 2026-05-31 20:00 · idea · logged — five\n\nb\n\n"
            "## TST-0006 · 2026-05-31 20:11 · improve · done · 2026-06-01 — six\n\nb\n")
        new = E.add_entry(self.f, PFX, "T", "seven", "", "idea")
        self.assertEqual(new["id"], "TST-0007")


class TestRoundTrip(ParserBase):
    def test_add_then_reload_stable(self):
        E.ensure_file(self.f, "T", PFX)
        E.add_entry(self.f, PFX, "T", "alpha", "body a", "idea")
        E.add_entry(self.f, PFX, "T", "beta", "body b", "fix")
        first = self.f.read_text(encoding="utf-8")
        E._cache.clear()
        E.load_entries(self.f, PFX)  # may rewrite
        second = self.f.read_text(encoding="utf-8")
        # A second load must not keep changing the file.
        E._cache.clear()
        E.load_entries(self.f, PFX)
        third = self.f.read_text(encoding="utf-8")
        self.assertEqual(second, third, "load_entries is not idempotent on disk")

    def test_emdash_in_title_survives(self):
        E.ensure_file(self.f, "T", PFX)
        E.add_entry(self.f, PFX, "T", "before — after", "b", "idea")
        E._cache.clear()
        e = E.load_entries(self.f, PFX)[0]
        self.assertEqual(e["title"], "before — after")

    def test_middot_in_title_survives(self):
        E.ensure_file(self.f, "T", PFX)
        E.add_entry(self.f, PFX, "T", "a · b · c", "b", "idea")
        E._cache.clear()
        e = E.load_entries(self.f, PFX)[0]
        self.assertEqual(e["title"], "a · b · c")

    def test_empty_and_header_only(self):
        self.f.write_text(f"# {PFX} — EntryBox\n\nManaged by EntryBox.\n", encoding="utf-8")
        self.assertEqual(E.load_entries(self.f, PFX), [])


class TestEditIsolation(ParserBase):
    def test_edit_preserves_siblings(self):
        _write(self.tmp,
            "## TST-0001 · 2026-05-01 10:00 · idea · logged — one\n\nbody one\n\n"
            "## TST-0002 · 2026-05-01 11:00 · fix · wip — two\n\nbody two\n")
        E.update_entry(self.f, PFX, "TST-0001", title="one edited", entry_type="docs")
        E._cache.clear()
        by_id = {e["id"]: e for e in E.load_entries(self.f, PFX)}
        self.assertEqual(by_id["TST-0001"]["title"], "one edited")
        self.assertEqual(by_id["TST-0001"]["type"], "docs")
        self.assertEqual(by_id["TST-0002"]["title"], "two")
        self.assertEqual(by_id["TST-0002"]["state"], "wip")


class TestDuplicateIdRepair(ParserBase):
    """New behavior (F-E): two entries with the same ID must be repaired on load
    so the UI never sees colliding keys and update/delete can't hit the wrong one."""

    def test_duplicate_ids_are_repaired(self):
        _write(self.tmp,
            "## TST-0006 · 2026-05-01 10:00 · idea · logged — original six\n\na\n\n"
            "## TST-0006 · 2026-05-02 10:00 · fix · logged — collision six\n\nb\n")
        entries = E.load_entries(self.f, PFX)
        ids = [e["id"] for e in entries]
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(set(ids)), 2, f"duplicate IDs not repaired: {ids}")


class TestAttachmentReaping(ParserBase):
    """delete_entry must not delete attachments other entries still reference."""

    def _setup_shared(self):
        eb = self.tmp / ".entrybox"
        att = eb / "attachments"
        att.mkdir(parents=True)
        f = eb / "entries.md"
        # shared.png used by TST-0001 and TST-0002; solo.png only by TST-0003.
        f.write_text(
            f"# {PFX} — EntryBox\n\nManaged by EntryBox.\n\n"
            "## TST-0001 · 2026-05-01 10:00 · idea · logged — one\n\n"
            "![s](attachments/shared.png)\n\n"
            "## TST-0002 · 2026-05-01 11:00 · idea · logged — two\n\n"
            "![s](attachments/shared.png)\n\n"
            "## TST-0003 · 2026-05-01 12:00 · idea · logged — three\n\n"
            "![x](attachments/solo.png)\n",
            encoding="utf-8",
        )
        (att / "shared.png").write_bytes(b"PNG")
        (att / "solo.png").write_bytes(b"PNG")
        return f, att

    def test_shared_attachment_kept_when_one_referrer_deleted(self):
        f, att = self._setup_shared()
        E.delete_entry(f, PFX, "TST-0001")
        self.assertTrue((att / "shared.png").is_file(), "shared attachment wrongly reaped")

    def test_attachment_reaped_when_last_referrer_deleted(self):
        f, att = self._setup_shared()
        E.delete_entry(f, PFX, "TST-0001")
        E.delete_entry(f, PFX, "TST-0002")
        self.assertFalse((att / "shared.png").is_file(), "attachment not reaped after last referrer gone")

    def test_solo_attachment_reaped(self):
        f, att = self._setup_shared()
        E.delete_entry(f, PFX, "TST-0003")
        self.assertFalse((att / "solo.png").is_file(), "solo attachment should be reaped")


class TestBodyHeadingEscape(ParserBase):
    """A body line shaped like the block separator must not split the entry
    into a phantom entry (silent data mangling from an ordinary markdown paste)."""

    DATE_BODY = "notes:\n## 2026-01-01 — planning session\nmore text"
    ID_BODY = "notes:\n## TST-0099 · 2026-01-01 00:00 · idea · logged — fake\nmore text"

    def test_body_with_date_heading_survives_reload(self):
        E.add_entry(self.f, PFX, "Test", "Meeting notes", self.DATE_BODY, "idea")
        for _ in range(2):
            entries = E.load_entries(self.f, PFX)
        self.assertEqual(len(entries), 1, "phantom entry fabricated from body line")
        self.assertEqual(entries[0]["body"], self.DATE_BODY, "body did not round-trip")

    def test_body_with_id_heading_survives_reload(self):
        E.add_entry(self.f, PFX, "Test", "Meeting notes", self.ID_BODY, "idea")
        for _ in range(2):
            entries = E.load_entries(self.f, PFX)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["body"], self.ID_BODY)

    def test_update_entry_preserves_escaped_body(self):
        e = E.add_entry(self.f, PFX, "Test", "Meeting notes", self.DATE_BODY, "idea")
        E.update_entry(self.f, PFX, e["id"], title="new title")
        entries = E.load_entries(self.f, PFX)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["title"], "new title")
        self.assertEqual(entries[0]["body"], self.DATE_BODY)

    def test_plain_bodies_unchanged_on_disk(self):
        E.add_entry(self.f, PFX, "Test", "Normal", "line one\nline two\n\nline four", "idea")
        raw = self.f.read_text(encoding="utf-8")
        self.assertNotIn("\\", raw, "escape leaked into a plain body")

    def test_literal_backslash_heading_round_trips(self):
        body = "\\## 2026-01-01 — user's own literal line"
        E.add_entry(self.f, PFX, "Test", "Edge", body, "idea")
        E.load_entries(self.f, PFX)
        entries = E.load_entries(self.f, PFX)
        self.assertEqual(entries[0]["body"], body)


class TestCacheInvalidation(ParserBase):
    def test_add_entry_visible_even_when_mtime_does_not_advance(self):
        """NTFS mtime ticks are ~15 ms — on fast machines an append can land in
        the same tick as the previous cache fill. Writers must invalidate the
        cache explicitly; simulate the tick collision by pinning mtime back."""
        E.add_entry(self.f, PFX, "Test", "first", "", "idea")
        E.load_entries(self.f, PFX)
        st = self.f.stat()
        E.add_entry(self.f, PFX, "Test", "second", "", "idea")
        os.utime(self.f, (st.st_atime, st.st_mtime))
        entries = E.load_entries(self.f, PFX)
        self.assertEqual(len(entries), 2, "second entry invisible — stale mtime cache")

    def test_delete_entry_visible_even_when_mtime_does_not_advance(self):
        E.add_entry(self.f, PFX, "Test", "first", "", "idea")
        e2 = E.add_entry(self.f, PFX, "Test", "second", "", "idea")
        E.load_entries(self.f, PFX)
        st = self.f.stat()
        E.delete_entry(self.f, PFX, e2["id"])
        os.utime(self.f, (st.st_atime, st.st_mtime))
        entries = E.load_entries(self.f, PFX)
        self.assertEqual(len(entries), 1, "deleted entry still served from stale cache")


class TestUpdateStateGuard(ParserBase):
    def test_update_state_on_mangled_header_returns_none(self):
        _write(self.tmp, "## TST-0001 · 2026-05-01 10:00 · idea · logged — t\n\nb\n")
        E.load_entries(self.f, PFX)
        # Mangle the header separators so neither the parser nor the
        # state-change regex can match the block.
        text = self.f.read_text(encoding="utf-8")
        self.f.write_text(text.replace("· idea · logged —", "| idea | logged —"), encoding="utf-8")
        E._cache.clear()
        entry, old = E.update_entry_state(self.f, PFX, "TST-0001", "wip")
        self.assertIsNone(entry)
        self.assertIsNone(old)
        # The unparseable block goes through the migration path: dropped from
        # the live file but snapshotted to .bak (pre-existing safety net).
        bak = self.f.with_name(self.f.name + ".bak")
        self.assertTrue(bak.exists())
        self.assertIn("| idea | logged —", bak.read_text(encoding="utf-8"))

    def test_same_state_set_is_idempotent_success(self):
        _write(self.tmp, "## TST-0001 · 2026-05-01 10:00 · idea · wip — t\n\nb\n")
        entry, old = E.update_entry_state(self.f, PFX, "TST-0001", "wip")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["state"], "wip")
        self.assertEqual(old, "wip")


if __name__ == "__main__":
    unittest.main(verbosity=2)
