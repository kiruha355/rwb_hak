// Deliberately synthetic UI data. Never imported by production components.
module.exports = function fixture() {
  const populations = ["all_statuses", "delivered"], bases = ["calendar_day", "timestamp"];
  const policies = ["within_score", "single_score_only"];
  const q6 = populations.flatMap(population => ["leader-aaaaaaaaaaaaaaaaaaaaaaaaa", "tied-bbbbbbbbbbbbbbbbbbbbbbbbbbb"].flatMap(product_id => [
    { purchase_date: "2017-03-01", price: "0.00", units_sold: "2" },
    { purchase_date: "2017-03-01", price: "35.00", units_sold: "3" },
    { purchase_date: "2018-08-29", price: "50.00", units_sold: "1" },
    { purchase_date: null, price: null, units_sold: "2" },
  ].map(row => ({ population, product_id, distinct_prices: "3", units_with_unknown_price: "2", ...row }))));
  const q7 = populations.flatMap(population => [
    { customer_state: "SP", orders_count: 500, duration_denominator: 490, avg_delivery_days: "12.25", late_denominator: 495, late_orders: 20, late_pct: "4.040404" },
    { customer_state: "BELOW_THRESHOLD", orders_count: 499, duration_denominator: 490, avg_delivery_days: 11, late_denominator: 495, late_orders: 20, late_pct: 4 },
    { customer_state: null, orders_count: 501, duration_denominator: 0, avg_delivery_days: null, late_denominator: 0, late_orders: 0, late_pct: null },
  ].flatMap(row => bases.map(late_basis => ({ population, late_basis, ...row,
    ...(row.customer_state === "SP" && late_basis === "timestamp" ? { late_orders: 30, late_pct: 30 / 495 * 100 } : {}),
  }))));
  const q10 = populations.flatMap(population => policies.flatMap(score_policy => bases.flatMap(late_basis => [1, 2, 3, 4, 5].map(review_score => {
    const empty = review_score === 3;
    const orders_count = empty ? 0 : (population === "delivered" ? 510 : 520) + review_score;
    const late_orders = empty ? 0 : (6 - review_score) * 20 + (late_basis === "timestamp" ? 9 : 0) + (score_policy === "within_score" ? 3 : 0);
    const duration_denominator = empty ? 0 : orders_count - 3, late_denominator = empty ? 0 : orders_count - 2;
    return { population, score_policy, late_basis, review_score, orders_count,
      duration_denominator, avg_delivery_days: empty ? null : 30 - review_score * 3 + (score_policy === "within_score" ? 0.3 : 0),
      late_denominator, late_orders, late_pct: empty ? null : late_orders / late_denominator * 100 };
  }))));
  return {
    q6: { rows: q6 }, q7: { rows: q7 },
    q8: { rows: [
      { order_status: "delivered", orders_count: 900, orders_pct: 90, orders_without_items: 0 },
      { order_status: "canceled", orders_count: 90, orders_pct: 9, orders_without_items: 80 },
      { order_status: null, orders_count: 10, orders_pct: 1, orders_without_items: 1 },
    ] },
    q9: {
      states: [
        { customer_state: "SP", payment_count: 500, amount_denominator: 499, payment_amount: null,
          known_payment_amount_sum: "12500.50", installments_denominator: 499, avg_installments_all_types: "2.25",
          credit_installments_denominator: 450, avg_installments_credit_card: "2.50" },
        { customer_state: null, payment_count: 2, amount_denominator: 2, payment_amount: "0.00",
          known_payment_amount_sum: "0.00", installments_denominator: 2, avg_installments_all_types: 0,
          credit_installments_denominator: 0, avg_installments_credit_card: null },
      ],
      methods: ["all_snapshot", "purchase_2018"].flatMap(period => [
        { payment_type: "credit_card", payment_count: period === "all_snapshot" ? 900 : 450, installments_denominator: 440, avg_installments: "2.50" },
        { payment_type: "voucher", payment_count: 8, installments_denominator: 8, avg_installments: "0.00" },
        { payment_type: null, payment_count: 1, installments_denominator: 0, avg_installments: null },
      ].map(row => ({ period, ...row }))),
    },
    q10: { rows: q10, coverage: populations.map(population => ({ population, orders_count: 2500,
      orders_without_score: 50, orders_with_multiple_scores: 20,
      orders_in_multiple_valid_score_groups: 18, orders_with_out_of_range_score: 3,
    })) },
    meta: { scope: { source: "SYNTHETIC_UI_QA_ONLY", full_snapshot: true, state_payments: "purchase_2018" } },
  };
};
