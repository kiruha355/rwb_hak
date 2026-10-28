"""Offline isolation/inventory checks; these do not parse or execute PostgreSQL."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("verify_model", ROOT / "scripts/verify-model.py")
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


class FixtureSafetyTests(unittest.TestCase):
    def setUp(self):
        self.schemas = {s: f"w11_{s}_012345abcdef" for s in ("raw", "core", "mart")}

    def test_schema_rebinding_includes_dynamic_sql(self):
        text = "SELECT * FROM raw.orders; EXECUTE 'SELECT * FROM core.fact_order'; SELECT * FROM mart.v_orders;"
        actual = verify.schema_sql(text, self.schemas)
        for old, new in self.schemas.items():
            self.assertNotIn(old + ".", actual.replace(new + ".", ""))
            self.assertIn(new + ".", actual)

    def test_unsafe_schema_psql_and_commit_rejected(self):
        bad = dict(self.schemas, raw="raw")
        with self.assertRaises(ValueError):
            verify.schema_sql("SELECT * FROM raw.orders", bad)
        for text in ("COMMIT;", "ROLLBACK;", "\\ir ../../model/build.sql", "SELECT * FROM RAW.orders"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                verify.schema_sql(text, self.schemas)

    def test_all_fixture_fragments_and_pipeline_rebind_without_live_schema(self):
        paths = verify.stages() + [ROOT / "scripts/init/02_raw_ddl.sql", verify.FIXTURES / "base.sql", verify.FIXTURES / "assert-base.sql"]
        for path in paths:
            with self.subTest(path=path):
                verify.schema_sql(path.read_text(), self.schemas)
        for case in verify.inventory():
            for field in ("before", "after", "assert_sql"):
                if field in case:
                    verify.schema_sql(case[field], self.schemas)

    def test_plan_reports_pending_and_no_fake_execution(self):
        result = verify.plan()
        self.assertEqual(result["status"], "pending_db_execution")
        self.assertEqual(len(result["cases"]), 16)
        self.assertEqual(result["missing_stages"], [])
        self.assertNotIn("passed", result)

    def test_required_negative_checks_name_real_diagnostics(self):
        sql = (ROOT / "model/90_checks.sql").read_text()
        mapping_names = {"items", "reviews"}
        suffixes = {"values_raw_minus_core", "keys_raw_minus_core", "keys_core_minus_raw", "multiplicity"}
        for case in verify.inventory():
            if case.get("error_code") == "23514":
                name = case["error_text"]
                if "." in name and name.split(".", 1)[0] in mapping_names:
                    mapping, suffix = name.split(".", 1)
                    self.assertIn(f"$sql${mapping}$sql$", sql)
                    self.assertIn(suffix, suffixes)
                    self.assertIn("'." + suffix + "'", sql)
                else:
                    self.assertIn(f"$sql${name}$sql$", sql)


if __name__ == "__main__":
    unittest.main()
