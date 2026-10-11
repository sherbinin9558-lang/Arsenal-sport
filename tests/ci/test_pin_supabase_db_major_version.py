import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.ci.pin_supabase_db_major_version import pin_major_version

class PinSupabaseMajorVersionTests(unittest.TestCase):
    def write_config(self, directory: Path, content: str) -> Path:
        path = directory / "config.toml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_replaces_existing_version_and_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_config(Path(tmp), '[api]\nport = 54321\n\n[db]\nport = 54322\nmajor_version = 15\n\n[studio]\nport = 54323\n')
            pin_major_version(path)
            result = path.read_text(encoding="utf-8")
            self.assertIn("major_version = 17", result)
            self.assertNotIn("major_version = 15", result)
            self.assertIn("port = 54321", result)
            self.assertIn("port = 54322", result)
            self.assertIn("port = 54323", result)
            self.assertEqual(result.count("major_version = 17"), 1)

    def test_inserts_missing_version_into_db_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_config(Path(tmp), '[db]\nport = 54322\n\n[studio]\nport = 54323\n')
            pin_major_version(path)
            result = path.read_text(encoding="utf-8")
            self.assertRegex(result, r'(?ms)^\[db\]\nmajor_version = 17\nport = 54322\n')
            self.assertIn("[studio]", result)

    def test_fails_when_db_section_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_config(Path(tmp), '[api]\nport = 54321\n')
            with self.assertRaisesRegex(ValueError, r'exactly one \[db\] section'):
                pin_major_version(path)

    def test_fails_when_db_section_is_duplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_config(Path(tmp), '[db]\nport = 54322\n\n[db]\nport = 54324\n')
            with self.assertRaisesRegex(ValueError, r'exactly one \[db\] section'):
                pin_major_version(path)

    def test_fails_on_duplicate_version_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_config(Path(tmp), '[db]\nmajor_version = 15\nmajor_version = 16\n')
            with self.assertRaisesRegex(ValueError, 'duplicate major_version'):
                pin_major_version(path)

if __name__ == "__main__":
    unittest.main()
