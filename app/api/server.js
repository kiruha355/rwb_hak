// Capibara API: read-only access to the core/mart model for the dashboard.
// Business numbers come only from mart views (and core for lineage); raw is read
// only to show where the model came from.
import express from "express";
import cors from "cors";
import pg from "pg";

pg.types.setTypeParser(1700, (v) => (v === null ? null : Number(v))); // numeric
pg.types.setTypeParser(20, (v) => (v === null ? null : Number(v))); // bigint
pg.types.setTypeParser(1082, (v) => v); // date as string

const pool = new pg.Pool({
  connectionString: process.env.DATABASE_URL || "postgresql://hack:hack@127.0.0.1:5432/marketplace",
  max: 8,
  options: "-c default_transaction_read_only=on -c statement_timeout=20000",
});

const q = async (sql, params = []) => (await pool.query(sql, params)).rows;

const app = express();
app.use(cors());

// ---- small cache: dashboards repeat the same queries a lot
const cache = new Map();
const TTL = 10 * 60 * 1000;
const cached = (handler) => async (req, res) => {
  const key = req.originalUrl;
  const hit = cache.get(key);
  if (hit && Date.now() - hit.t < TTL) return res.json(hit.data);
  try {
    const data = await handler(req);
    cache.set(key, { t: Date.now(), data });
    res.json(data);
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: e.message });
  }
};
app.post("/api/cache/clear", (_req, res) => {
  cache.clear();
  res.json({ ok: true });
});

// ---- filters: period (YYYY-MM), customer state, category
const MONTH = /^\d{4}-\d{2}$/;
function filters(req) {
  const f = {
    from: MONTH.test(req.query.from || "") ? req.query.from : "2016-09",
    to: MONTH.test(req.query.to || "") ? req.query.to : "2018-08",
    state: /^[A-Z]{2}$/.test(req.query.state || "") ? req.query.state : null,
    category: typeof req.query.category === "string" && req.query.category.length < 120 ? req.query.category : null,
  };
  return f;
}
// WHERE for an order-grain relation aliased `o` (v_orders columns)
function orderWhere(f, params, alias = "o") {
  const w = [];
  params.push(f.from + "-01");
  w.push(`${alias}.purchase_month >= $${params.length}`);
  params.push(f.to + "-01");
  w.push(`${alias}.purchase_month <= $${params.length}`);
  if (f.state) {
    params.push(f.state);
    w.push(`${alias}.customer_state = $${params.length}`);
  }
  if (f.category) {
    params.push(f.category);
    w.push(`EXISTS (SELECT 1 FROM core.fact_order_item fi JOIN core.dim_product p USING (product_id)
             WHERE fi.order_id = ${alias}.order_id AND p.category_key = $${params.length})`);
  }
  return w.join(" AND ");
}
// WHERE for item grain (v_order_items aliased `i`)
function itemWhere(f, params, alias = "i") {
  const w = [];
  params.push(f.from + "-01");
  w.push(`${alias}.purchase_month >= $${params.length}`);
  params.push(f.to + "-01");
  w.push(`${alias}.purchase_month <= $${params.length}`);
  if (f.state) {
    params.push(f.state);
    w.push(`${alias}.customer_state = $${params.length}`);
  }
  if (f.category) {
    params.push(f.category);
    w.push(`${alias}.category_key = $${params.length}`);
  }
  return w.join(" AND ");
}

// ---- meta for filter controls
app.get(
  "/api/meta",
  cached(async () => {
    const [states, categories, months, built] = await Promise.all([
      q(`SELECT customer_state AS state, count(*) AS orders FROM core.fact_order GROUP BY 1 ORDER BY 2 DESC`),
      q(`SELECT category_key AS key, coalesce(name_en, name_pt, 'unknown') AS name FROM core.dim_category ORDER BY 2`),
      q(`SELECT DISTINCT to_char(month_start, 'YYYY-MM') AS m FROM core.dim_date
         WHERE month_start BETWEEN '2016-09-01' AND '2018-10-01' ORDER BY 1`),
      q(`SELECT max(checked_at) AS built_at, count(*) AS checks, count(*) FILTER (WHERE ok) AS passed,
                count(*) FILTER (WHERE severity = 'error' AND NOT ok) AS failed_errors
         FROM core.check_results`),
    ]);
    return { states, categories, months: months.map((r) => r.m), build: built[0] };
  })
);

// ---- overview: KPI + monthly series
app.get(
  "/api/overview",
  cached(async (req) => {
    const f = filters(req);
    const p1 = [], p2 = [], p3 = [], p4 = [], p5 = [], p6 = [], p7 = [];
    const [kpi, rev, late, monthsOrders, monthsRev, monthsLate, repeat] = await Promise.all([
      q(`SELECT count(*) AS orders_placed,
                count(*) FILTER (WHERE o.is_delivered) AS orders_delivered,
                avg(o.order_gmv) FILTER (WHERE o.is_revenue AND o.order_gmv IS NOT NULL) AS avg_check,
                count(*) FILTER (WHERE o.is_revenue AND o.order_gmv IS NOT NULL) AS avg_check_n,
                count(DISTINCT o.customer_unique_id) AS buyers,
                avg(o.review_avg_pair_score) FILTER (WHERE o.review_score_count > 0) AS review_avg,
                count(*) FILTER (WHERE o.review_score_count > 0) AS review_n
         FROM mart.v_orders o WHERE ${orderWhere(f, p1)}`, p1),
      q(`SELECT sum(i.price) AS item_revenue, count(*) AS item_rows
         FROM mart.v_order_items i WHERE i.is_revenue AND ${itemWhere(f, p2)}`, p2),
      q(`SELECT count(*) AS n, avg(d.is_late_calendar_day::int) AS late_share,
                percentile_cont(0.5) WITHIN GROUP (ORDER BY d.purchase_to_delivery_days) AS median_days
         FROM mart.v_orders o JOIN mart.v_order_delivery_variants d USING (order_id)
         WHERE o.is_delivered AND o.order_delivered_customer_date IS NOT NULL AND ${orderWhere(f, p3)}`, p3),
      q(`SELECT to_char(o.purchase_month, 'YYYY-MM') AS m, count(*) AS placed,
                count(*) FILTER (WHERE o.is_delivered) AS delivered,
                count(DISTINCT o.customer_unique_id) AS buyers,
                avg(o.order_gmv) FILTER (WHERE o.is_revenue AND o.order_gmv IS NOT NULL) AS avg_check,
                avg(o.review_avg_pair_score) FILTER (WHERE o.review_score_count > 0) AS review_avg
         FROM mart.v_orders o WHERE ${orderWhere(f, p4)} GROUP BY 1`, p4),
      q(`SELECT to_char(i.purchase_month, 'YYYY-MM') AS m, sum(i.price) AS revenue
         FROM mart.v_order_items i WHERE i.is_revenue AND ${itemWhere(f, p5)} GROUP BY 1`, p5),
      q(`SELECT to_char(o.purchase_month, 'YYYY-MM') AS m, avg(d.is_late_calendar_day::int) AS late_share, count(*) AS n
         FROM mart.v_orders o JOIN mart.v_order_delivery_variants d USING (order_id)
         WHERE o.is_delivered AND o.order_delivered_customer_date IS NOT NULL AND ${orderWhere(f, p6)} GROUP BY 1`, p6),
      // repeat = a person with 2+ orders inside the selected slice
      q(`SELECT count(*) FILTER (WHERE n >= 2) AS repeat_buyers
         FROM (SELECT o.customer_unique_id, count(*) AS n FROM mart.v_orders o
               WHERE ${orderWhere(f, p7)} GROUP BY 1) t`, p7),
    ]);
    // calendar months so empty months stay visible as 0
    const cal = await q(
      `SELECT DISTINCT to_char(month_start, 'YYYY-MM') AS m FROM core.dim_date
       WHERE month_start BETWEEN $1 AND $2 ORDER BY 1`,
      [f.from + "-01", f.to + "-01"]
    );
    const by = (rows) => Object.fromEntries(rows.map((r) => [r.m, r]));
    const mo = by(monthsOrders), mr = by(monthsRev), ml = by(monthsLate);
    const series = cal.map(({ m }) => ({
      month: m,
      placed: mo[m]?.placed ?? 0,
      delivered: mo[m]?.delivered ?? 0,
      buyers: mo[m]?.buyers ?? 0,
      avg_check: mo[m]?.avg_check ?? null,
      review_avg: mo[m]?.review_avg ?? null,
      revenue: mr[m]?.revenue ?? 0,
      late_share: ml[m] ? ml[m].late_share : null,
      late_n: ml[m]?.n ?? 0,
    }));
    return { filters: f, kpi: { ...kpi[0], ...rev[0], ...late[0], ...repeat[0] }, series };
  })
);

// ---- delivery: price of lateness
app.get(
  "/api/delivery",
  cached(async (req) => {
    const f = filters(req);
    const base = (p) => `FROM mart.v_orders o JOIN mart.v_order_delivery_variants d USING (order_id)
      WHERE o.is_delivered AND o.order_delivered_customer_date IS NOT NULL AND ${orderWhere(f, p)}`;
    const p1 = [], p2 = [], p3 = [], p4 = [];
    const [split, states, stage, buckets] = await Promise.all([
      q(`SELECT d.is_late_calendar_day AS late, count(*) AS n,
                avg(o.review_avg_pair_score) FILTER (WHERE o.review_score_count > 0) AS score,
                avg((o.review_avg_pair_score <= 2)::int) FILTER (WHERE o.review_score_count > 0) AS low_share,
                count(*) FILTER (WHERE o.review_score_count > 0) AS scored
         ${base(p1)} GROUP BY 1`, p1),
      q(`SELECT o.customer_state AS state, count(*) AS n, avg(d.is_late_calendar_day::int) AS late_share,
                percentile_cont(0.5) WITHIN GROUP (ORDER BY d.purchase_to_delivery_days) AS median_days,
                avg(o.review_avg_pair_score) FILTER (WHERE o.review_score_count > 0) AS score
         ${base(p2)} GROUP BY 1 ORDER BY 2 DESC`, p2),
      q(`SELECT count(*) AS late_n,
                count(*) FILTER (WHERE d.is_handover_after_max_item_deadline) AS handover_late,
                count(*) FILTER (WHERE NOT d.is_handover_after_max_item_deadline) AS after_handover,
                count(*) FILTER (WHERE d.is_handover_after_max_item_deadline IS NULL) AS unknown_stage
         ${base(p3)} AND d.is_late_calendar_day`, p3),
      q(`SELECT CASE WHEN d.purchase_to_delivery_days < 8 THEN '0–7'
                     WHEN d.purchase_to_delivery_days < 15 THEN '8–14'
                     WHEN d.purchase_to_delivery_days < 22 THEN '15–21'
                     WHEN d.purchase_to_delivery_days < 31 THEN '22–30'
                     WHEN d.purchase_to_delivery_days < 46 THEN '31–45' ELSE '46+' END AS bucket,
                count(*) AS n, avg(d.is_late_calendar_day::int) AS late_share
         ${base(p4)} GROUP BY 1`, p4),
    ]);
    const order = ["0–7", "8–14", "15–21", "22–30", "31–45", "46+"];
    buckets.sort((a, b) => order.indexOf(a.bucket) - order.indexOf(b.bucket));
    return { filters: f, split, states, stage: stage[0], buckets };
  })
);

// ---- late orders: the working list for logistics
app.get(
  "/api/late-orders",
  cached(async (req) => {
    const f = filters(req);
    const p = [];
    const rows = await q(
      `SELECT o.order_id, o.customer_state AS state, o.customer_city AS city,
              o.order_purchase_timestamp::date AS purchased,
              o.order_estimated_delivery_date::date AS promised,
              o.order_delivered_customer_date::date AS delivered,
              (o.order_delivered_customer_date::date - o.order_estimated_delivery_date::date) AS days_late,
              d.is_handover_after_max_item_deadline AS handover_late,
              o.sellers_count, o.order_gmv, o.review_avg_pair_score AS score
       FROM mart.v_orders o JOIN mart.v_order_delivery_variants d USING (order_id)
       WHERE o.is_delivered AND d.is_late_calendar_day AND ${orderWhere(f, p)}
       ORDER BY days_late DESC, o.order_gmv DESC NULLS LAST LIMIT 60`,
      p
    );
    return { filters: f, rows };
  })
);

// ---- commerce: categories, sellers, payment types
app.get(
  "/api/commerce",
  cached(async (req) => {
    const f = filters(req);
    const limit = [10, 25, 50, 100].includes(Number(req.query.limit)) ? Number(req.query.limit) : 10;
    const p1 = [], p2 = [], p3 = [];
    const [cats, sellers, pays] = await Promise.all([
      q(`SELECT i.category_key AS key, coalesce(i.category_name_en, i.category_name_pt, 'unknown') AS name,
                i.is_unknown_category AS is_unknown, sum(i.price) AS revenue, count(*) AS units,
                count(DISTINCT i.order_id) AS orders, count(DISTINCT i.seller_id) AS sellers
         FROM mart.v_order_items i WHERE i.is_revenue AND ${itemWhere(f, p1)}
         GROUP BY 1, 2, 3 ORDER BY 4 DESC`, p1),
      q(`SELECT i.seller_id, i.seller_city, i.seller_state, sum(i.price) AS revenue,
                count(DISTINCT i.order_id) AS orders, count(*) AS units
         FROM mart.v_order_items i WHERE i.is_revenue AND ${itemWhere(f, p2)}
         GROUP BY 1, 2, 3 ORDER BY 4 DESC LIMIT ${limit}`, p2),
      q(`SELECT p.payment_type AS type, count(*) AS payments, sum(p.payment_value) AS amount,
                avg(p.payment_installments) AS avg_installments
         FROM core.fact_payment p JOIN mart.v_orders o USING (order_id)
         WHERE ${orderWhere(f, p3)} GROUP BY 1 ORDER BY 3 DESC`, p3),
    ]);
    const total = cats.reduce((s, c) => s + (c.revenue || 0), 0);
    return { filters: f, total, categories: cats, sellers, payments: pays };
  })
);

// ---- model lineage: raw -> core -> mart
const RAW_TO_CORE = [
  { raw: "orders", core: ["fact_order", "dim_order_status"], rule: "даты из текста в timestamp; статусы собираются в справочник с правилом выручки" },
  { raw: "customers", core: ["dim_customer", "dim_customer_context", "fact_order"], rule: "человек = customer_unique_id; адрес остаётся снимком на заказе; индекс дополняется до 5 цифр" },
  { raw: "order_items", core: ["fact_order_item"], rule: "цена и доставка в numeric; ключ = заказ + номер позиции" },
  { raw: "order_payments", core: ["fact_payment"], rule: "сумма в numeric; ключ = заказ + номер платежа" },
  { raw: "order_reviews", core: ["fact_review"], rule: "ключ = отзыв + заказ: повторяющийся review_id не теряется" },
  { raw: "products", core: ["dim_product", "dim_category"], rule: "размеры в numeric; пустая категория → unknown" },
  { raw: "sellers", core: ["dim_seller"], rule: "текст сохраняется как есть; индекс проверяется отдельно" },
  { raw: "product_category_translation", core: ["dim_category"], rule: "английское имя; нет перевода ≠ нет категории" },
  { raw: null, core: ["dim_date"], rule: "календарь генерируется: месяцы без заказов остаются в отчётах" },
];
app.get(
  "/api/model",
  cached(async () => {
    const rawTables = RAW_TO_CORE.filter((r) => r.raw).map((r) => r.raw);
    const rawCounts = await Promise.all(
      rawTables.map(async (t) => ({ table: t, rows: (await q(`SELECT count(*) AS n FROM raw.${t}`))[0].n }))
    );
    const [coreTables, keys, cols, martObjs, deps, balance] = await Promise.all([
      q(`SELECT c.relname AS name, obj_description(c.oid) AS comment
         FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'core' AND c.relkind = 'r' ORDER BY 1`),
      q(`SELECT conrelid::regclass::text AS tbl, contype::text AS type, pg_get_constraintdef(oid) AS def
         FROM pg_constraint WHERE connamespace = 'core'::regnamespace AND contype IN ('p', 'f') ORDER BY 1`),
      q(`SELECT table_schema AS schema, table_name AS name, column_name AS col, data_type AS type
         FROM information_schema.columns WHERE table_schema IN ('core', 'mart') ORDER BY table_name, ordinal_position`),
      q(`SELECT c.relname AS name, CASE c.relkind WHEN 'v' THEN 'view' ELSE 'table' END AS kind,
                obj_description(c.oid) AS comment
         FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'mart' AND c.relkind IN ('v', 'r') ORDER BY 1`),
      q(`SELECT DISTINCT r.ev_class::regclass::text AS view, d.refobjid::regclass::text AS uses
         FROM pg_rewrite r JOIN pg_depend d ON d.objid = r.oid AND d.refobjid <> r.ev_class
         JOIN pg_class c ON c.oid = d.refobjid AND c.relkind IN ('r', 'v')
         JOIN pg_class v ON v.oid = r.ev_class JOIN pg_namespace vn ON vn.oid = v.relnamespace
         WHERE vn.nspname = 'mart'`),
      q(`SELECT check_name, expected, actual, ok FROM core.check_results WHERE check_group = 'balance' ORDER BY 1`),
    ]);
    const coreCounts = await Promise.all(
      coreTables.map(async (t) => ({ ...t, rows: (await q(`SELECT count(*) AS n FROM core.${t.name}`))[0].n }))
    );
    const strip = (s) => s.replace(/^(core|mart)\./, "");
    return {
      raw: RAW_TO_CORE.map((r) => ({ ...r, rows: rawCounts.find((x) => x.table === r.raw)?.rows ?? null })),
      core: coreCounts.map((t) => ({
        ...t,
        keys: keys.filter((k) => strip(k.tbl) === t.name),
        columns: cols.filter((c) => c.schema === "core" && c.name === t.name).map((c) => ({ name: c.col, type: c.type })),
      })),
      mart: martObjs.map((m) => ({
        ...m,
        uses: deps.filter((d) => strip(d.view) === m.name).map((d) => d.uses),
        columns: cols.filter((c) => c.schema === "mart" && c.name === m.name).map((c) => ({ name: c.col, type: c.type })),
      })),
      balance,
    };
  })
);

// ---- generic table preview (whitelisted by the catalog)
app.get(
  "/api/table/:schema/:name",
  cached(async (req) => {
    const { schema, name } = req.params;
    if (!["raw", "core", "mart"].includes(schema)) throw new Error("schema not allowed");
    const exists = await q(
      `SELECT array_agg(column_name::text ORDER BY ordinal_position) AS cols FROM information_schema.columns
       WHERE table_schema = $1 AND table_name = $2`,
      [schema, name]
    );
    const colsList = exists[0]?.cols;
    if (!colsList) throw new Error("unknown table");
    const params = [];
    let where = "";
    if (req.query.order_id && colsList.includes("order_id")) {
      params.push(String(req.query.order_id));
      where = `WHERE order_id = $1`;
    }
    const rows = await q(`SELECT * FROM ${schema}."${name}" ${where} LIMIT 25`, params);
    const visible = colsList.filter((c) => !c.startsWith("_"));
    return { schema, name, columns: visible, rows: rows.map((r) => Object.fromEntries(visible.map((c) => [c, r[c]]))) };
  })
);

// ---- view definition + result
app.get(
  "/api/view/:name",
  cached(async (req) => {
    const name = req.params.name;
    const ok = await q(
      `SELECT c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'mart' AND c.relname = $1`,
      [name]
    );
    if (!ok.length) throw new Error("unknown mart object");
    const sql = ok[0].relkind === "v" ? (await q(`SELECT pg_get_viewdef($1::regclass, true) AS d`, [`mart.${name}`]))[0].d : null;
    const rows = await q(`SELECT * FROM mart."${name}" LIMIT 30`);
    return { name, sql, rows };
  })
);

// ---- follow one order through every layer
app.get(
  "/api/trace/:orderId",
  cached(async (req) => {
    const id = req.params.orderId;
    if (!/^[0-9a-f]{32}$/.test(id)) throw new Error("bad order id");
    const one = (sql) => q(sql, [id]);
    const [rawOrder, rawItems, rawPays, rawRevs, rawCust, fOrder, fItems, fPays, fRevs, vOrder, vDelivery] = await Promise.all([
      one(`SELECT order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date FROM raw.orders WHERE order_id = $1`),
      one(`SELECT order_item_id, product_id, seller_id, price, freight_value, shipping_limit_date FROM raw.order_items WHERE order_id = $1 ORDER BY order_item_id::int`),
      one(`SELECT payment_sequential, payment_type, payment_installments, payment_value FROM raw.order_payments WHERE order_id = $1`),
      one(`SELECT review_id, review_score, review_creation_date FROM raw.order_reviews WHERE order_id = $1`),
      one(`SELECT c.customer_id, c.customer_unique_id, c.customer_city, c.customer_state FROM raw.customers c JOIN raw.orders o USING (customer_id) WHERE o.order_id = $1`),
      one(`SELECT * FROM core.fact_order WHERE order_id = $1`),
      one(`SELECT * FROM core.fact_order_item WHERE order_id = $1 ORDER BY order_item_id`),
      one(`SELECT * FROM core.fact_payment WHERE order_id = $1`),
      one(`SELECT review_id, order_id, review_score, review_creation_date FROM core.fact_review WHERE order_id = $1`),
      one(`SELECT order_id, order_status, is_revenue, units_count, sellers_count, item_revenue, freight_amount, order_gmv, payment_amount, payment_coverage, review_avg_pair_score FROM mart.v_orders WHERE order_id = $1`),
      one(`SELECT is_late_calendar_day, purchase_to_delivery_days, purchase_to_carrier_days, carrier_to_delivery_days, is_handover_after_max_item_deadline FROM mart.v_order_delivery_variants WHERE order_id = $1`),
    ]);
    if (!rawOrder.length) throw new Error("order not found");
    return {
      raw: { orders: rawOrder, customers: rawCust, order_items: rawItems, order_payments: rawPays, order_reviews: rawRevs },
      core: { fact_order: fOrder, fact_order_item: fItems, fact_payment: fPays, fact_review: fRevs },
      mart: { v_orders: vOrder, v_order_delivery_variants: vDelivery },
    };
  })
);

// ---- checks and data quality
app.get(
  "/api/checks",
  cached(async () => {
    const [summary, failed, issues, examples] = await Promise.all([
      q(`SELECT check_group AS grp, severity, count(*) AS total, count(*) FILTER (WHERE ok) AS passed
         FROM core.check_results GROUP BY 1, 2 ORDER BY 1`),
      q(`SELECT check_name, check_group, severity, expected, actual FROM core.check_results WHERE NOT ok ORDER BY 1`),
      q(`SELECT issue_code, entity_type, count(*) AS n FROM core.data_issues GROUP BY 1, 2 ORDER BY 3 DESC`),
      q(`SELECT DISTINCT ON (issue_code) issue_code, entity_key, details FROM core.data_issues ORDER BY issue_code`),
    ]);
    const balance = await q(`SELECT check_name, expected, actual, ok FROM core.check_results
                             WHERE check_group IN ('balance', 'money') ORDER BY check_group, check_name LIMIT 30`);
    return { summary, failed, issues: issues.map((i) => ({ ...i, example: examples.find((e) => e.issue_code === i.issue_code) })), balance };
  })
);

// ---- metric passports
app.get(
  "/api/metrics",
  cached(async () => q(`SELECT * FROM mart.metric_definitions ORDER BY name`))
);

// ---- answers Q1-Q5 straight from mart views, with the task's control numbers
app.get(
  "/api/answers",
  cached(async () => {
    const [q1, q2, q3, q4, q4w, q5] = await Promise.all([
      q(`SELECT to_char(month_start, 'YYYY-MM') AS month, orders_placed, orders_delivered, item_revenue FROM mart.q01_revenue_monthly ORDER BY month_start`),
      q(`SELECT revenue_rank, seller_id, seller_city, seller_state, orders_delivered, units_delivered, orders_all_statuses, item_revenue FROM mart.q02_sellers_top10 ORDER BY revenue_rank`),
      q(`SELECT n_delivered_orders, avg_order_gmv_rounded, avg_payment_amount_rounded, avg_source_rows, avg_units, avg_distinct_product_seller_lines FROM mart.q03_average_order`),
      q(`SELECT observation_window, buyers, repeat_buyers, repeat_buyer_pct_rounded FROM mart.q04_buyers_repeat`),
      q(`SELECT observation_window, buyers, repeat_buyers, repeat_buyer_pct_rounded FROM mart.q04_buyers_repeat_q1_window`),
      q(`SELECT category_key, coalesce(name_en, name_pt, 'unknown') AS name, item_revenue, revenue_pct_rounded FROM mart.q05_category_revenue ORDER BY item_revenue DESC`),
    ]);
    const q1Total = q1.reduce((s, r) => s + (r.item_revenue || 0), 0);
    const q5Total = q5.reduce((s, r) => s + (r.item_revenue || 0), 0);
    return {
      q1: { rows: q1, total: q1Total, control: { rows: 24, total: 13221498.11 } },
      q2: { rows: q2, control: { top1: 226987.93 } },
      q3: { row: q3[0], control: { avg_check: 159.88 } },
      q4: { row: q4[0], window: q4w[0], control: { buyers: 96096, pct: 3.12 } },
      q5: { rows: q5, total: q5Total, control: { categories: 74, top: 1233131.72, total: 13221498.11 } },
    };
  })
);

// ---- block B answers (Q6–Q10). The views come from model/55_answers_block_b.sql;
// until that step is in the build, report them as not available instead of failing.
app.get(
  "/api/answers-b",
  cached(async () => {
    const [{ ok }] = await q(`SELECT to_regclass('mart.q06_price_history') IS NOT NULL AS ok`);
    if (!ok) return { available: false };
    const [q6, q7, q8, q9s, q9m, q10, q10c] = await Promise.all([
      q(`SELECT population, product_id, distinct_prices, purchase_date::text AS purchase_date, price, units_sold
         FROM mart.q06_price_history ORDER BY population, product_id, purchase_date, price`),
      q(`SELECT population, customer_state, late_basis, orders_count, avg_delivery_days, late_pct, late_denominator, late_orders
         FROM mart.q07_delivery_by_state ORDER BY orders_count DESC`),
      q(`SELECT order_status, orders_count, orders_pct, orders_without_items FROM mart.q08_status_snapshot ORDER BY orders_count DESC`),
      q(`SELECT customer_state, payment_count, payment_amount, avg_installments_all_types, avg_installments_credit_card
         FROM mart.q09_payments_2018_by_state ORDER BY payment_amount DESC NULLS LAST`),
      q(`SELECT period, payment_type, payment_count, avg_installments FROM mart.q09_payment_methods ORDER BY period, payment_count DESC`),
      q(`SELECT population, score_policy, late_basis, review_score, orders_count, avg_delivery_days, late_pct
         FROM mart.q10_review_delivery ORDER BY review_score`),
      q(`SELECT population, orders_count, orders_without_score, orders_with_multiple_scores FROM mart.q10_review_coverage`),
    ]);
    return { available: true, q6, q7, q8, q9: { states: q9s, methods: q9m }, q10: { rows: q10, coverage: q10c } };
  })
);

const PORT = Number(process.env.PORT || 8787);
app.listen(PORT, "127.0.0.1", () => console.log(`Capibara API on http://127.0.0.1:${PORT}`));
