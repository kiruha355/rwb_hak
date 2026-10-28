#!/usr/bin/env python3
"""Exercise the real shell entrypoint with a fake psql; never connect to a DB."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class Wiring(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="q6-q10-wiring-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for directory in ("model", "answers"):
            shutil.copytree(ROOT / directory, self.root / directory,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (self.root / "scripts").mkdir()
        shutil.copy2(ROOT / "scripts/build-model.sh", self.root / "scripts/build-model.sh")
        (self.root / "bin").mkdir()
        fake = self.root / "bin/psql"
        fake.write_text('#!/bin/sh\ncat > "$CAPIBARA_TEST_CAPTURE"\n')
        fake.chmod(0o755)
        self.capture = self.root / "capture.sql"
        self.env = dict(os.environ, PATH=str(self.root / "bin") + os.pathsep + os.environ["PATH"],
                        RWB_RAW_RELOAD_PAUSED="1", RWB_DB_MODE="host",
                        CAPIBARA_TEST_CAPTURE=str(self.capture))

    def run_wrapper(self, mode):
        return subprocess.run(["bash", "scripts/build-model.sh", mode], cwd=self.root,
                              env=self.env, text=True, capture_output=True)

    def test_real_build_and_answers_are_expanded(self):
        build = self.run_wrapper("build")
        self.assertEqual(build.returncode, 0, build.stderr)
        expanded = self.capture.read_text()
        self.assertLess(expanded.index("model/50_answers.sql"), expanded.index("model/55_answers_block_b.sql"))
        self.assertLess(expanded.index("model/55_answers_block_b.sql"), expanded.index("model/90_checks.sql"))
        for name in ("q06_price_history", "q07_delivery_by_state", "q08_status_snapshot",
                     "q09_payments_2018_by_state", "q09_payment_methods", "q10_review_delivery",
                     "q10_review_coverage"):
            self.assertIn("CREATE VIEW mart." + name + " AS", expanded)
        answer = self.run_wrapper("answers")
        self.assertEqual(answer.returncode, 0, answer.stderr)
        expanded = self.capture.read_text()
        for name in ("q01.sql", "q02.sql", "q03.sql", "q04.sql", "q05.sql"):
            self.assertIn("answers/" + name, expanded)
        for name in ("q06.sql", "q07.sql", "q08.sql", "q09.sql", "q10.sql", "q10_coverage.sql"):
            self.assertIn("answers/q06-q10/" + name, expanded)
        self.assertIn("SELECT * FROM mart.q09_payments_2018_by_state", expanded)
        self.assertIn("SELECT * FROM mart.q09_payment_methods", expanded)
        self.assertIn("SELECT * FROM mart.q10_review_coverage", expanded)

    def test_missing_stage_or_answer_fails_before_psql(self):
        (self.root / "model/55_answers_block_b.sql").unlink()
        result = self.run_wrapper("build")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("55_answers_block_b.sql", result.stderr)
        self.assertFalse(self.capture.exists())
        (self.root / "answers/q06-q10/q10_coverage.sql").unlink()
        result = self.run_wrapper("answers")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("q10_coverage.sql", result.stderr)
        self.assertFalse(self.capture.exists())

    def test_rebuild_drop_inventory_covers_created_views(self):
        """A new dependent view left behind blocks the next RESTRICT rebuild."""
        created = set()
        for path in (self.root / "model").glob("*.sql"):
            created.update(re.findall(r"CREATE\s+VIEW\s+(mart\.\w+)", path.read_text(), re.I))
        reset = (self.root / "model/00_schemas.sql").read_text()
        view_drop = re.search(r"DROP VIEW IF EXISTS\s+(.*?)\s+RESTRICT;", reset, re.S).group(1)
        dropped = set(re.findall(r"mart\.\w+", view_drop))
        self.assertTrue(created)
        self.assertEqual(created - dropped, set(), "Views missing from the owned rebuild inventory")


if __name__ == "__main__":
    unittest.main()
