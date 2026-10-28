#!/usr/bin/env python3
"""Small offline checks of evidence integrity; no Olist fixture or database."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from decimal import Decimal

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('full_olist',ROOT/'scripts/verify-full-olist.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class EvidenceIntegrity(unittest.TestCase):
    def test_pg_copy_null_and_empty_multiline(self):
        with tempfile.TemporaryDirectory(prefix='olist-parser-test-') as d:
            p=Path(d)/'small.csv'
            p.write_bytes(b'\xef\xbb\xbfa,b,c,d,e\r\n,"",0,"line\r\nbreak","quote "" plus comma,"\r\n')
            rows=list(m.csv_rows(p,['a','b','c','d','e']))
        self.assertEqual(rows,[dict(a=None,b='',c='0',d='line\r\nbreak',e='quote " plus comma,')])

    def test_multiset_retains_multiplicity_null_empty_and_each_value(self):
        rows=[('a',None),('b',''),('a',None)]
        self.assertEqual(m.multiset(rows),m.multiset(list(reversed(rows))))
        for mutation in [rows[:-1],[('a',''),('b',''),('a',None)],[('c',None),('b',''),('a',None)]]:
            self.assertNotEqual(m.multiset(rows),m.multiset(mutation))

    def test_comparator_detects_wrong_denominator_and_null_zero(self):
        expected=[dict(group='x',duration_denominator=499,mean=Decimal('12.1234567890123'),late_pct=None)]
        self.assertEqual(m.compare_rows(expected,expected)['status'],'pass')
        for column,value in [('duration_denominator',500),('late_pct',0),('mean',Decimal('12.1234568'))]:
            changed=[dict(expected[0],**{column:value})]
            with self.assertRaises(ValueError):m.compare_rows(changed,expected)

    def test_statement_filter_rejects_ddl_and_psql(self):
        self.assertEqual(len(m.statements('-- note\nWITH a AS (SELECT 1) SELECT * FROM a; SELECT 2;')),2)
        for sql in ['CREATE VIEW a AS SELECT 1;','SELECT 1; DROP TABLE a;',r'\i other.sql']:
            with self.assertRaises(ValueError):m.statements(sql)


if __name__=='__main__':unittest.main()
