"""Small offline tests; no DB, network, dependency install, or production writes."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("input_manifest", ROOT / "scripts/input-manifest.py")
manifest = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manifest)


class InputManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.pin = manifest.load_manifest(manifest.PIN)

    def spec(self):
        return {"file": "example.csv", "header": ["id", "comment"], "table": "raw.example"}

    def test_bom_multiline_and_bytes_are_exact(self):
        payload = b'\xef\xbb\xbfid,comment\r\n1,"two\r\nlines"\r\n2,""\r\n'
        path = self.directory / "example.csv"
        path.write_bytes(payload)
        actual = manifest.inspect_file(path, self.spec())
        self.assertEqual(actual["rows"], 2)  # not physical newline count
        self.assertEqual(actual["bytes"], len(payload))
        self.assertEqual(actual["sha256"], hashlib.sha256(payload).hexdigest())

    def test_bad_headers_and_ragged_rows_rejected(self):
        for text in ('comment,id\n1,x\n', 'id,comment\n1,x,extra\n', 'id,comment\n\n', ''):
            with self.subTest(text=text):
                path = self.directory / "example.csv"
                path.write_text(text)
                with self.assertRaises(manifest.ManifestError):
                    manifest.inspect_file(path, self.spec())

    def test_malformed_quoted_record_rejected(self):
        path = self.directory / "example.csv"
        path.write_text('id,comment\n1,"unfinished\n')
        with self.assertRaises(Exception) as raised:
            manifest.inspect_file(path, self.spec())
        self.assertIn("unexpected end", str(raised.exception))

    def test_same_row_count_changed_payload_is_not_equal(self):
        expected = copy.deepcopy(self.pin)
        actual = copy.deepcopy(expected)
        actual["files"][0]["sha256"] = "0" * 64
        self.assertEqual(len(manifest.compare(actual, expected)), 1)
        self.assertIn("sha256", manifest.compare(actual, expected)[0])

    def test_every_contract_field_and_file_inventory_is_checked(self):
        for field in ("header", "rows", "bytes", "source_url", "table"):
            actual = copy.deepcopy(self.pin)
            actual["files"][0][field] = None
            with self.subTest(field=field):
                self.assertTrue(manifest.compare(actual, self.pin))
        actual = copy.deepcopy(self.pin)
        actual["files"].pop()
        self.assertTrue(manifest.compare(actual, self.pin))

    def test_manifest_order_does_not_matter(self):
        actual = copy.deepcopy(self.pin)
        actual["files"].reverse()
        self.assertEqual(manifest.compare(actual, self.pin), [])

    def test_duplicate_or_missing_or_unsafe_entry_rejected(self):
        for kind in ("duplicate", "missing", "unsafe"):
            invalid = copy.deepcopy(self.pin)
            if kind == "duplicate":
                invalid["files"][1] = invalid["files"][0]
            elif kind == "missing":
                invalid["files"].pop()
            else:
                invalid["files"][0]["file"] = "../outside.csv"
            path = self.directory / "manifest.json"
            path.write_text(json.dumps(invalid))
            with self.subTest(kind=kind), self.assertRaises(manifest.ManifestError):
                manifest.load_manifest(path)

    def test_changed_source_ref_rejected(self):
        actual = copy.deepcopy(self.pin)
        actual["source"]["ref"] = "master"
        self.assertTrue(manifest.compare(actual, self.pin))

    def test_cli_missing_inputs_fails_without_writing_output(self):
        output = self.directory / "result.json"
        result = subprocess.run([sys.executable, str(ROOT / "scripts/input-manifest.py"), "--data-dir", str(self.directory), "--verify-pinned", "--output", str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("input-manifest:", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
