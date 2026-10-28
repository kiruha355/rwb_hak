import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Col, DataTable, ErrorBox, Loading, Panel, Seg, nf, useApi, useViewParam } from "../lib";
import { axis, tip, C } from "../charts";

type Pop = "delivered" | "all_statuses";
type Basis = "calendar_day" | "timestamp";
type Policy = "within_score" | "single_score_only";
type Q6 = { population: Pop; product_id: string; distinct_prices: number; purchase_date: string; price: number; units_sold: number };
type Q7 = { population: Pop; customer_state: string; late_basis: Basis; orders_count: number; avg_delivery_days: number; late_pct: number; late_denominator: number; late_orders: number };
type Q8 = { order_status: string; orders_count: number; orders_pct: number; orders_without_items: number };
type Q9s = { customer_state: string; payment_count: number; payment_amount: number; avg_installments_all_types: number; avg_installments_credit_card: number | null };
type Q9m = { period: "all_snapshot" | "purchase_2018"; payment_type: string; payment_count: number; avg_installments: number };
type Q10 = { population: Pop; score_policy: Policy; late_basis: Basis; review_score: number; orders_count: number; avg_delivery_days: number; late_pct: number };
type Data = {
  available: boolean;
  q6: Q6[]; q7: Q7[]; q8: Q8[];
  q9: { states: Q9s[]; methods: Q9m[] };
  q10: { rows: Q10[]; coverage: { population: Pop; orders_count: number; orders_without_score: number; orders_with_multiple_scores: number }[] };
};

const POP = [{ id: "delivered" as Pop, label: "Доставленные" }, { id: "all_statuses" as Pop, label: "Все статусы" }];
const BASIS = [{ id: "calendar_day" as Basis, label: "Опоздание по дню" }, { id: "timestamp" as Basis, label: "По времени" }];
const POLICY = [{ id: "within_score" as Policy, label: "Каждая оценка заказа" }, { id: "single_score_only" as Policy, label: "Только однозначные" }];
const PAY: Record<string, string> = { credit_card: "Кредитная карта", boleto: "Boleto", voucher: "Ваучер", debit_card: "Дебетовая карта", not_defined: "Не указан" };
const STATUS: Record<string, string> = {
  delivered: "доставлен", shipped: "в пути", canceled: "отменён", unavailable: "недоступен",
  invoiced: "счёт выставлен", processing: "в обработке", created: "создан", approved: "оплата подтверждена",
};
const MIN_ORDERS = 500;
const csvCols = <T,>(cols: Col<T>[]) => cols.map((c) => ({ key: c.key, label: c.label }));

export default function AnswersB() {
  const { data, error } = useApi<Data>("/api/answers-b");
  const [p6, setP6] = useViewParam<Pop>("q6", "delivered");
  const [p7, setP7] = useViewParam<Pop>("q7", "delivered");
  const [b7, setB7] = useViewParam<Basis>("q7b", "calendar_day");
  const [per9, setPer9] = useViewParam<"purchase_2018" | "all_snapshot">("q9", "all_snapshot");
  const [p10, setP10] = useViewParam<Pop>("q10", "delivered");
  const [pol10, setPol10] = useViewParam<Policy>("q10p", "within_score");
  const [b10, setB10] = useViewParam<Basis>("q10b", "calendar_day");

  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading />;
  if (!data.available)
    return <div className="card">Витрин q06–q10 в базе нет: шаг <span className="mono">model/55_answers_block_b.sql</span> ещё не вошёл в сборку. Соберите модель из ветки с блоком Б.</div>;

  const q6 = data.q6.filter((r) => r.population === p6);
  const q7 = data.q7.filter((r) => r.population === p7 && r.late_basis === b7 && r.orders_count >= MIN_ORDERS);
  const q7Below = new Set(data.q7.filter((r) => r.population === p7 && r.orders_count < MIN_ORDERS).map((r) => r.customer_state)).size;
  const q9m = data.q9.methods.filter((r) => r.period === per9);
  const q10 = data.q10.rows.filter((r) => r.population === p10 && r.score_policy === pol10 && r.late_basis === b10);
  const cov = data.q10.coverage.find((c) => c.population === p10);
  const q8Total = data.q8.reduce((s, r) => s + r.orders_count, 0);

  const c6: Col<Q6>[] = [
    { key: "purchase_date", label: "Дата", fmt: (r) => new Date(r.purchase_date).toLocaleDateString("ru-RU") },
    { key: "price", label: "Цена", num: true, fmt: (r) => nf(r.price, 2) },
    { key: "units_sold", label: "Продано единиц", num: true, bar: true, fmt: (r) => nf(r.units_sold) },
  ];
  const c7: Col<Q7>[] = [
    { key: "customer_state", label: "Штат" },
    { key: "orders_count", label: "Заказов", num: true, fmt: (r) => nf(r.orders_count) },
    { key: "avg_delivery_days", label: "Ср. дней доставки", num: true, fmt: (r) => nf(r.avg_delivery_days, 2) },
    { key: "late_pct", label: "Доля опозданий", num: true, bar: true, fmt: (r) => nf(r.late_pct, 2) + " %" },
  ];
  const c8: Col<Q8>[] = [
    { key: "order_status", label: "Статус", fmt: (r) => <>{r.order_status} <span className="dim">· {STATUS[r.order_status] || ""}</span></> },
    { key: "orders_count", label: "Заказов", num: true, fmt: (r) => nf(r.orders_count) },
    { key: "orders_pct", label: "Доля", num: true, bar: true, fmt: (r) => nf(r.orders_pct, 2) + " %" },
    { key: "orders_without_items", label: "Из них без товаров", num: true, fmt: (r) => (r.orders_without_items ? <b>{nf(r.orders_without_items)}</b> : "0") },
  ];
  const c9s: Col<Q9s>[] = [
    { key: "customer_state", label: "Штат" },
    { key: "payment_count", label: "Платежей", num: true, fmt: (r) => nf(r.payment_count) },
    { key: "payment_amount", label: "Сумма", num: true, bar: true, fmt: (r) => nf(r.payment_amount, 2) },
    { key: "avg_installments_all_types", label: "Ср. рассрочка, все способы", num: true, fmt: (r) => nf(r.avg_installments_all_types, 2) },
    { key: "avg_installments_credit_card", label: "Ср. рассрочка, карта", num: true, fmt: (r) => nf(r.avg_installments_credit_card, 2) },
  ];
  const c9m: Col<Q9m>[] = [
    { key: "payment_type", label: "Способ", fmt: (r) => PAY[r.payment_type] || r.payment_type },
    { key: "payment_count", label: "Платежей", num: true, bar: true, fmt: (r) => nf(r.payment_count) },
    { key: "avg_installments", label: "Ср. рассрочка", num: true, fmt: (r) => nf(r.avg_installments, 2) },
  ];
  const c10: Col<Q10>[] = [
    { key: "review_score", label: "Оценка", fmt: (r) => "★".repeat(r.review_score) },
    { key: "orders_count", label: "Заказов", num: true, fmt: (r) => nf(r.orders_count) },
    { key: "avg_delivery_days", label: "Ср. дней доставки", num: true, bar: true, fmt: (r) => nf(r.avg_delivery_days, 2) },
    { key: "late_pct", label: "Доля опозданий", num: true, fmt: (r) => nf(r.late_pct, 2) + " %" },
  ];

  return (
    <>
      <div className="note" style={{ marginTop: 0, marginBottom: 12 }}>
        Витрины выдают все варианты расчёта; переключатели выбирают, какой показать. По умолчанию стоит рекомендованный вариант, командой он ещё не утверждён.
      </div>

      <Panel title="6 · Как менялась цена одного товара"
        hint={q6[0] ? `Товар ${q6[0].product_id} — ${nf(q6[0].distinct_prices)} разных цен; дата — день покупки` : "Цена каждой проданной единицы по дате заказа"}
        controls={<Seg value={p6} onChange={setP6} options={POP} />}
        csv={{ name: "q06_istoriya_ceny", columns: csvCols(c6), rows: q6 }}>
        <div className="grid g2">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={q6} margin={{ top: 8, right: 8, left: 0 }}>
              <CartesianGrid stroke={C.grid} vertical={false} />
              <XAxis dataKey="purchase_date" {...axis} tickFormatter={(v) => new Date(v).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" })} minTickGap={24} />
              <YAxis {...axis} width={44} domain={["auto", "auto"]} />
              <Tooltip {...tip} labelFormatter={(v) => new Date(v).toLocaleDateString("ru-RU")} formatter={(v: number, n: string) => [nf(v, 2), n === "price" ? "цена" : n]} />
              <Line type="stepAfter" dataKey="price" stroke={C.accent} strokeWidth={2} dot={{ r: 2 }} />
            </LineChart>
          </ResponsiveContainer>
          <div style={{ border: "1px solid var(--line)", borderRadius: 6 }}>
            <DataTable cols={c6} rows={q6} maxHeight={258} />
          </div>
        </div>
      </Panel>

      <div className="grid g2 mt">
        <Panel title="7 · Доставка по штатам покупателя"
          hint={`Только штаты от ${MIN_ORDERS} заказов: ${q7.length} штатов, ещё ${q7Below} не прошли порог`}
          controls={<><Seg value={p7} onChange={setP7} options={POP} /><Seg value={b7} onChange={setB7} options={BASIS} /></>}
          csv={{ name: "q07_dostavka_po_shtatam", columns: csvCols(c7), rows: q7 }} flush>
          <DataTable cols={c7} rows={q7} initialSort={{ key: "orders_count", desc: true }} maxHeight={420} />
        </Panel>
        <Panel title="8 · Воронка статусов" hint="Все заказы снимка; «без товаров» — у заказа нет ни одной позиции"
          csv={{ name: "q08_voronka_statusov", columns: csvCols(c8), rows: data.q8 }} flush
          footer={`Всего ${nf(q8Total)} заказов, без товаров ${nf(data.q8.reduce((s, r) => s + r.orders_without_items, 0))}`}>
          <DataTable cols={c8} rows={data.q8} />
        </Panel>
      </div>

      <div className="grid g-3-2 mt">
        <Panel title="9 · Оплата по штатам, заказы 2018 года" hint="Год — по дате покупки заказа: даты самого платежа в данных нет. Все статусы."
          csv={{ name: "q09_oplata_shtaty_2018", columns: csvCols(c9s), rows: data.q9.states }} flush>
          <DataTable cols={c9s} rows={data.q9.states} initialSort={{ key: "payment_amount", desc: true }} maxHeight={380} />
        </Panel>
        <Panel title="9 · Способы оплаты целиком" hint="У boleto, ваучера и дебетовой карты рассрочки почти не бывает"
          controls={<Seg value={per9} onChange={setPer9} options={[{ id: "all_snapshot", label: "Весь период" }, { id: "purchase_2018", label: "2018" }]} />}
          csv={{ name: "q09_sposoby_oplaty", columns: csvCols(c9m), rows: q9m }} flush>
          <DataTable cols={c9m} rows={q9m} />
        </Panel>
      </div>

      <Panel className="mt" title="10 · Оценка покупателя и срок доставки"
        hint={cov ? `${nf(cov.orders_with_multiple_scores)} заказов имеют разные оценки в нескольких отзывах; без оценки — ${nf(cov.orders_without_score)}` : undefined}
        controls={<><Seg value={p10} onChange={setP10} options={POP} /><Seg value={pol10} onChange={setPol10} options={POLICY} /><Seg value={b10} onChange={setB10} options={BASIS} /></>}
        csv={{ name: "q10_ocenka_i_dostavka", columns: csvCols(c10), rows: q10 }} flush
        footer={pol10 === "within_score" ? "Заказ с оценками 2 и 5 входит в обе группы, поэтому заказы по оценкам нельзя складывать." : "Заказы с разными оценками исключены; группы не пересекаются."}>
        <DataTable cols={c10} rows={q10} />
      </Panel>
    </>
  );
}
