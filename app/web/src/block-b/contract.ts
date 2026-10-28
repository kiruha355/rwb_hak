// Read-only boundary for /api/answers-block-b. No metric is recomputed here.
export const POPULATIONS = ["all_statuses", "delivered"] as const;
export const BASES = ["calendar_day", "timestamp"] as const;
export const POLICIES = ["within_score", "single_score_only"] as const;
export const PERIODS = ["all_snapshot", "purchase_2018"] as const;
export type Population = typeof POPULATIONS[number];
export type LateBasis = typeof BASES[number];
export type ScorePolicy = typeof POLICIES[number];
export type Period = typeof PERIODS[number];

export type PriceRow = {
  population: Population; product_id: string; distinct_prices: number;
  units_with_unknown_price: number; purchase_date: string | null;
  price: number | null; units_sold: number;
};
export type DeliveryMetrics = {
  population: Population; late_basis: LateBasis; orders_count: number;
  duration_denominator: number; avg_delivery_days: number | null;
  late_denominator: number; late_orders: number; late_pct: number | null;
};
export type StateRow = DeliveryMetrics & { customer_state: string | null };
export type StatusRow = {
  order_status: string | null; orders_count: number; orders_pct: number | null;
  orders_without_items: number;
};
export type PaymentStateRow = {
  customer_state: string | null; payment_count: number; amount_denominator: number;
  payment_amount: number | null; known_payment_amount_sum: number | null;
  installments_denominator: number; avg_installments_all_types: number | null;
  credit_installments_denominator: number; avg_installments_credit_card: number | null;
};
export type MethodRow = {
  period: Period; payment_type: string | null; payment_count: number;
  installments_denominator: number; avg_installments: number | null;
};
export type ReviewRow = DeliveryMetrics & { score_policy: ScorePolicy; review_score: number };
export type CoverageRow = {
  population: Population; orders_count: number; orders_without_score: number;
  orders_with_multiple_scores: number; orders_in_multiple_valid_score_groups: number;
  orders_with_out_of_range_score: number;
};
export type BlockBData = {
  q6: { rows: PriceRow[] }; q7: { rows: StateRow[] }; q8: { rows: StatusRow[] };
  q9: { states: PaymentStateRow[]; methods: MethodRow[] };
  q10: { rows: ReviewRow[]; coverage: CoverageRow[] };
  meta: { scope: unknown; [key: string]: unknown };
};

type RecordValue = Record<string, unknown>;
type Parser<T> = (value: unknown, path: string) => T;
const fail = (path: string): never => { throw new Error(`Некорректный ответ блока Б: ${path}`); };
const record: Parser<RecordValue> = (v, p) =>
  v !== null && typeof v === "object" && !Array.isArray(v) ? v as RecordValue : fail(p);
const text: Parser<string> = (v, p) => typeof v === "string" && v.length > 0 ? v : fail(p);
const numeric: Parser<number> = (v, p) => {
  // PostgreSQL numeric/bigint may travel as strings. Empty strings are not zero.
  if (typeof v !== "number" && (typeof v !== "string" || !/^-?\d+(\.\d+)?$/.test(v))) return fail(p);
  const n = Number(v);
  return Number.isFinite(n) ? n : fail(p);
};
const count: Parser<number> = (v, p) => {
  const n = numeric(v, p);
  return Number.isSafeInteger(n) && n >= 0 ? n : fail(p);
};
const nullable = <T,>(parse: Parser<T>): Parser<T | null> => (v, p) => v === null ? null : parse(v, p);
const enumeration = <T extends string,>(values: readonly T[]): Parser<T> =>
  (v, p) => values.includes(v as T) ? v as T : fail(p);
const population = enumeration(POPULATIONS), basis = enumeration(BASES);

function fields<T>(v: unknown, p: string, schema: { [K in keyof T]: Parser<T[K]> }): T {
  const row = record(v, p), result = {} as T;
  for (const key in schema) result[key] = schema[key](row[key], `${p}.${key}`);
  return result;
}
function rows<T>(v: unknown, p: string, parse: Parser<T>, key: (r: T) => unknown[]): T[] {
  if (!Array.isArray(v)) return fail(p);
  const result = v.map((row, i) => parse(row, `${p}[${i}]`)), keys = new Set<string>();
  for (const row of result) {
    const id = JSON.stringify(key(row));
    if (keys.has(id)) return fail(`${p}: повтор ключа ${id}`);
    keys.add(id);
  }
  return result;
}
const delivery = {
  population, late_basis: basis, orders_count: count, duration_denominator: count,
  avg_delivery_days: nullable(numeric), late_denominator: count,
  late_orders: count, late_pct: nullable(numeric),
};

export function adaptBlockB(value: unknown): BlockBData {
  const root = record(value, "response");
  const q6 = record(root.q6, "q6"), q7 = record(root.q7, "q7"), q8 = record(root.q8, "q8");
  const q9 = record(root.q9, "q9"), q10 = record(root.q10, "q10"), meta = record(root.meta, "meta");
  if (!("scope" in meta) || meta.scope === undefined || meta.scope === null) fail("meta.scope");
  const data: BlockBData = {
    q6: { rows: rows(q6.rows, "q6.rows", (v, p) => fields<PriceRow>(v, p, {
      population, product_id: text, distinct_prices: count, units_with_unknown_price: count,
      purchase_date: nullable((v, p) => {
        const s = text(v, p);
        const time = Date.parse(s);
        return /^\d{4}-\d{2}-\d{2}$/.test(s) && !Number.isNaN(time) && new Date(time).toISOString().slice(0, 10) === s ? s : fail(p);
      }), price: nullable(numeric), units_sold: count,
    }), r => [r.population, r.product_id, r.purchase_date, r.price]) },
    q7: { rows: rows(q7.rows, "q7.rows", (v, p) => fields<StateRow>(v, p, {
      ...delivery, customer_state: nullable(text),
    }), r => [r.population, r.customer_state, r.late_basis]) },
    q8: { rows: rows(q8.rows, "q8.rows", (v, p) => fields<StatusRow>(v, p, {
      order_status: nullable(text), orders_count: count, orders_pct: nullable(numeric), orders_without_items: count,
    }), r => [r.order_status]) },
    q9: {
      states: rows(q9.states, "q9.states", (v, p) => fields<PaymentStateRow>(v, p, {
        customer_state: nullable(text), payment_count: count, amount_denominator: count,
        payment_amount: nullable(numeric), known_payment_amount_sum: nullable(numeric),
        installments_denominator: count, avg_installments_all_types: nullable(numeric),
        credit_installments_denominator: count, avg_installments_credit_card: nullable(numeric),
      }), r => [r.customer_state]),
      methods: rows(q9.methods, "q9.methods", (v, p) => fields<MethodRow>(v, p, {
        period: enumeration(PERIODS), payment_type: nullable(text), payment_count: count,
        installments_denominator: count, avg_installments: nullable(numeric),
      }), r => [r.period, r.payment_type]),
    },
    q10: {
      rows: rows(q10.rows, "q10.rows", (v, p) => fields<ReviewRow>(v, p, {
        ...delivery, score_policy: enumeration(POLICIES), review_score: (v, p) => {
          const n = count(v, p);
          return n >= 1 && n <= 5 ? n : fail(p);
        },
      }), r => [r.population, r.score_policy, r.late_basis, r.review_score]),
      coverage: rows(q10.coverage, "q10.coverage", (v, p) => fields<CoverageRow>(v, p, {
        population, orders_count: count, orders_without_score: count,
        orders_with_multiple_scores: count, orders_in_multiple_valid_score_groups: count,
        orders_with_out_of_range_score: count,
      }), r => [r.population]),
    },
    meta: { ...meta, scope: meta.scope },
  };
  // Keep a missing grid cell missing; the view promises five scores per variant.
  // A totally empty response remains a valid empty response.
  if (data.q10.rows.length > 0 && data.q10.rows.length !== 40) fail("q10.rows: нужны пять оценок в каждом из восьми вариантов");
  if (data.q10.rows.length > 0 && data.q10.coverage.length !== 2) fail("q10.coverage: нужен охват обеих совокупностей");
  // Repeated product totals are metadata, not additive history measures.
  const products = new Map<string, PriceRow>();
  for (const row of data.q6.rows) {
    const id = JSON.stringify([row.population, row.product_id]), first = products.get(id);
    if (first && (row.distinct_prices !== first.distinct_prices || row.units_with_unknown_price !== first.units_with_unknown_price)) fail("q6.rows: противоречивые итоги товара");
    products.set(id, row);
  }
  return data;
}

export const populationLabel: Record<Population, string> = { all_statuses: "Все статусы", delivered: "Только доставленные" };
export const basisLabel: Record<LateBasis, string> = { calendar_day: "По дате", timestamp: "По времени" };
export const policyLabel: Record<ScorePolicy, string> = { within_score: "Каждая оценка заказа", single_score_only: "Только одна оценка" };
export const periodLabel: Record<Period, string> = { all_snapshot: "Весь снимок", purchase_2018: "Покупки 2018 года" };
export const number = (v: number | null, digits = 0): string => v === null ? "Нет данных" : v.toLocaleString("ru-RU", { minimumFractionDigits: digits, maximumFractionDigits: digits });
export const percent = (v: number | null): string => v === null ? "Нет данных" : `${number(v, 2)} %`;
export const stateLabel = (v: string | null): string => v === null ? "Штат неизвестен" : v;

// Export dimensions and denominators together; never sum across named variants.
export function csvRows<T extends object>(rows: T[]): string {
  if (rows.length === 0) return "";
  const keys = Object.keys(rows[0]) as (keyof T)[];
  const cell = (v: unknown) => v === null || v === undefined ? "" : `"${String(v).replace(/"/g, '""')}"`;
  return "\uFEFF" + [keys.map(cell).join(";"), ...rows.map(row => keys.map(key => cell(row[key])).join(";"))].join("\r\n");
}
