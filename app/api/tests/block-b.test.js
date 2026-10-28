import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import {
  BLOCK_B_VARIANTS, mountAnswersBlockB, parseBlockBFilters, readAnswersBlockB,
} from "../block-b.js";

const names = [
  "q06_price_history", "q07_delivery_by_state", "q08_status_snapshot",
  "q09_payments_2018_by_state", "q09_payment_methods",
  "q10_review_delivery", "q10_review_coverage",
];
const samples = {
  q06_price_history: [{ population: "all_statuses", product_id: "p1", distinct_prices: 2,
    units_with_unknown_price: 1, purchase_date: null, price: null, units_sold: 1 }],
  q07_delivery_by_state: [{ population: "delivered", customer_state: null, late_basis: "timestamp",
    orders_count: 500, duration_denominator: 498, avg_delivery_days: 1.25,
    late_denominator: 499, late_orders: 1, late_pct: 100 / 499 }],
  q08_status_snapshot: [{ order_status: "canceled", orders_count: 1, orders_pct: 10, orders_without_items: 1 }],
  q09_payments_2018_by_state: [{ customer_state: null, payment_count: 2, amount_denominator: 1,
    payment_amount: null, known_payment_amount_sum: 10.25, installments_denominator: 1,
    avg_installments_all_types: 2, credit_installments_denominator: 0, avg_installments_credit_card: null }],
  q09_payment_methods: [{ period: "purchase_2018", payment_type: null, payment_count: 1,
    installments_denominator: 0, avg_installments: null }],
  q10_review_delivery: [{ population: "delivered", score_policy: "single_score_only", late_basis: "calendar_day",
    review_score: 2, orders_count: 0, duration_denominator: 0, avg_delivery_days: null,
    late_denominator: 0, late_orders: 0, late_pct: null }],
  q10_review_coverage: [{ population: "delivered", orders_count: 500, orders_without_score: 4,
    orders_with_multiple_scores: 3, orders_in_multiple_valid_score_groups: 2, orders_with_out_of_range_score: 1 }],
};

function recorder() {
  const calls = [];
  return {
    calls,
    q: async (sql, params = []) => {
      const name = sql.match(/FROM mart\.(\w+)/)?.[1];
      assert.ok(names.includes(name), `Unexpected relation: ${sql}`);
      calls.push({ name, sql, params });
      return samples[name];
    },
  };
}

// Execute the actual server/cache/mount code with inert Express and pg adapters.
// No listening socket, dependency installation or database is needed.
function serverHarness(query) {
  const routes = new Map(), parsers = new Map(), pools = [];
  const app = {
    use() {}, post() {}, listen() {},
    get(path, ...handlers) {
      assert.ok(!routes.has(path), `Duplicate route would shadow an implementation: ${path}`);
      routes.set(path, handlers);
    },
  };
  const source = readFileSync(new URL("../server.js", import.meta.url), "utf8")
    .replace(/^import .*;\n/gm, "");
  vm.runInNewContext(source, {
    express: () => app, cors: () => () => {}, mountAnswersBlockB,
    process: { env: {} }, console: { log() {}, error() {} },
    pg: {
      types: { setTypeParser(oid, parse) { parsers.set(oid, parse); } },
      Pool: class {
        constructor(options) { pools.push(options); }
        async query(sql, params) { return { rows: await query(sql, params) }; }
      },
    },
  });
  return {
    routes, parsers, pools,
    request(path = "/api/answers-block-b", query = {}, originalUrl = path) {
      return new Promise((resolve, reject) => {
        const handlers = routes.get(path);
        assert.ok(handlers, `No route mounted at ${path}`);
        let index = 0;
        const res = {
          statusCode: 200,
          status(code) { this.statusCode = code; return this; },
          json(data) { resolve({ status: this.statusCode, body: JSON.parse(JSON.stringify(data)) }); },
        };
        const req = { query, originalUrl };
        const next = () => {
          try { Promise.resolve(handlers[index++](req, res, next)).catch(reject); }
          catch (error) { reject(error); }
        };
        next();
      });
    },
  };
}

test("unfiltered response reads exactly seven views, retaining stage-55 fields and NULL", async () => {
  const { q, calls } = recorder();
  const body = await readAnswersBlockB(q);
  assert.deepEqual(calls.map((c) => c.name), names);
  assert.deepEqual(body.q6.rows, samples.q06_price_history);
  assert.deepEqual(body.q7.rows, samples.q07_delivery_by_state);
  assert.deepEqual(body.q8.rows, samples.q08_status_snapshot);
  assert.deepEqual(body.q9.states, samples.q09_payments_2018_by_state);
  assert.deepEqual(body.q9.methods, samples.q09_payment_methods);
  assert.deepEqual(body.q10.rows, samples.q10_review_delivery);
  assert.deepEqual(body.q10.coverage, samples.q10_review_coverage);
  assert.equal(body.q9.states[0].payment_amount, null);
  assert.equal(body.q10.rows[0].late_pct, null);
  assert.equal(body.meta.scope.q9_states, "purchase_2018");
  assert.equal(body.meta.scope.q7_min_orders, 500);
  assert.deepEqual(body.meta.variants, BLOCK_B_VARIANTS);
  assert.deepEqual(body.meta.filters, { population: null, late_basis: null, score_policy: null, period: null });
});

test("variant selections bind parameters only to applicable relations", async () => {
  const { q, calls } = recorder();
  const selection = { population: "delivered", late_basis: "timestamp",
    score_policy: "single_score_only", period: "purchase_2018" };
  assert.deepEqual((await readAnswersBlockB(q, selection)).meta.filters, selection);
  assert.deepEqual(calls.map((c) => c.params), [
    ["delivered"], ["delivered", "timestamp", 500], [], [], ["purchase_2018"],
    ["delivered", "single_score_only", "timestamp"], ["delivered"],
  ]);
  assert.match(calls[1].sql, /orders_count >= \$3::bigint/);
  for (const { sql } of calls) {
    assert.doesNotMatch(sql, /\b(?:INSERT|UPDATE|DELETE|DROP|CREATE|raw\.|core\.)\b/i);
    for (const value of Object.values(selection)) assert.ok(!sql.includes(`'${value}'`));
  }
  const defaults = recorder();
  await readAnswersBlockB(defaults.q);
  assert.deepEqual(calls.map((c) => c.sql), defaults.calls.map((c) => c.sql));
});

test("every named enum value is accepted; absence means all variants", () => {
  for (const [key, values] of Object.entries(BLOCK_B_VARIANTS)) {
    for (const value of values) assert.equal(parseBlockBFilters({ [key]: value })[key], value);
  }
});

test("invalid, unsupported and structured parameters fail before queries", async () => {
  const bad = [null, [], "delivered", { from: "2018-01" }, { to: "2018-12" },
    { category: "health_beauty" }, { state: "SP" }, { limit: "5" }, { min_orders: "0" },
    { population: "DELIVERED" }, { population: "delivered' OR TRUE --" },
    { late_basis: "" }, { score_policy: "latest" }, { period: "2018" },
    { population: ["all_statuses", "delivered"] }, { late_basis: { x: "timestamp" } },
    { period: null }, { population: true }, { period: 2018 },
    JSON.parse('{"__proto__":"delivered"}'), { constructor: "delivered" }];
  let calls = 0;
  for (const input of bad) await assert.rejects(readAnswersBlockB(async () => { calls++; return []; }, input));
  assert.equal(calls, 0);
});

test("HTTP mount shares actual cache and pg parsers; Q1–Q5 remain mounted", async () => {
  const { q, calls } = recorder();
  const h = serverHarness(q);
  assert.ok(h.routes.has("/api/answers"));
  assert.equal(h.parsers.get(1700)("10.25"), 10.25);
  assert.equal(h.parsers.get(20)("500"), 500);
  assert.equal(h.parsers.get(1082)("2018-01-01"), "2018-01-01");
  assert.equal(h.parsers.get(1700)(null), null);
  assert.match(h.pools[0].options, /default_transaction_read_only=on/);
  assert.equal((await h.request()).status, 200);
  assert.equal((await h.request()).status, 200);
  assert.equal(calls.length, 7);
  // Validation also runs on an already-cached URL.
  const bad = await h.request(undefined, { category: "x" });
  assert.equal(bad.status, 400);
  assert.equal(bad.body.code, "invalid_block_b_filter");
  assert.equal(calls.length, 7);
  assert.equal((await h.request(undefined, { population: "delivered" },
    "/api/answers-block-b?population=delivered")).status, 200);
  assert.equal(calls.length, 14);
});

test("existing /answers-b keeps arrays, available and below-threshold state input", async () => {
  const { q, calls } = recorder();
  const h = serverHarness(q);
  const legacy = await h.request("/api/answers-b");
  assert.equal(legacy.status, 200);
  assert.equal(legacy.body.available, true);
  assert.deepEqual(legacy.body.q6, samples.q06_price_history);
  assert.deepEqual(legacy.body.q7, samples.q07_delivery_by_state);
  assert.deepEqual(legacy.body.q8, samples.q08_status_snapshot);
  assert.deepEqual(legacy.body.q9.states, samples.q09_payments_2018_by_state);
  assert.deepEqual(legacy.body.q10.coverage, samples.q10_review_coverage);
  assert.equal(legacy.body.meta.scope.q7_min_orders, null);
  assert.deepEqual(calls.find((c) => c.name === "q07_delivery_by_state").params, [null, null, null]);
  const modern = await h.request();
  assert.equal(modern.body.meta.scope.q7_min_orders, 500);
  assert.deepEqual(modern.body.q6.rows, legacy.body.q6);
  assert.deepEqual(modern.body.q9, legacy.body.q9);
  assert.deepEqual(modern.body.q10, legacy.body.q10);
  assert.equal(calls.length, 14); // Both routes use the same seven query definitions.
});

test("both routes reject duplicate/unknown filters and missing views", async () => {
  let calls = 0;
  const h = serverHarness(async () => { calls++; throw new Error("missing stage-55 view"); });
  for (const path of ["/api/answers-b", "/api/answers-block-b"]) {
    for (const query of [{ population: ["delivered", "all_statuses"] }, { from: "2018-01" }]) {
      const bad = await h.request(path, query);
      assert.equal(bad.status, 400);
      assert.equal(bad.body.code, "invalid_block_b_filter");
    }
    const failed = await h.request(path);
    assert.equal(failed.status, 500);
    assert.deepEqual(failed.body, { error: "missing stage-55 view" });
  }
  assert.equal(calls, 14);
});

test("each missing view fails the whole request; failures are not cached", async () => {
  for (const name of names) {
    let failing = true, calls = 0;
    const h = serverHarness(async (sql) => {
      calls++;
      if (failing && sql.includes(`FROM mart.${name}\n`)) {
        throw Object.assign(new Error(`relation mart.${name} does not exist`), { code: "42P01" });
      }
      return [{ observed: true }];
    });
    const failed = await h.request();
    assert.equal(failed.status, 500, name);
    assert.match(failed.body.error, /does not exist/);
    assert.equal(failed.body.q6, undefined);
    failing = false;
    assert.equal((await h.request()).status, 200);
    assert.equal(calls, 14);
    await h.request();
    assert.equal(calls, 14);
  }
});

test("database timeout/connection/column failures stay HTTP 500, never partial success", async () => {
  for (const code of ["57014", "08006", "42703"]) {
    const h = serverHarness(async () => { throw Object.assign(new Error(`DB error ${code}`), { code }); });
    const result = await h.request();
    assert.equal(result.status, 500);
    assert.deepEqual(result.body, { error: `DB error ${code}` });
  }
});

test("genuine empty results remain successful and carry scope/variant metadata", async () => {
  const result = await serverHarness(async () => []).request();
  assert.equal(result.status, 200);
  assert.deepEqual(result.body.q6.rows, []);
  assert.deepEqual(result.body.q7.rows, []);
  assert.deepEqual(result.body.q9, { states: [], methods: [] });
  assert.deepEqual(result.body.q10, { rows: [], coverage: [] });
  assert.ok(result.body.meta.scope);
  assert.ok(result.body.meta.variants.score_policy.includes("within_score"));
});
