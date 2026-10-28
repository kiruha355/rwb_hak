"""Independent, deliberately small raw inputs. No production/CSV rows loaded."""
from copy import deepcopy


def fixture():
    tables = {n: [] for n in ('customers', 'orders', 'products', 'sellers',
                              'order_items', 'order_payments', 'order_reviews',
                              'product_category_translation')}
    tables['sellers'] = [dict(seller_id=s, seller_city=s, seller_state='SP') for s in ('s1', 's2')]
    tables['products'] = [dict(product_id=p, product_category_name=c) for p, c in
                          [('a', 'translated'), ('b', 'untranslated'), ('z', None),
                           ('u', 'unknown'), ('unused', 'unused')]]
    tables['product_category_translation'] = [
        dict(product_category_name='translated', product_category_name_english='Translated'),
        dict(product_category_name='unused', product_category_name_english=None)]

    def order(oid, status='delivered', state='SP', purchase='2018-01-01 00:00:00',
              actual='2018-01-03 00:00:00', estimate='2018-01-03 00:00:00',
              carrier='2018-01-02 00:00:00', buyer=None):
        tables['customers'].append(dict(customer_id='c-' + oid, customer_unique_id=buyer or 'b-' + oid,
                                       customer_state=state, customer_city='city-' + oid,
                                       customer_zip_code_prefix='01234'))
        tables['orders'].append(dict(order_id=oid, customer_id='c-' + oid, order_status=status,
                                    order_purchase_timestamp=purchase, order_approved_at=purchase,
                                    order_delivered_carrier_date=carrier,
                                    order_delivered_customer_date=actual,
                                    order_estimated_delivery_date=estimate))

    def item(oid, product, price, freight='0', seller='s1', deadline=None):
        seq = 1 + sum(i['order_id'] == oid for i in tables['order_items'])
        tables['order_items'].append(dict(order_id=oid, order_item_id=str(seq), product_id=product,
                                         seller_id=seller, price=price, freight_value=freight,
                                         shipping_limit_date=deadline))

    def payment(oid, value, parts='1', kind='credit_card'):
        seq = 1 + sum(i['order_id'] == oid for i in tables['order_payments'])
        tables['order_payments'].append(dict(order_id=oid, payment_sequential=str(seq),
                                            payment_type=kind, payment_value=value,
                                            payment_installments=parts))

    def review(oid, score, rid=None, text=None):
        tables['order_reviews'].append(dict(order_id=oid, review_id=rid or 'r-' + oid,
                                           review_score=score, review_comment_title=text,
                                           review_comment_message=text,
                                           review_creation_date='2018-01-04 00:00:00',
                                           review_answer_timestamp='2018-01-04 12:34:56'))

    order('fanout', purchase='2018-01-01 12:00:00', actual='2018-01-03 18:00:00',
          carrier='2018-01-03 00:00:00', buyer='shared-buyer')
    item('fanout', 'a', '10', '1', deadline='2018-01-02 00:00:00')
    item('fanout', 'a', '20', '2', seller='s2', deadline='2018-01-04 00:00:00')
    item('fanout', 'b', '20', deadline='2018-01-04 00:00:00')
    item('fanout', 'b', '20', deadline='2018-01-04 00:00:00')
    payment('fanout', '5', '0'); payment('fanout', '7', '1', 'voucher')
    review('fanout', '5', 'shared-review', 'alpha\nстрока')
    review('fanout', '5', 'repeated-score', '')
    review('fanout', '1', 'conflicting-score', None)
    order('second', state='RJ', purchase='2018-01-02 00:00:00', actual='2018-01-06 00:00:00',
          estimate='2018-01-05 00:00:00', buyer='shared-buyer')
    item('second', 'a', '8'); item('second', 'b', '10', seller='s2')
    payment('second', '18', '3'); review('second', '4', 'shared-review', 'beta')
    order('zero', actual='2018-01-01 00:00:00', carrier='2018-01-01 00:00:00')
    item('zero', 'z', '0'); payment('zero', '0', '0'); review('zero', '2')
    order('no-child', actual=None); review('no-child', '3')
    order('missing-money')
    item('missing-money', 'a', None, '1'); item('missing-money', 'b', '8', None)
    payment('missing-money', None, None, 'boleto'); review('missing-money', None)
    order('canceled', status='canceled', actual='2018-01-05 00:00:00')
    item('canceled', 'u', '999'); payment('canceled', '999', '1', 'voucher'); review('canceled', '3')
    order('new-status', status='returned_custom', state='RS')
    item('new-status', 'u', '99'); review('new-status', '6')
    order('negative', purchase='2018-01-10 00:00:00', actual='2018-01-08 00:00:00',
          carrier='2018-01-09 00:00:00', estimate='2018-01-07 00:00:00'); review('negative', '1')
    order('no-purchase', purchase=None, actual='2018-01-05 00:00:00', estimate='2018-01-06 00:00:00')
    item('no-purchase', 'a', '10'); payment('no-purchase', '9', None, 'voucher'); review('no-purchase', '5')
    order('no-estimate', actual='2018-01-02 00:00:00', estimate=None); review('no-estimate', '4')
    order('carrier-negative', purchase='2018-01-05 00:00:00', actual='2018-01-06 00:00:00',
          carrier='2018-01-04 00:00:00'); review('carrier-negative', '4')
    order('valid-invalid-score'); review('valid-invalid-score', '5'); review('valid-invalid-score', '6', 'invalid-too')
    order('only-invalid-score'); review('only-invalid-score', '6')
    order('null-state', state=None, status='processing', actual=None)
    for oid, purchase, amount, parts in [
            ('before-year', '2017-12-31 23:59:59', '2', '2'),
            ('start-year', '2018-01-01 00:00:00', '4', '4'),
            ('end-year', '2018-12-31 23:59:59', '6', '0'),
            ('after-year', '2019-01-01 00:00:00', '8', '8')]:
        order(oid, state='YY', purchase=purchase, actual=None)
        payment(oid, amount, parts)
    # Scale 499/500/501 to 1/2/3; only answer selector's literal is substituted.
    for count in (1, 2, 3):
        for i in range(count):
            order(f'boundary-{count}-{i}', state=f'K{count}',
                  status='canceled' if count > 1 and i == 0 else 'delivered',
                  actual=None if i == 0 else '2018-01-02 00:00:00')
    return tables


def metamorphic(tables, variant):
    t = deepcopy(tables)
    if variant == 'more_children':
        t['order_reviews'].append(dict(t['order_reviews'][0], review_id='extra-same-score'))
        t['order_payments'].append(dict(t['order_payments'][0], payment_sequential='3', payment_value='11'))
    elif variant == 'item_replication':
        t['order_items'].append(dict(t['order_items'][0], order_item_id='5'))
    elif variant == 'nonrevenue_price_leader':
        for seq, price in enumerate(('1', '2', '3', '4'), 2):
            t['order_items'].append(dict(t['order_items'][0], order_id='new-status',
                                         order_item_id=str(seq), product_id='u', price=price))
    elif variant == 'permuted_input':
        t = {table: list(reversed(rows)) for table, rows in t.items()}
    elif variant == 'complete_money':
        for row in t['order_items']:
            if row['price'] is None:
                row['price'] = '10'
            if row['freight_value'] is None:
                row['freight_value'] = '0'
        for row in t['order_payments']:
            if row['payment_value'] is None:
                row['payment_value'] = '8'
    else:
        raise ValueError(variant)
    return t


def sql_literal(value):
    return 'NULL' if value is None else "'" + str(value).replace("'", "''") + "'"


def insert_sql(tables):
    statements = []
    for table, rows in tables.items():
        for row in rows:
            statements.append('INSERT INTO raw.' + table + ' (' + ','.join(row) + ') VALUES (' +
                              ','.join(sql_literal(v) for v in row.values()) + ');')
    return '\n'.join(statements) + '\n'
