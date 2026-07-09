"""Crash-safety tests for app/config.py (data/entrybox.json).

The state file holds every project registration; writes must be atomic and
corruption must never silently reset it without a recoverable snapshot.

Run from github/:  python -m unittest discover -s tests -v
"""
import tempfile
import unittest
from pathlib import Path

from app import config


class ConfigBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._old_dir = config.DATA_DIR
        self._old_file = config._STATE_FILE
        config.DATA_DIR = self.tmp
        config._STATE_FILE = self.tmp / "entrybox.json"

    def tearDown(self):
        config.DATA_DIR = self._old_dir
        config._STATE_FILE = self._old_file


class TestStateWrites(ConfigBase):
    def test_update_state_round_trip(self):
        config.update_state({"theme": "ocean"})
        self.assertEqual(config.get_state()["theme"], "ocean")
        self.assertFalse((self.tmp / "entrybox.json.tmp").exists(),
                         "temp file left behind — write not atomic")

    def test_update_preserves_other_keys(self):
        config.update_state({"projects": [{"id": "x"}]})
        config.update_state({"theme": "minimal"})
        state = config.get_state()
        self.assertEqual(state["projects"], [{"id": "x"}])
        self.assertEqual(state["theme"], "minimal")

    def test_corrupt_state_file_is_snapshotted(self):
        config._STATE_FILE.write_text("{not json!!", encoding="utf-8")
        state = config.get_state()
        self.assertEqual(state["theme"], "dark")  # defaults returned
        snapshot = self.tmp / "entrybox.json.corrupt"
        self.assertTrue(snapshot.exists(), "corrupt file lost without snapshot")
        self.assertEqual(snapshot.read_text(encoding="utf-8"), "{not json!!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
