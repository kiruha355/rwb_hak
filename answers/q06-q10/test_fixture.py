#!/usr/bin/env python3
"""Behavior checks on a disposable PostgreSQL DB with no raw/core/mart schemas.

Pass libpq environment variables for a DB named q6_q10_fixture. This test creates
fixture-only raw/core/mart inside a rolled-back transaction; never point it at a
working database. It loads the repository's actual core and mart SQL.
"""
from pathlib import Path
import psycopg

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sql(path):
    return (ROOT / path).read_text(encoding='utf-8')


def rows(cur, filename):
    cur.execute((HERE / filename).read_text(encoding='utf-8'))
    return [dict(zip([c.name for c in cur.description], row)) for row in cur.fetchall()]


with psycopg.connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(), count(*) FROM pg_namespace WHERE nspname IN ('raw','core','mart')")
        db, existing = cur.fetchone()
        if db != 'q6_q10_fixture' or existing:
            raise SystemExit('Refusing: requires empty fixture schemas in database q6_q10_fixture')
        cur.execute('CREATE SCHEMA raw; CREATE SCHEMA core; CREATE SCHEMA mart')
        cur.execute(sql('scripts/init/02_raw_ddl.sql'))
        cur.execute(sql('tests/model/fixtures/base.sql'))
        cur.execute("""
            UPDATE raw.orders SET order_status='canceled' WHERE order_id='neither';
            UPDATE raw.orders SET order_purchase_timestamp='2018-01-01 10:00:00' WHERE order_id='all-null';
            INSERT INTO raw.order_reviews(review_id,order_id,review_score) VALUES ('cancel-review','neither','3');
            UPDATE raw.orders SET order_purchase_timestamp='2018-01-01 10:00:00',
              order_delivered_carrier_date='2018-01-02 10:00:00',
              order_delivered_customer_date='2018-01-03 18:00:00',
              order_estimated_delivery_date='2018-01-03 00:00:00'
              WHERE order_id='fanout';
            INSERT INTO raw.products(product_id, product_category_name) VALUES ('p2', 'cat');
            INSERT INTO raw.order_items(order_id,order_item_id,product_id,seller_id,price,freight_value)
              SELECT 'fanout', (n+2)::text, 'p2','s1', price, '0'
              FROM (VALUES (1,'0'),(2,'4'),(3,'5'),(4,'7'),(5,'10'),(6,'20'),(7,'30')) v(n,price);
        """)
        for stage in ('model/10_dims.sql', 'model/20_facts.sql', 'model/40_mart.sql'):
            cur.execute(sql(stage))
        q6 = rows(cur, 'q06.sql')
        assert {r['product_id'] for r in q6 if r['population'] == 'all_statuses'} == {'p1', 'p2'}
        assert all(r['distinct_prices'] == 7 for r in q6)
        assert sum(r['units_sold'] for r in q6 if r['population'] == 'all_statuses' and r['product_id'] == 'p2') == 7
        q7 = rows(cur, 'q07.sql')
        assert q7 == []  # 10 orders are below the required 500
        q7sql = (HERE / 'q07.sql').read_text().replace('500::bigint', '2::bigint')
        cur.execute(q7sql)
        q7 = [dict(zip([c.name for c in cur.description], row)) for row in cur.fetchall()]
        by7 = {(r['population'], r['late_basis']): r for r in q7}
        assert by7['all_statuses', 'timestamp']['orders_count'] == 10
        assert by7['delivered', 'timestamp']['orders_count'] == 9
        assert by7['delivered', 'calendar_day']['late_orders'] == 0
        assert by7['delivered', 'timestamp']['late_orders'] == 8
        assert by7['delivered', 'timestamp']['late_denominator'] == 8
        assert by7['delivered', 'timestamp']['duration_denominator'] == 7
        q8 = {r['order_status']: r for r in rows(cur, 'q08.sql')}
        assert q8['canceled']['orders_count'] == q8['canceled']['orders_without_items'] == 1
        assert q8['delivered']['orders_count'] == 9
        assert q8['canceled']['orders_pct'] == 10
        cur.execute((HERE / 'q09.sql').read_text())
        q9 = [dict(zip([c.name for c in cur.description], row)) for row in cur.fetchall()]
        assert len(q9) == 1 and q9[0]['payment_count'] == 4 and q9[0]['payment_amount'] is None
        assert q9[0]['known_payment_amount_sum'] == 30 and q9[0]['amount_denominator'] == 3
        assert q9[0]['credit_installments_denominator'] == 2
        assert cur.nextset()
        methods = [dict(zip([c.name for c in cur.description], row)) for row in cur.fetchall()]
        assert sum(r['payment_count'] for r in methods if r['period'] == 'purchase_2018') == 4
        assert sum(r['payment_count'] for r in methods if r['period'] == 'all_snapshot') == 9
        q10 = rows(cur, 'q10.sql')
        by10 = {(r['score_policy'], r['late_basis'], r['review_score']): r for r in q10 if r['population'] == 'all_statuses'}
        assert len(q10) == 40
        assert by10['within_score', 'timestamp', 5]['orders_count'] == 2
        assert by10['within_score', 'timestamp', 1]['orders_count'] == 1
        assert by10['single_score_only', 'timestamp', 5]['orders_count'] == 1
        assert by10['within_score', 'calendar_day', 5]['late_orders'] == 0
        assert by10['within_score', 'timestamp', 5]['late_orders'] == 2
        assert by10['within_score', 'timestamp', 3]['orders_count'] == 1
        assert by10['within_score', 'timestamp', 3]['late_pct'] is None
        delivered3 = next(r for r in q10 if r['population'] == 'delivered' and r['score_policy'] == 'within_score' and r['late_basis'] == 'timestamp' and r['review_score'] == 3)
        assert delivered3['orders_count'] == 0
        coverage = {r['population']: r for r in rows(cur, 'q10_coverage.sql')}
        assert coverage['all_statuses']['orders_with_multiple_scores'] == 1
        print('PASS: Q6 ties and units; Q7 threshold and denominators; Q8 no-item status; Q9 payment grains and periods; Q10 multi-score and late variants')
    conn.rollback()
