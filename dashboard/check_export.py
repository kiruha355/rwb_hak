#!/usr/bin/env python3
"""Small offline exporter checks; no DB connection and no model execution."""
import decimal
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest

import export_data

HERE = Path(__file__).resolve().parent


class Embedded(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.payload = ""

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("id") == "embedded-data":
            self.active = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.payload += data


class ExportChecks(unittest.TestCase):
    def test_precision_and_nonfinite(self):
        self.assertEqual(export_data.encode(decimal.Decimal("0E-8")), "0.00000000")
        self.assertEqual(export_data.encode(decimal.Decimal("12.3456789")), "12.3456789")
        with self.assertRaises(ValueError):
            export_data.encode(decimal.Decimal("NaN"))

    def test_queries_are_selects_and_no_raw(self):
        for sql in export_data.QUERIES.values():
            self.assertTrue(sql.lstrip().startswith("SELECT"))
            self.assertNotIn("raw.", sql.lower())
            self.assertNotIn("LIMIT", sql.upper())

    def test_synthetic_embedded_matches_sample(self):
        parser = Embedded()
        parser.feed((HERE / "index.html").read_text())
        self.assertEqual(json.loads(parser.payload), json.loads((HERE / "sample.json").read_text()))

    def test_roundtrip_and_script_escape(self):
        data = json.loads((HERE / "sample.json").read_text())
        data["manifest"]["dataset_label"] = "</script><script>bad()</script>"
        with tempfile.TemporaryDirectory(prefix="capibara-export-") as temp:
            target = Path(temp)
            export_data.write_export(data, target / "out.json", target / "out.html")
            self.assertEqual(json.loads((target / "out.json").read_text()), data)
            rendered = (target / "out.html").read_text()
            self.assertNotIn("</script><script>bad()", rendered)
            parser = Embedded()
            parser.feed(rendered)
            self.assertEqual(json.loads(parser.payload), data)


if __name__ == "__main__":
    unittest.main()
