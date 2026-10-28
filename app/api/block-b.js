// Read-only Q6–Q10 adapter for the seven stage-55 mart views.
// q supplies rows using the server's existing pg numeric/bigint/date parsers.
export const BLOCK_B_VARIANTS = Object.freeze({
  population: Object.freeze(["all_statuses", "delivered"]),
  late_basis: Object.freeze(["calendar_day", "timestamp"]),
  score_policy: Object.freeze(["within_score", "single_score_only"]),
  period: Object.freeze(["all_snapshot", "purchase_2018"]),
});

export const BLOCK_B_SCOPE = Object.freeze({
  q6: "all_snapshot",
  q7: "all_snapshot",
  q8: "all_snapshot",
  q9_states: "purchase_2018",
  q9_methods: "named_periods",
  q10: "all_snapshot",
  q7_min_orders: 500,
  unsupported_filters: Object.freeze(["from", "to", "state", "category"]),
});

export function parseBlockBFilters(query = {}) {
  if (query === null || typeof query !== "object" || Array.isArray(query)) {
    throw new Error("Query parameters must be an object");
  }
  for (const key of Object.keys(query)) {
    if (!Object.hasOwn(BLOCK_B_VARIANTS, key)) {
      throw new Error(`Unsupported block B filter: ${key}`);
    }
  }
  return Object.fromEntries(Object.entries(BLOCK_B_VARIANTS).map(([key, allowed]) => {
    if (!Object.hasOwn(query, key)) return [key, null];
    const value = query[key];
    if (typeof value !== "string" || !allowed.includes(value)) {
      throw new Error(`Invalid ${key}; expected one of: ${allowed.join(", ")}`);
    }
    return [key, value];
  }));
}

// SQL structure and relation/column names are fixed. All values are bound.
const SQL = Object.freeze({
  q6: `SELECT population, product_id, distinct_prices, units_with_unknown_price,
              purchase_date, price, units_sold
       FROM mart.q06_price_history
       WHERE ($1::text IS NULL OR population = $1)
       ORDER BY population, product_id, purchase_date NULLS LAST, price NULLS LAST`,
  q7: `SELECT population, customer_state, late_basis, orders_count,
              duration_denominator, avg_delivery_days, late_denominator, late_orders, late_pct
       FROM mart.q07_delivery_by_state
       WHERE ($3::bigint IS NULL OR orders_count >= $3::bigint)
         AND ($1::text IS NULL OR population = $1)
         AND ($2::text IS NULL OR late_basis = $2)
       ORDER BY population, customer_state NULLS LAST, late_basis`,
  q8: `SELECT order_status, orders_count, orders_pct, orders_without_items
       FROM mart.q08_status_snapshot
       ORDER BY orders_count DESC, order_status`,
  q9States: `SELECT customer_state, payment_count, amount_denominator, payment_amount,
                    known_payment_amount_sum, installments_denominator,
                    avg_installments_all_types, credit_installments_denominator,
                    avg_installments_credit_card
             FROM mart.q09_payments_2018_by_state
             ORDER BY customer_state NULLS LAST`,
  q9Methods: `SELECT period, payment_type, payment_count, installments_denominator, avg_installments
              FROM mart.q09_payment_methods
              WHERE ($1::text IS NULL OR period = $1)
              ORDER BY period, payment_type NULLS LAST`,
  q10: `SELECT population, score_policy, late_basis, review_score, orders_count,
               duration_denominator, avg_delivery_days, late_denominator, late_orders, late_pct
        FROM mart.q10_review_delivery
        WHERE ($1::text IS NULL OR population = $1)
          AND ($2::text IS NULL OR score_policy = $2)
          AND ($3::text IS NULL OR late_basis = $3)
        ORDER BY population, score_policy, late_basis, review_score`,
  q10Coverage: `SELECT population, orders_count, orders_without_score, orders_with_multiple_scores,
                       orders_in_multiple_valid_score_groups, orders_with_out_of_range_score
                FROM mart.q10_review_coverage
                WHERE ($1::text IS NULL OR population = $1)
                ORDER BY population`,
});

export async function readAnswersBlockB(q, query = {}, { includeBelowThreshold = false } = {}) {
  // Validate before issuing any query, including direct uses outside Express.
  const filters = parseBlockBFilters(query);
  const { population, late_basis, score_policy, period } = filters;
  const [q6, q7, q8, states, methods, q10, coverage] = await Promise.all([
    q(SQL.q6, [population]),
    // The existing AnswersB page counts states below 500 before hiding them.
    // Preserve that input on /answers-b; the new contract applies the task threshold.
    q(SQL.q7, [population, late_basis, includeBelowThreshold ? null : 500]),
    q(SQL.q8),
    q(SQL.q9States),
    q(SQL.q9Methods, [period]),
    q(SQL.q10, [population, score_policy, late_basis]),
    q(SQL.q10Coverage, [population]),
  ]);
  return {
    q6: { rows: q6 },
    q7: { rows: q7 },
    q8: { rows: q8 },
    q9: { states, methods },
    q10: { rows: q10, coverage },
    meta: {
      scope: { ...BLOCK_B_SCOPE, q7_min_orders: includeBelowThreshold ? null : 500 },
      variants: BLOCK_B_VARIANTS, filters,
    },
  };
}

export function mountAnswersBlockB(app, { q, cached }) {
  // Run validation even on a cache hit; errors never enter the success cache.
  const validate = (req, res, next) => {
    try {
      parseBlockBFilters(req.query);
      next();
    } catch (error) {
      res.status(400).json({ error: error.message, code: "invalid_block_b_filter" });
    }
  };
  app.get("/api/answers-block-b", validate, cached((req) => readAnswersBlockB(q, req.query)));
  // Compatibility adapter for the existing AnswersB.tsx: keep its array shape,
  // available flag and below-threshold input; add all stage-55 fields and meta.
  app.get("/api/answers-b", validate, cached(async (req) => {
    const data = await readAnswersBlockB(q, req.query, { includeBelowThreshold: true });
    return { available: true, ...data, q6: data.q6.rows, q7: data.q7.rows, q8: data.q8.rows };
  }));
}
