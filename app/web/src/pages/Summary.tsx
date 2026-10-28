import { Link } from "react-router-dom";
import { Area, AreaChart, Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Filters from "../Filters";
import { ErrorBox, Loading, PageHead, Ring, money, monthLabel, nf, pct, useApi, useFilters } from "../lib";
import { axis, tip, C } from "../charts";

type Overview = {
  kpi: {
    orders_placed: number; orders_delivered: number; avg_check: number; buyers: number;
    review_avg: number; item_revenue: number; late_share: number; median_days: number;
  };
  series: { month: string; placed: number; delivered: number; revenue: number; late_share: number | null; late_n: number }[];
};
type Delivery = {
  split: { late: boolean; n: number; score: number; low_share: number }[];
  states: { state: string; n: number; late_share: number }[];
};

const MIN_N = 300;

export default function Summary() {
  const { qs } = useFilters();
  const ov = useApi<Overview>("/api/overview?" + qs);
  const dl = useApi<Delivery>("/api/delivery?" + qs);
  const k = ov.data?.kpi;
  const series = (ov.data?.series || []).map((s) => ({ ...s, label: monthLabel(s.month) }));
  const on = dl.data?.split.find((s) => !s.late);
  const late = dl.data?.split.find((s) => s.late);
  const worst = [...(dl.data?.states || [])].filter((s) => s.n >= MIN_N).sort((a, b) => b.late_share - a.late_share)[0];
  const peak = [...series].filter((s) => s.late_n >= 100 && s.late_share !== null).sort((a, b) => (b.late_share || 0) - (a.late_share || 0))[0];
  const link = (to: string) => to + (qs ? "?" + qs : "");

  return (
    <>
      <PageHead eyebrow="" title="Сводка" />
      <Filters />
      {ov.error && <ErrorBox error={ov.error} />}
      {ov.loading && !k && <Loading />}
      {k && (
        <>
          <div className="grid g4">
            <div className="card dark span2 kpi">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <span className="label">Выручка с доставленных</span>
                <span className="info" title={"Сумма цен товаров в доставленных заказах, без стоимости доставки.\nМожно складывать по месяцам, штатам, категориям."}>i</span>
              </div>
              <div className="value">{money(k.item_revenue)}</div>
              <ResponsiveContainer width="100%" height={86}>
                <AreaChart data={series} margin={{ top: 6, right: 0, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={C.ice} stopOpacity={0.55} />
                      <stop offset="100%" stopColor={C.ice} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Tooltip {...tip} labelFormatter={(_, p: any) => p?.[0]?.payload.label} formatter={(v: number) => [money(v), "выручка"]} />
                  <Area type="monotone" dataKey="revenue" stroke={C.ice} strokeWidth={3} fill="url(#rev)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="card ice">
              <Stat label="Средний чек" value={nf(k.avg_check, 2)} hint="товары + доставка"
                help={"Среднее по доставленным заказам от суммы цен и доставки.\nНельзя складывать по срезам."} />
            </div>
            <div className="card">
              <Stat label="Покупатели" value={nf(k.buyers)} hint={`${nf(k.orders_placed)} заказов`}
                help={"Уникальные люди (customer_unique_id) по всем заказам.\nНельзя складывать по срезам: один человек покупает в разных месяцах."} />
            </div>
          </div>

          <div className="grid g3" style={{ marginTop: 16 }}>
            <div className="card row" style={{ gap: 22, flexWrap: "nowrap" }}>
              <Ring value={1 - k.late_share} label="вовремя" />
              <div>
                <h3>Доставка</h3>
                <div className="muted">медиана {nf(k.median_days, 0)} дн.</div>
                <div className="muted">оценка {nf(k.review_avg, 2)} ★</div>
              </div>
            </div>
            <div className="card sand">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <h3>Цена опоздания</h3>
                <Link className="arrow-btn" to={link("/delivery")}>→</Link>
              </div>
              {on && late ? (
                <div className="row" style={{ gap: 18, marginTop: 10, alignItems: "baseline" }}>
                  <span className="big-num" style={{ fontSize: 48 }}>{nf(on.score, 1)}</span>
                  <span className="muted" style={{ fontSize: 22 }}>→</span>
                  <span className="big-num" style={{ fontSize: 48 }}>{nf(late.score, 1)} ★</span>
                </div>
              ) : <div className="muted">нет опозданий в срезе</div>}
              <div className="muted" style={{ marginTop: 8 }}>вовремя → с опозданием</div>
            </div>
            <div className="card">
              <h3>Требует внимания</h3>
              <div className="grid" style={{ gap: 10, marginTop: 12 }}>
                {worst && (
                  <div className="row" style={{ justifyContent: "space-between" }}>
                    <span>Штат <b>{worst.state}</b></span>
                    <span className="pill no">{pct(worst.late_share)} опозданий</span>
                  </div>
                )}
                {peak && (
                  <div className="row" style={{ justifyContent: "space-between" }}>
                    <span>Месяц <b>{peak.label}</b></span>
                    <span className="pill no">{pct(peak.late_share)} опозданий</span>
                  </div>
                )}
                {late && (
                  <div className="row" style={{ justifyContent: "space-between" }}>
                    <span>Оценки 1–2 при опоздании</span>
                    <span className="pill no">{pct(late.low_share)}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <h3>Заказы по месяцам</h3>
              <div className="legend" style={{ margin: 0 }}>
                <span><i style={{ background: C.ink }} />доставлены</span>
                <span><i style={{ background: C.silver }} />прочие статусы</span>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={series.map((s) => ({ ...s, other: s.placed - s.delivered }))} margin={{ top: 16 }}>
                <XAxis dataKey="label" {...axis} interval={1} />
                <YAxis {...axis} width={50} tickFormatter={(v) => nf(v)} />
                <Tooltip {...tip} formatter={(v: number, n: string) => [nf(v), n === "delivered" ? "доставлены" : "прочие статусы"]} />
                <Bar dataKey="delivered" stackId="a" fill={C.ink} radius={[0, 0, 8, 8]} />
                <Bar dataKey="other" stackId="a" radius={[10, 10, 0, 0]}>
                  {series.map((s) => <Cell key={s.month} fill={C.silver} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <p className="note">Пустой ноябрь 2016 остаётся на оси: месяцы берутся из календаря, а не из заказов.</p>
          </div>
        </>
      )}
    </>
  );
}

function Stat({ label, value, hint, help }: { label: string; value: string; hint?: string; help?: string }) {
  return (
    <div className="kpi">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <span className="label">{label}</span>
        {help && <span className="info" title={help}>i</span>}
      </div>
      <div className="value">{value}</div>
      {hint && <div className="hint">{hint}</div>}
    </div>
  );
}
