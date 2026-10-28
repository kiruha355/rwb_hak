// Invoked only by block-b.pg16.py against its own disposable PG16 instance.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readAnswersBlockB } from "../block-b.js";

if (process.env.RWB_BLOCK_B_FIXTURE !== "1" || process.env.PGDATABASE !== "block_b_fixture"
    || !process.env.PGHOST?.startsWith("/")) {
  throw new Error("Requires the private fixture server created by block-b.pg16.py");
}
const psql = process.env.RWB_BLOCK_B_PSQL;
const readEnv = { ...process.env, PGOPTIONS: "-c default_transaction_read_only=on -c statement_timeout=20000" };
const args = ["-X", "-w", "-qAt", "-v", "ON_ERROR_STOP=1"];

// Test-only bridge: PREPARE binds the production query's placeholders. psql's
// literal quoting binds EXECUTE arguments. JSON carries PG numbers/date/NULL.
// This verifies SQL/data shape, not the installed pg or Express packages.
async function q(sql, params = []) {
  const wrapped = `SELECT coalesce(json_agg(r), '[]'::json) FROM (${sql}) r`;
  const variables = params.flatMap((p, i) => p === null ? [] : ["-v", `p${i}=${p}`]);
  const input = params.length
    ? `PREPARE api_query(${params.map(() => "text").join(",")}) AS ${wrapped};\n`
      + `EXECUTE api_query(${params.map((p, i) => p === null ? "NULL" : `:'p${i}'`).join(",")});\n`
    : wrapped + ";\n";
  return JSON.parse(execFileSync(psql, [...args, ...variables], {
    input, env: readEnv, encoding: "utf8", timeout: 15000, stdio: ["pipe", "pipe", "pipe"],
  }));
}

const full = await readAnswersBlockB(q);
const compatible = await readAnswersBlockB(q, {}, { includeBelowThreshold: true });
const relations = {
  q06_price_history: full.q6.rows, q07_delivery_by_state: full.q7.rows,
  q08_status_snapshot: full.q8.rows, q09_payments_2018_by_state: full.q9.states,
  q09_payment_methods: full.q9.methods, q10_review_delivery: full.q10.rows,
  q10_review_coverage: full.q10.coverage,
};
for (const [name, rows] of Object.entries(relations)) {
  const columns = await q(`SELECT column_name FROM information_schema.columns
    WHERE table_schema = 'mart' AND table_name = $1 ORDER BY ordinal_position`, [name]);
  assert.ok(columns.length > 0, name);
  for (const row of rows) assert.deepEqual(Object.keys(row), columns.map((c) => c.column_name), name);
}
assert.equal(full.q7.rows.length, 0); // Ten orders do not satisfy the fixed 500 threshold.
assert.ok(compatible.q7.rows.length > 0);
assert.ok(compatible.q7.rows.every((r) => r.orders_count < 500));
assert.equal(compatible.meta.scope.q7_min_orders, null);
const q7Columns = await q(`SELECT column_name FROM information_schema.columns
  WHERE table_schema = 'mart' AND table_name = 'q07_delivery_by_state' ORDER BY ordinal_position`);
for (const row of compatible.q7.rows) assert.deepEqual(Object.keys(row), q7Columns.map((c) => c.column_name));
assert.equal(full.q10.rows.length, 40);
assert.equal(full.q10.coverage.length, 2);
assert.deepEqual(new Set(full.q9.methods.map((r) => r.period)), new Set(["all_snapshot", "purchase_2018"]));
assert.equal(full.q9.states[0].payment_amount, null);
assert.equal(full.q9.states[0].customer_state, null);
assert.equal(full.q9.states[0].known_payment_amount_sum, 30);
assert.equal(full.q9.states[0].amount_denominator, 3);
assert.ok(full.q6.rows.some((r) => r.price === null && r.purchase_date === null));
assert.ok(full.q6.rows.some((r) => r.purchase_date === "2018-01-01" && typeof r.price === "number"));
assert.ok(full.q10.rows.some((r) => r.orders_count === 0 && r.avg_delivery_days === null && r.late_pct === null));
assert.ok(full.q8.rows.some((r) => r.order_status === "canceled" && r.orders_without_items === 1));

// Test all 16 combinations against the same actual stage-55 rows.
let combinations = 0;
for (const population of ["all_statuses", "delivered"]) {
  for (const late_basis of ["calendar_day", "timestamp"]) {
    for (const score_policy of ["within_score", "single_score_only"]) {
      for (const period of ["all_snapshot", "purchase_2018"]) {
        const selected = await readAnswersBlockB(q, { population, late_basis, score_policy, period });
        assert.deepEqual(selected.q6.rows, full.q6.rows.filter((r) => r.population === population));
        assert.deepEqual(selected.q8, full.q8);
        assert.deepEqual(selected.q9.states, full.q9.states);
        assert.deepEqual(selected.q9.methods, full.q9.methods.filter((r) => r.period === period));
        assert.deepEqual(selected.q10.rows, full.q10.rows.filter((r) =>
          r.population === population && r.late_basis === late_basis && r.score_policy === score_policy));
        assert.equal(selected.q10.rows.length, 5);
        assert.deepEqual(selected.q10.coverage, full.q10.coverage.filter((r) => r.population === population));
        combinations++;
      }
    }
  }
}
// Intentional fault belongs only to this script's disposable database.
execFileSync(psql, args, { input: "DROP VIEW mart.q10_review_coverage;\n",
  env: { ...process.env, PGOPTIONS: "" }, encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] });
await assert.rejects(readAnswersBlockB(q), /q10_review_coverage.*does not exist/);
console.log(JSON.stringify({ status: "pass", scope: "synthetic_stage55_psql_bridge",
  orders: 10, combinations, q10_rows: full.q10.rows.length,
  compatible_q7_rows: compatible.q7.rows.length,
  relations: Object.fromEntries(Object.entries(relations).map(([name, rows]) => [name, rows.length])),
  missing_view: "rejects", actual_express_pg_http: "not_run", full_olist: "not_run" }));
