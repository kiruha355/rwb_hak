import Page from "../Page";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Col, DataTable, ErrorBox, KpiStrip, Loading, Panel, Seg, money, nf, pct, useApi, useFilters, useViewParam } from "../lib";
import { axis, tip, C } from "../charts";

type Cat = { key: string; name: string; is_unknown: boolean; revenue: number; units: number; orders: number; sellers: number };
type Seller = { seller_id: string; seller_city: string; seller_state: string; revenue: number; orders: number; units: number };
type Pay = { type: string; payments: number; amount: number; avg_installments: number };
type Commerce = { total: number; categories: Cat[]; sellers: Seller[]; payments: Pay[] };

const PAY: Record<string, string> = { credit_card: "Кредитная карта", boleto: "Boleto (квитанция)", voucher: "Ваучер", debit_card: "Дебетовая карта", not_defined: "Не указан" };
const PAY_COLORS = [C.ink, C.accent, C.sand, C.silver, C.accentSoft];

export default function Commerce() {
  const { qs, f, set } = useFilters();
  const [view, setView] = useViewParam<"chart" | "table">("cats", "chart");
  const [topN, setTopN] = useViewParam<"10" | "25" | "50" | "100">("sellers", "10");
  const { data, error, loading } = useApi<Commerce>(`/api/commerce?${qs}${topN !== "10" ? "&limit=" + topN : ""}`);
  const cats = data?.categories || [];
  const units = cats.reduce((s, c) => s + c.units, 0);
  const unknown = cats.find((c) => c.is_unknown);
  const payTotal = data?.payments.reduce((s, p) => s + p.amount, 0) || 0;
  const payCount = data?.payments.reduce((s, p) => s + p.payments, 0) || 0;
  const pickCat = (c: Cat) => set({ category: f.category === c.key ? "" : c.key });

  const catCols: Col<Cat>[] = [
    { key: "name", label: "Категория", fmt: (c) => (c.is_unknown ? <span className="dim">без категории</span> : c.name) },
    { key: "revenue", label: "Выручка", num: true, bar: true, fmt: (c) => nf(c.revenue, 2) },
    { key: "share", label: "Доля", num: true, value: (c) => c.revenue / (data?.total || 1), fmt: (c) => pct(c.revenue / (data?.total || 1)) },
    { key: "orders", label: "Заказы", num: true, fmt: (c) => nf(c.orders) },
    { key: "units", label: "Продано единиц", num: true, fmt: (c) => nf(c.units) },
    { key: "avg", label: "Средняя цена", num: true, value: (c) => c.revenue / c.units, fmt: (c) => nf(c.revenue / c.units, 2) },
    { key: "sellers", label: "Продавцов", num: true, fmt: (c) => nf(c.sellers) },
  ];
  const sellerCols: Col<Seller & { rank: number }>[] = [
    { key: "rank", label: "#", num: true },
    { key: "seller_id", label: "Продавец", fmt: (s) => <span className="mono" title={s.seller_id}>{s.seller_id.slice(0, 12)}…</span> },
    { key: "seller_city", label: "Город" },
    { key: "seller_state", label: "Штат" },
    { key: "orders", label: "Заказы", num: true, fmt: (s) => nf(s.orders) },
    { key: "units", label: "Единиц", num: true, fmt: (s) => nf(s.units) },
    { key: "revenue", label: "Выручка", num: true, bar: true, fmt: (s) => nf(s.revenue, 2) },
    { key: "share", label: "Доля", num: true, value: (s) => s.revenue / (data?.total || 1), fmt: (s) => pct(s.revenue / (data?.total || 1), 2) },
  ];
  const payCols: Col<Pay>[] = [
    { key: "type", label: "Способ", fmt: (p) => PAY[p.type] || p.type },
    { key: "payments", label: "Платежей", num: true, fmt: (p) => nf(p.payments) },
    { key: "amount", label: "Сумма", num: true, bar: true, fmt: (p) => nf(p.amount, 2) },
    { key: "share", label: "Доля суммы", num: true, value: (p) => p.amount / payTotal, fmt: (p) => pct(p.amount / payTotal) },
    { key: "avg_installments", label: "Частей рассрочки, в ср.", num: true, fmt: (p) => nf(p.avg_installments, 1) },
  ];
  const sellers = (data?.sellers || []).map((s, i) => ({ ...s, rank: i + 1 }));

  return (
    <Page title="Продажи" lead="Из чего складывается выручка: какие категории и продавцы её дают и как покупатели платят.">
      {error && <ErrorBox error={error} />}
      {loading && !data && <Loading />}
      {data && (
        <>
          <KpiStrip
            items={[
              { label: "Выручка", value: money(data.total), sub: "сумма по категориям = итог", help: "sum(price) по доставленным заказам. Сумма по всем категориям, включая «без категории», совпадает с общей выручкой." },
              { label: "Продано единиц", value: nf(units), sub: "одна строка заказа = одна единица", help: "Число позиций в доставленных заказах. Складывается." },
              { label: "Средняя цена единицы", value: nf(data.total / (units || 1), 2), sub: "выручка ÷ единицы", help: "Не складывается: пересчитывается в каждом срезе." },
              { label: "Категорий с продажами", value: nf(cats.filter((c) => !c.is_unknown).length), sub: unknown ? `плюс «без категории»: ${money(unknown.revenue)}` : "все товары с категорией" },
              { label: "Платежи", value: nf(payCount), sub: `на ${money(payTotal)} по всем заказам периода`, help: "Платежи по всем заказам периода, любой статус: деньги приходят и по заказам, которые потом отменили. Поэтому сумма не равна выручке." },
            ]}
          />

          <Panel
            className="mt"
            title="Категории"
            hint="Нажмите на категорию, чтобы отфильтровать по ней весь дашборд"
            controls={<Seg value={view} onChange={setView} options={[{ id: "chart", label: "График" }, { id: "table", label: "Таблица" }]} />}
            csv={{ name: "kategorii", columns: catCols.filter((c) => !["share", "avg"].includes(c.key)).map((c) => ({ key: c.key, label: c.label })), rows: cats }}
            flush={view === "table"}
          >
            {view === "chart" ? (
              <ResponsiveContainer width="100%" height={15 * 26 + 20}>
                <BarChart data={cats.slice(0, 15)} layout="vertical" margin={{ left: 0, right: 24 }}>
                  <CartesianGrid stroke={C.grid} horizontal={false} />
                  <XAxis type="number" {...axis} tickFormatter={(v) => money(v)} />
                  <YAxis type="category" dataKey="name" width={200} {...axis} fontSize={12} tickFormatter={(v) => (v === "unknown" ? "без категории" : v)} />
                  <Tooltip {...tip} formatter={(v: number) => [`${nf(v, 2)} · ${pct(v / data.total)}`, "выручка"]} />
                  <Bar dataKey="revenue" barSize={16} radius={[0, 2, 2, 0]} cursor="pointer" onClick={(d: any) => pickCat(d)}>
                    {cats.slice(0, 15).map((c) => <Cell key={c.key} fill={c.key === f.category ? C.accent : c.is_unknown ? C.silver : C.ink} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <DataTable cols={catCols} rows={cats} initialSort={{ key: "revenue", desc: true }} onRow={pickCat} active={(c) => c.key === f.category} limit={20}
                total={{ name: "Итого", revenue: nf(data.total, 2), share: "100 %", units: nf(units) }} />
            )}
          </Panel>

          <div className="grid g2 mt">
            <Panel
              title="Лучшие продавцы"
              hint="Выручка продавца — только его товары в заказе, не весь заказ"
              controls={<Seg value={topN} onChange={setTopN} options={[{ id: "10", label: "Топ 10" }, { id: "25", label: "25" }, { id: "50", label: "50" }, { id: "100", label: "100" }]} />}
              csv={{ name: "prodavcy_top" + topN, columns: sellerCols.filter((c) => c.key !== "share").map((c) => ({ key: c.key, label: c.label })), rows: sellers }}
              flush
            >
              <DataTable cols={sellerCols} rows={sellers} maxHeight={420} />
            </Panel>
            <Panel title="Способы оплаты" hint="По всем заказам периода" csv={{ name: "oplata", columns: payCols.filter((c) => c.key !== "share").map((c) => ({ key: c.key, label: c.label })), rows: data.payments }}>
              <div className="stack" style={{ height: 14, marginBottom: 10 }}>
                {data.payments.map((p, i) => <div key={p.type} title={`${PAY[p.type] || p.type}: ${pct(p.amount / payTotal)}`} style={{ width: (p.amount / payTotal) * 100 + "%", background: PAY_COLORS[i % PAY_COLORS.length] }} />)}
              </div>
              <div className="legend" style={{ marginBottom: 12 }}>
                {data.payments.map((p, i) => <span key={p.type}><i style={{ background: PAY_COLORS[i % PAY_COLORS.length] }} />{PAY[p.type] || p.type}</span>)}
              </div>
              <div style={{ margin: "0 -16px -14px", borderTop: "1px solid var(--line)" }}>
                <DataTable cols={payCols} rows={data.payments} maxHeight={300} />
              </div>
            </Panel>
          </div>
        </>
      )}
    </Page>
  );
}
