"""Small native PG regression for temp setup, CSV NULLs and read-only comparison.

Opt in with RWB_TEST_DSN to a dedicated test DB. This does not bind Olist pins.
The tiny source schema is preserved in that DB; no existing raw object is used.
"""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("csv_raw_verify", ROOT / "scripts/verify-model.py")
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


@unittest.skipUnless(os.environ.get("RWB_TEST_DSN"), "dedicated PG test DSN not configured")
class CsvRawPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from psycopg2 import sql
        cls.sql = sql
        cls.schema = "w11_csv_probe_" + uuid.uuid4().hex[:12]
        cls.directory = tempfile.TemporaryDirectory(prefix="rwb-csv-probe-")
        cls.data_dir = Path(cls.directory.name)
        (cls.data_dir / "probe.csv").write_text('id,value\nnull,\nempty,""\n')
        cls.source = verify.connect("RWB_TEST_DSN", fixtures=True)
        with cls.source.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(cls.schema)))
            cursor.execute(sql.SQL("CREATE TABLE {}.probe (id text, value text, _source_file text)").format(sql.Identifier(cls.schema)))
            cursor.execute(sql.SQL("INSERT INTO {}.probe VALUES ('null',NULL,'probe.csv'),('empty','','probe.csv')").format(sql.Identifier(cls.schema)))
        cls.source.commit()
        cls.entries = [{"file": "probe.csv", "table": cls.schema + ".probe", "header": ["id", "value"], "rows": 2}]

    @classmethod
    def tearDownClass(cls):
        cls.source.close()
        cls.directory.cleanup()

    def test_csv_copy_runs_read_only_and_preserves_null_vs_empty(self):
        connection = verify.connect("RWB_TEST_DSN", fixtures=False)
        try:
            rows = verify.compare_csv_rows(connection, self.entries, self.data_dir)
            self.assertEqual([(r["missing_in_raw"], r["extra_in_raw"], r["wrong_source_file"]) for r in rows], [(0, 0, 0)])
            with connection.cursor() as cursor:
                cursor.execute("SHOW transaction_read_only")
                self.assertEqual(cursor.fetchone()[0], "on")
                cursor.execute("SELECT count(*) FILTER (WHERE value IS NULL), count(*) FILTER (WHERE value='') FROM pg_temp.w11_csv_0")
                self.assertEqual(cursor.fetchone(), (1, 1))
        finally:
            connection.rollback()
            connection.close()

    def test_changed_source_is_not_accepted_as_equal(self):
        with self.source.cursor() as cursor:
            cursor.execute(self.sql.SQL("UPDATE {}.probe SET value='' WHERE id='null'").format(self.sql.Identifier(self.schema)))
        self.source.commit()
        connection = verify.connect("RWB_TEST_DSN", fixtures=False)
        try:
            row = verify.compare_csv_rows(connection, self.entries, self.data_dir)[0]
            self.assertEqual((row["missing_in_raw"], row["extra_in_raw"]), (1, 1))
        finally:
            connection.rollback()
            connection.close()
            with self.source.cursor() as cursor:
                cursor.execute(self.sql.SQL("UPDATE {}.probe SET value=NULL WHERE id='null'").format(self.sql.Identifier(self.schema)))
            self.source.commit()

    def test_comparison_transaction_cannot_write_source(self):
        import psycopg2
        connection = verify.connect("RWB_TEST_DSN", fixtures=False)
        try:
            verify.compare_csv_rows(connection, self.entries, self.data_dir)
            with self.assertRaises(psycopg2.errors.ReadOnlySqlTransaction):
                with connection.cursor() as cursor:
                    cursor.execute(self.sql.SQL("DELETE FROM {}.probe").format(self.sql.Identifier(self.schema)))
        finally:
            connection.rollback()
            connection.close()


if __name__ == "__main__":
    unittest.main()
