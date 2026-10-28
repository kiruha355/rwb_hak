#!/usr/bin/env python3
"""Small offline exporter checks; no DB connection and no model execution."""
import decimal
import base64
import gzip
import hashlib
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
        self.encoding = None

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("id") == "embedded-data":
            self.active = True
            self.encoding = dict(attrs).get("data-encoding")

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
        parser.feed((HERE / "template.html").read_text())
        self.assertEqual(json.loads(parser.payload), json.loads((HERE.parent / "sample" / "sample.json").read_text()))

    def test_roundtrip_and_script_escape(self):
        data = json.loads((HERE.parent / "sample" / "sample.json").read_text())
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

    def test_real_export_is_lossless_and_never_resets_to_synthetic_rows(self):
        data = json.loads((HERE.parent / "sample" / "sample.json").read_text())
        data["manifest"]["mode"] = "model_export"
        with tempfile.TemporaryDirectory(prefix="capibara-real-export-") as temp:
            target = Path(temp)
            export_data.write_export(data, target / "out.json", target / "out.html")
            rendered = (target / "out.html").read_text()
            parser = Embedded()
            parser.feed(rendered)
            self.assertEqual(parser.encoding, "gzip-base64")
            decoded = gzip.decompress(base64.b64decode(parser.payload))
            self.assertEqual(json.loads(decoded), data)
            self.assertNotIn("const DEMO_DATA=", rendered)
            self.assertNotIn("load(DEMO_DATA)", rendered)
            self.assertIn("load(embedded)", rendered)
            self.assertIn("Исходная выгрузка", rendered)

    def test_subset_gate_rejects_another_database_and_changed_values(self):
        data = json.loads((HERE.parent / "sample" / "sample.json").read_text())
        data.pop("manifest")
        counts = {k: len(data[k]) for k in ("orders", "items", "reviews", "months")}
        names = ["CONTRACT.md", "05_typecheck.sql", "10_dims.sql", "20_facts.sql",
                 "30_quality.sql", "40_mart.sql", "50_answers.sql", "90_checks.sql"]
        report = {"kind": "olist_subset_validation", "status": "passed", "database": "unit_db",
                  "scope": {"kind": "olist_subset", "selected_orders": counts["orders"],
                            "source_orders": 99441, "full_population_validated": False},
                  "row_counts": counts, "csv_raw": {"status": "passed"},
                  "core_checks": {"errors": 0},
                  "data_sha256": hashlib.sha256(export_data.canonical(data).encode()).hexdigest(),
                  "code_sha256": {"model/" + n: hashlib.sha256((export_data.ROOT / "model" / n).read_bytes()).hexdigest() for n in names}}
        with tempfile.TemporaryDirectory(prefix="capibara-gate-") as temp:
            path = Path(temp) / "proof.json"
            path.write_text(json.dumps(report))
            result = export_data.subset_validation(path, data, "unit_db")
            self.assertEqual(result["validation_status"], "subset_checked_not_full_olist")
            with self.assertRaises(ValueError):
                export_data.subset_validation(path, data, "another_db")
            data["orders"][0]["order_status"] = "changed"
            with self.assertRaises(ValueError):
                export_data.subset_validation(path, data, "unit_db")


if __name__ == "__main__":
    unittest.main()
