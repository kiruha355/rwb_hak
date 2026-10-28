import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Filters from "../Filters";
import { ErrorBox, Loading, PageHead, money, nf, pct, useApi, useFilters } from "../lib";
import { axis, tip, C } from "../charts";

type Commerce = {
  total: number;
  categories: { key: string; name: string; is_unknown: boolean; revenue: number; units: number }[];
  sellers: { seller_id: string; seller_city: string; seller_state: string; revenue: number; orders: number; units: number }[];
  payments: { type: string; payments: number; amount: number; avg_installments: number }[];
};

const PAY: Record<string, string> = { credit_card: "Карта", boleto: "Boleto", voucher: "Ваучер", debit_card: "Дебетовая", not_defined: "Не указан" };
const PAY_COLORS = [C.ink, C.ice, C.sand, C.silver, C.iceSoft];

export default function Commerce() {
  const { qs, f, set } = useFilters();
  const { data, error, loading } = useApi<Commerce>("/api/commerce?" + qs);
  const top = data?.categories.slice(0, 10) || [];
  const unknown = data?.categories.find((c) => c.is_unknown);
  const sumCats = data?.categories.reduce((s, c) => s + c.revenue, 0) || 0;
  const payTotal = data?.payments.reduce((s, p) => s + p.amount, 0) || 0;
  return (
    <>
      <PageHead eyebrow="" title="Продажи" />
      <Filters />
      {error && <ErrorBox error={error} />}
      {loading && !data && <Loading />}
      {data && (
        <>
          <div className="grid g3">
            <div className="card dark kpi">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <span className="label">Выручка</span>
                <span className="info" title={`Сумма по категориям = ${nf(sumCats, 2)}. Товары без категории не теряются: они в строке «без категории».`}>i</span>
              </div>
              <div className="value">{money(data.total)}</div>
              {Math.abs(sumCats - data.total) < 0.01 && <span className="pill ok">категории сходятся с итогом</span>}
            </div>
            <div className="card ice kpi">
              <span className="label">Лидер</span>
              <div className="value" style={{ fontSize: 30 }}>{top[0]?.name || "—"}</div>
              <div className="hint">{top[0] ? pct(top[0].revenue / data.total) + " выручки" : ""}</div>
            </div>
            <div className="card kpi">
              <span className="label">Категорий</span>
              <div className="value">{nf(data.categories.length)}</div>
              <div className="hint">{unknown ? money(unknown.revenue) + " без категории" : ""}</div>
            </div>
          </div>

          <div className="grid g2" style={{ marginTop: 16 }}>
            <div className="card">
              <h3>Топ категорий</h3>
              <ResponsiveContainer width="100%" height={top.length * 34 + 20}>
                <BarChart data={top} layout="vertical" margin={{ left: 0, right: 16 }}>
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" width={170} {...axis} fontSize={13} />
                  <Tooltip {...tip} formatter={(v: number) => [`${money(v)} · ${pct(v / data.total)}`, "выручка"]} />
                  <Bar dataKey="revenue" radius={9} barSize={18} cursor="pointer"
                    onClick={(d: any) => set({ category: f.category === d.key ? "" : d.key })}>
                    {top.map((c) => <Cell key={c.key} fill={c.key === f.category ? C.ice : c.is_unknown ? C.silver : C.ink} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="card">
              <h3>Как платят</h3>
              <div className="row" style={{ flexWrap: "nowrap", gap: 20 }}>
                <div style={{ width: 200, height: 200, flex: "none" }}>
                  <PieChart width={200} height={200}>
                    <Pie data={data.payments} dataKey="amount" nameKey="type" innerRadius={62} outerRadius={92} paddingAngle={3} cornerRadius={10} stroke="none">
                      {data.payments.map((p, i) => <Cell key={p.type} fill={PAY_COLORS[i % PAY_COLORS.length]} />)}
                    </Pie>
                    <Tooltip {...tip} formatter={(v: number, n: string) => [money(v), PAY[n] || n]} />
                  </PieChart>
                </div>
                <div style={{ flex: 1 }}>
                  {data.payments.map((p, i) => (
                    <div key={p.type} className="row" style={{ justifyContent: "space-between", margin: "10px 0" }}>
                      <span><i style={{ display: "inline-block", width: 10, height: 10, borderRadius: 99, background: PAY_COLORS[i % PAY_COLORS.length], marginRight: 8 }} />{PAY[p.type] || p.type}</span>
                      <b>{pct(p.amount / payTotal, 0)}</b>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <div className="row" style={{ justifyContent: "space-between", marginBottom: 14 }}>
              <h3>Топ-10 продавцов</h3>
              <span className="info" title="Выручка продавца — только по его товарам, а не по всему заказу.">i</span>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>#</th><th>Продавец</th><th>Город</th><th className="n">Заказы</th><th className="n">Товары</th><th className="n">Выручка</th></tr>
                </thead>
                <tbody>
                  {data.sellers.map((s, i) => (
                    <tr key={s.seller_id}>
                      <td>{i + 1}</td>
                      <td className="mono">{s.seller_id.slice(0, 8)}</td>
                      <td>{s.seller_city}, {s.seller_state}</td>
                      <td className="n">{nf(s.orders)}</td>
                      <td className="n">{nf(s.units)}</td>
                      <td className="n"><b>{nf(s.revenue, 2)}</b></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </>
  );
}
