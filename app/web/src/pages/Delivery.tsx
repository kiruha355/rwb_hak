import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Filters from "../Filters";
import { ErrorBox, Loading, PageHead, Ring, nf, pct, useApi, useFilters } from "../lib";
import { axis, tip, C } from "../charts";

type Delivery = {
  split: { late: boolean; n: number; score: number; low_share: number; scored: number }[];
  states: { state: string; n: number; late_share: number; median_days: number; score: number }[];
  stage: { late_n: number; handover_late: number; after_handover: number; unknown_stage: number };
  buckets: { bucket: string; n: number; late_share: number }[];
};
type Late = {
  rows: { order_id: string; state: string; city: string; purchased: string; promised: string; delivered: string;
    days_late: number; handover_late: boolean | null; sellers_count: number; order_gmv: number; score: number | null }[];
};

const MIN_N = 300;
const d = (s: string) => new Date(s).toLocaleDateString("ru-RU", { day: "numeric", month: "short", year: "2-digit" });

export default function Delivery() {
  const { qs, f, set } = useFilters();
  const { data, error, loading } = useApi<Delivery>("/api/delivery?" + qs);
  const lo = useApi<Late>("/api/late-orders?" + qs);
  const on = data?.split.find((s) => !s.late);
  const late = data?.split.find((s) => s.late);
  const total = (on?.n || 0) + (late?.n || 0);
  const st = data?.stage;
  const states = [...(data?.states || [])].filter((s) => s.n >= MIN_N).sort((a, b) => b.late_share - a.late_share).slice(0, 8);
  const maxShare = states[0]?.late_share || 1;
  return (
    <>
      <PageHead eyebrow="" title="Доставка" />
      <Filters />
      {error && <ErrorBox error={error} />}
      {loading && !data && <Loading />}
      {data && on && (
        <>
          <div className="grid g3">
            <div className="card ice">
              <span className="muted">Вовремя · {pct(on.n / total, 0)}</span>
              <div className="big-num" style={{ margin: "14px 0 8px" }}>{nf(on.score, 2)} ★</div>
              <span className="pill">{pct(on.low_share, 0)} плохих оценок</span>
            </div>
            <div className="card sand">
              <span className="muted">С опозданием · {late ? pct(late.n / total, 0) : "—"}</span>
              <div className="big-num" style={{ margin: "14px 0 8px" }}>{late ? nf(late.score, 2) : "—"} ★</div>
              <span className="pill">{late ? pct(late.low_share, 0) : "—"} плохих оценок</span>
            </div>
            <div className="card row" style={{ gap: 20, flexWrap: "nowrap" }}>
              {st && st.late_n > 0 && <Ring value={st.handover_late / st.late_n} label="у продавца" color={C.ink} />}
              <div>
                <h3>Где застряло</h3>
                <div className="muted" style={{ fontSize: 14 }}>
                  {st && st.late_n > 0 && <>продавец передал поздно, остальное — после передачи</>}
                </div>
                <span className="info" title="Этап задержки, а не виноватый: причины в данных нет." style={{ marginTop: 8 }}>i</span>
              </div>
            </div>
          </div>

          <div className="grid g2" style={{ marginTop: 16 }}>
            <div className="card dark">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <h3>Штаты с опозданиями</h3>
                <span className="info" title={`Только штаты от ${MIN_N} заказов. Доли нельзя складывать — каждый раз пересчитываются из заказов.`}>i</span>
              </div>
              <div style={{ marginTop: 12 }}>
                {states.map((s) => (
                  <div key={s.state} className="bar-row" style={{ cursor: "pointer", gridTemplateColumns: "48px 1fr 64px" }}
                    onClick={() => set({ state: f.state === s.state ? "" : s.state })}>
                    <b>{s.state}</b>
                    <div className="track"><div className="fill" style={{ width: (s.late_share / maxShare) * 100 + "%" }} /></div>
                    <span style={{ textAlign: "right" }}>{pct(s.late_share, 0)}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="card">
              <h3>Дней от покупки до вручения</h3>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.buckets} margin={{ top: 16 }}>
                  <XAxis dataKey="bucket" {...axis} />
                  <YAxis {...axis} tickFormatter={(v) => nf(v)} width={54} />
                  <Tooltip {...tip} formatter={(v: number, _n: string, p: any) => [`${nf(v)} · опоздали ${pct(p.payload.late_share, 0)}`, "заказов"]} />
                  <Bar dataKey="n" radius={[12, 12, 12, 12]}>
                    {data.buckets.map((b) => <Cell key={b.bucket} fill={b.late_share > 0.08 ? C.ice : C.silver} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="legend" style={{ marginTop: 6 }}>
                <span><i style={{ background: C.ice }} />много опозданий</span>
              </div>
            </div>
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <div className="row" style={{ justifyContent: "space-between", marginBottom: 14 }}>
              <h3>Самые долгие опоздания</h3>
              <span className="pill">{lo.data ? nf(lo.data.rows.length) : "…"} заказов</span>
            </div>
            {lo.data && (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th>Заказ</th><th>Город</th><th>Обещали</th><th>Привезли</th><th className="n">Опоздание</th><th>Где застряло</th><th className="n">Оценка</th></tr>
                  </thead>
                  <tbody>
                    {lo.data.rows.map((r) => (
                      <tr key={r.order_id}>
                        <td className="mono">{r.order_id.slice(0, 8)}</td>
                        <td>{r.city}, {r.state}</td>
                        <td>{d(r.promised)}</td>
                        <td>{d(r.delivered)}</td>
                        <td className="n"><b>{nf(r.days_late)} дн.</b></td>
                        <td>{r.handover_late === null ? <span className="pill">нет данных</span> : r.handover_late ? <span className="pill no">у продавца</span> : <span className="pill ok">в доставке</span>}</td>
                        <td className="n">{r.score === null ? "—" : nf(r.score, 0) + " ★"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </>
  );
}
