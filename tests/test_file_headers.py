"""Header hardening for the served-file route (app/routes/files.py).

Run from github/:  python -m unittest discover -s tests -v
"""
import unittest
from app.routes.files import _file_headers


class TestFileHeaders(unittest.TestCase):
    def test_nosniff_always_present(self):
        for suffix in (".png", ".txt", ".json", ".svg", ".unknown", ""):
            self.assertEqual(_file_headers(suffix).get("X-Content-Type-Options"), "nosniff")

    def test_svg_forced_to_download(self):
        self.assertEqual(_file_headers(".svg").get("Content-Disposition"), "attachment")
        self.assertEqual(_file_headers(".SVG").get("Content-Disposition"), "attachment")

    def test_non_svg_not_forced_to_download(self):
        for suffix in (".png", ".jpg", ".txt", ".json", ".md"):
            self.assertNotIn("Content-Disposition", _file_headers(suffix))


if __name__ == "__main__":
    unittest.main(verbosity=2)
