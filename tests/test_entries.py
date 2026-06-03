"""Parser / storage safety net for app/entries.py.

Stdlib unittest — no third-party dependency. Run from the github/ dir:

    python -m unittest discover -s tests -v

Loads entries.py directly by path so it needs no package install and no
running server. Covers the duplicate-ID bug class (date-only stamps),
round-trip stability, edit isolation, and the new duplicate-ID repair.
"""
import importlib.util
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
