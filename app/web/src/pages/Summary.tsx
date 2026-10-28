import Page from "../Page";
import { Link } from "react-router-dom";
import { Bar, CartesianGrid, ComposedChart, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Col, DataTable, ErrorBox, Loading, Panel, Seg, KpiStrip, money, monthLabel, nf, pct, useApi, useFilters, useViewParam } from "../lib";
import { axis, tip, C } from "../charts";

type Month = {
  month: string; placed: number; delivered: number; buyers: number; avg_check: number | null;
  review_avg: number | null; revenue: number; late_share: number | null; late_n: number;
};
type Overview = {
  kpi: {
    orders_placed: number; orders_delivered: number; avg_check: number; buyers: number; repeat_buyers: number;
    review_avg: number; item_revenue: number; late_share: number; median_days: number; n: number;
  };
  series: Month[];
};
type Delivery = { states: { state: string; n: number; late_share: number }[] };
type Commerce = { total: number; categories: { key: string; name: string; is_unknown: boolean; revenue: number }[] };

type MetricId = "revenue" | "orders" | "avg_check" | "buyers" | "late" | "review";
const METRICS: { id: MetricId; label: string; key: keyof Month; fmt: (v: number | null) => string; axis: (v: number) => string; hint: string }[] = [
  { id: "revenue", label: "Выручка", key: "revenue", fmt: (v) => nf(v, 2), axis: (v) => money(v), hint: "сумма цен товаров в доставленных заказах, без доставки" },
  { id: "orders", label: "Заказы", key: "placed", fmt: (v) => nf(v), axis: (v) => nf(v), hint: "все оформленные заказы; тёмная часть — доставленные" },
  { id: "avg_check", label: "Средний чек", key: "avg_check", fmt: (v) => nf(v, 2), axis: (v) => nf(v), hint: "товары + доставка, по доставленным заказам" },
  { id: "buyers", label: "Покупатели", key: "buyers", fmt: (v) => nf(v), axis: (v) => nf(v), hint: "уникальные люди в месяце; по месяцам не суммируются" },
  { id: "late", label: "Опоздания", key: "late_share", fmt: (v) => pct(v), axis: (v) => nf(v * 100, 0) + "%", hint: "доля доставленных позже обещанной даты" },
  { id: "review", label: "Оценка", key: "review_avg", fmt: (v) => nf(v, 2), axis: (v) => nf(v, 1), hint: "средняя оценка отзывов, 1–5" },
];

const Spark = ({ data, k }: { data: Month[]; k: keyof Month }) => (
  <ResponsiveContainer width="100%" height={28}>
    <LineChart data={data} margin={{ top: 2, bottom: 2, left: 0, right: 0 }}>
      <Line type="monotone" dataKey={k as string} stroke={C.accent} strokeWidth={1.5} dot={false} isAnimationActive={false} connectNulls />
    </LineChart>
  </ResponsiveContainer>
);

export default function Summary() {
  const { qs } = useFilters();
  const ov = useApi<Overview>("/api/overview?" + qs);
  const dl = useApi<Delivery>("/api/delivery?" + qs);
  const cm = useApi<Commerce>("/api/commerce?" + qs);
  const [metricId, setMetric] = useViewParam<MetricId>("metric", "revenue");
  const [chart, setChart] = useViewParam<"bar" | "line">("chart", "bar");
  const metric = METRICS.find((m) => m.id === metricId) || METRICS[0];
  const k = ov.data?.kpi;
  const series = (ov.data?.series || []).map((s) => ({ ...s, label: monthLabel(s.month), other: s.placed - s.delivered, ontime: s.late_share === null ? null : 1 - s.late_share }));
  const withQs = (to: string, extra = "") => to + "?" + [qs, extra].filter(Boolean).join("&");

  // insights: computed from the same API answers, each links to the page that explains it
  const worst = [...(dl.data?.states || [])].filter((s) => s.n >= 300).sort((a, b) => b.late_share - a.late_share)[0];
  const peakLate = series.filter((s) => s.late_n >= 100 && s.late_share !== null).sort((a, b) => (b.late_share || 0) - (a.late_share || 0))[0];
  const bestMonth = [...series].sort((a, b) => b.revenue - a.revenue)[0];
  const unknown = cm.data?.categories.find((c) => c.is_unknown);
  const topCat = cm.data?.categories[0];

  const cols: Col<(typeof series)[number]>[] = [
    { key: "month", label: "Месяц", fmt: (r) => r.label },
    { key: "placed", label: "Заказы", num: true, fmt: (r) => nf(r.placed) },
    { key: "delivered", label: "Доставлено", num: true, fmt: (r) => nf(r.delivered) },
    { key: "revenue", label: "Выручка", num: true, bar: true, fmt: (r) => nf(r.revenue, 2) },
    { key: "avg_check", label: "Средний чек", num: true, fmt: (r) => nf(r.avg_check, 2) },
    { key: "buyers", label: "Покупатели", num: true, fmt: (r) => nf(r.buyers) },
    { key: "late_share", label: "Опоздания", num: true, fmt: (r) => pct(r.late_share) },
    { key: "review_avg", label: "Оценка", num: true, fmt: (r) => nf(r.review_avg, 2) },
  ];

  return (
    <Page title="Обзор" lead="Главные показатели за выбранный период и как они менялись по месяцам.">
      {ov.error && <ErrorBox error={ov.error} />}
      {ov.loading && !k && <Loading />}
      {k && (
        <>
          <KpiStrip
            items={[
              { label: "Выручка", value: money(k.item_revenue), sub: "товары в доставленных заказах", help: "sum(price) по позициям заказов со статусом delivered, без стоимости доставки. Складывается по срезам.", spark: <Spark data={series} k="revenue" /> },
              { label: "Заказы", value: nf(k.orders_placed), sub: `доставлено ${nf(k.orders_delivered)} · ${pct(k.orders_delivered / k.orders_placed)}`, help: "Все оформленные заказы, любой статус. Складывается по срезам.", spark: <Spark data={series} k="placed" /> },
              { label: "Средний чек", value: nf(k.avg_check, 2), sub: "товары + доставка", help: "Среднее по доставленным заказам от суммы price + freight. Не складывается: пересчитывается в каждом срезе.", spark: <Spark data={series} k="avg_check" /> },
              { label: "Покупатели", value: nf(k.buyers), sub: `повторно купили ${nf(k.repeat_buyers)} · ${pct(k.repeat_buyers / k.buyers, 2)}`, help: "Уникальные customer_unique_id по всем заказам периода. Не складывается по месяцам: один человек покупает в разные месяцы.", spark: <Spark data={series} k="buyers" /> },
              { label: "Доставлено вовремя", value: pct(1 - k.late_share), sub: `медиана ${nf(k.median_days, 1)} дн. от покупки`, help: "Доля доставленных заказов, вручённых не позже обещанной даты (сравнение по календарному дню). Не складывается.", spark: <Spark data={series as any} k={"ontime" as any} /> },
              { label: "Средняя оценка", value: nf(k.review_avg, 2), sub: "по отзывам, шкала 1–5", help: "Среднее по заказам с отзывом. Не складывается.", spark: <Spark data={series} k="review_avg" /> },
            ]}
          />

          <div className="grid g-3-2 mt">
            <Panel
              title={`${metric.label} по месяцам`}
              hint={metric.hint}
              controls={
                <>
                  <select className="btn sm" value={metric.id} onChange={(e) => setMetric(e.target.value as MetricId)}>
                    {METRICS.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
                  </select>
                  <Seg value={chart} onChange={setChart} options={[{ id: "bar", label: "Столбцы" }, { id: "line", label: "Линия" }]} />
                </>
              }
              csv={{ name: "po_mesyacam_" + metric.id, columns: [{ key: "month", label: "Месяц" }, { key: metric.key as string, label: metric.label }], rows: series }}
            >
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke={C.grid} vertical={false} />
                  <XAxis dataKey="label" {...axis} interval="preserveStartEnd" minTickGap={16} />
                  <YAxis {...axis} width={64} tickFormatter={metric.axis} domain={metric.id === "review" ? [1, 5] : [0, "auto"]} />
                  <Tooltip {...tip} formatter={(v: number, n: string) => [metric.id === "orders" ? nf(v) : metric.fmt(v), n === "delivered" ? "доставлено" : n === "other" ? "прочие статусы" : metric.label]} />
                  {chart === "bar" && metric.id === "orders" ? (
                    <>
                      <Bar dataKey="delivered" stackId="o" fill={C.ink} />
                      <Bar dataKey="other" stackId="o" fill={C.silver} radius={[2, 2, 0, 0]} />
                    </>
                  ) : chart === "bar" ? (
                    <Bar dataKey={metric.key as string} fill={C.ink} radius={[2, 2, 0, 0]} />
                  ) : (
                    <Line type="monotone" dataKey={metric.key as string} stroke={C.accent} strokeWidth={2} dot={{ r: 2 }} connectNulls={false} />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            </Panel>

            <Panel title="На что обратить внимание" hint="Считается автоматически по текущим фильтрам">
              <div className="insights">
                {bestMonth && bestMonth.revenue > 0 && (
                  <Insight label="Пик выручки" value={bestMonth.label} note={money(bestMonth.revenue)} to={withQs("/", "metric=revenue")} />
                )}
                {peakLate && (
                  <Insight label="Месяц с худшей доставкой" value={peakLate.label} note={`${pct(peakLate.late_share)} опозданий`} to={withQs("/", "metric=late&chart=line")} />
                )}
                {worst && (
                  <Insight label="Штат с худшей доставкой" value={worst.state} note={`${pct(worst.late_share)} опозданий, ${nf(worst.n)} заказов`} to={withQs("/delivery")} />
                )}
                {topCat && cm.data && (
                  <Insight label="Главная категория" value={topCat.name} note={`${pct(topCat.revenue / cm.data.total)} выручки`} to={withQs("/sales")} />
                )}
                {unknown && cm.data && (
                  <Insight label="Выручка без категории" value={money(unknown.revenue)} note={`${pct(unknown.revenue / cm.data.total)} — товары без категории в справочнике`} to={withQs("/sales")} />
                )}
              </div>
            </Panel>
          </div>

          <Panel
            className="mt"
            title="Помесячно"
            hint="Нажмите на заголовок столбца, чтобы отсортировать. Итог: суммы для заказов и выручки, пересчёт за период — для чека, покупателей, опозданий и оценки."
            csv={{ name: "pomesyachno", columns: cols.map((c) => ({ key: c.key, label: c.label })), rows: series }}
            flush
          >
            <DataTable
              cols={cols}
              rows={series}
              maxHeight={520}
              total={{
                month: "За период",
                placed: nf(k.orders_placed),
                delivered: nf(k.orders_delivered),
                revenue: nf(k.item_revenue, 2),
                avg_check: nf(k.avg_check, 2),
                buyers: nf(k.buyers),
                late_share: pct(k.late_share),
                review_avg: nf(k.review_avg, 2),
              }}
            />
          </Panel>
        </>
      )}
    </Page>
  );
}

function Insight({ label, value, note, to }: { label: string; value: string; note: string; to: string }) {
  return (
    <Link to={to} className="insight">
      <span className="il">{label}</span>
      <span className="iv">{value}</span>
      <span className="in">{note}</span>
      <span className="ia">→</span>
    </Link>
  );
}
