"""Theme-id sandbox tests for app/theme.py.

Theme ids map straight to filenames under themes/ — a traversal id must never
read JSON outside that directory.

Run from github/:  python -m unittest discover -s tests -v
"""
import unittest

from app.theme import get_theme


class TestThemeIdWhitelist(unittest.TestCase):
    def test_traversal_ids_rejected(self):
        for bad in ("../data/entrybox", "..\\data\\entrybox", "a/b", "a\\b",
                    "..", ".", "", "x" * 65):
            self.assertIsNone(get_theme(bad), f"id {bad!r} must be rejected")

    def test_valid_theme_ids_load(self):
        theme = get_theme("dark")
        self.assertIsInstance(theme, dict)
        self.assertIn("vars", theme)

    def test_unknown_but_wellformed_id_is_none(self):
        self.assertIsNone(get_theme("no-such-theme"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
