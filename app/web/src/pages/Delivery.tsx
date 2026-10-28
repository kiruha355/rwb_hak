import Page from "../Page";
import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Col, DataTable, ErrorBox, KpiStrip, Loading, Panel, Seg, nf, pct, useApi, useFilters, useViewParam } from "../lib";
import { axis, tip, C } from "../charts";

type Split = { late: boolean; n: number; score: number; low_share: number; scored: number };
type State = { state: string; n: number; late_share: number; median_days: number; score: number };
type Delivery = {
  split: Split[];
  states: State[];
  stage: { late_n: number; handover_late: number; after_handover: number; unknown_stage: number };
  buckets: { bucket: string; n: number; late_share: number }[];
};
type LateRow = {
  order_id: string; state: string; city: string; purchased: string; promised: string; delivered: string;
  days_late: number; handover_late: boolean | null; sellers_count: number; order_gmv: number; score: number | null;
};

const MIN_N = 300;
const d = (s: string) => new Date(s).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "2-digit" });
const stageLabel = (v: boolean | null) => (v === null ? "нет данных" : v ? "передал продавец поздно" : "после передачи в доставку");

export default function Delivery() {
  const { qs, f, set } = useFilters();
  const { data, error, loading } = useApi<Delivery>("/api/delivery?" + qs);
  const lo = useApi<{ rows: LateRow[] }>("/api/late-orders?" + qs);
  const [small, setSmall] = useViewParam<"hide" | "show">("small", "hide");
  const on = data?.split.find((s) => !s.late);
  const late = data?.split.find((s) => s.late);
  const total = (on?.n || 0) + (late?.n || 0);
  const st = data?.stage;
  const states = (data?.states || []).filter((s) => small === "show" || s.n >= MIN_N);

  const stateCols: Col<State>[] = [
    { key: "state", label: "Штат", fmt: (s) => <>{s.state} {s.n < MIN_N && <span className="pill" title={`Меньше ${MIN_N} заказов — доля неустойчива`}>мало данных</span>}</> },
    { key: "n", label: "Доставлено", num: true, fmt: (s) => nf(s.n) },
    { key: "late_share", label: "Опоздали", num: true, bar: true, fmt: (s) => pct(s.late_share) },
    { key: "median_days", label: "Медиана, дн.", num: true, fmt: (s) => nf(s.median_days, 1) },
    { key: "score", label: "Оценка", num: true, fmt: (s) => nf(s.score, 2) },
  ];
  const lateCols: Col<LateRow>[] = [
    { key: "order_id", label: "Заказ", fmt: (r) => <span className="mono" title={r.order_id}>{r.order_id.slice(0, 12)}…</span> },
    { key: "city", label: "Покупатель", fmt: (r) => `${r.city}, ${r.state}` },
    { key: "purchased", label: "Куплен", fmt: (r) => d(r.purchased) },
    { key: "promised", label: "Обещали", fmt: (r) => d(r.promised) },
    { key: "delivered", label: "Вручили", fmt: (r) => d(r.delivered) },
    { key: "days_late", label: "Опоздание, дн.", num: true, fmt: (r) => <b>{nf(r.days_late)}</b> },
    { key: "handover_late", label: "Где задержка", value: (r) => stageLabel(r.handover_late), fmt: (r) => <span className={"pill" + (r.handover_late ? " no" : r.handover_late === false ? " ok" : "")}>{stageLabel(r.handover_late)}</span> },
    { key: "order_gmv", label: "Сумма заказа", num: true, fmt: (r) => nf(r.order_gmv, 2) },
    { key: "score", label: "Оценка", num: true, fmt: (r) => (r.score === null ? "—" : nf(r.score, 0)) },
  ];

  return (
    <Page title="Доставка" lead="Насколько вовремя доставляем, где возникают задержки и как опоздание влияет на оценку покупателя.">
      {error && <ErrorBox error={error} />}
      {loading && !data && <Loading />}
      {data && on && (
        <>
          <KpiStrip
            items={[
              { label: "Доставлено заказов", value: nf(total), sub: "с известной датой вручения" },
              { label: "Вовремя", value: pct(on.n / total), sub: `${nf(on.n)} заказов`, help: "Вручили не позже обещанной даты (по календарному дню). Не складывается по срезам." },
              { label: "С опозданием", value: late ? pct(late.n / total) : "—", sub: `${nf(late?.n || 0)} заказов` },
              { label: "Оценка, если вовремя", value: nf(on.score, 2), sub: `плохих оценок (1–2): ${pct(on.low_share)}` },
              { label: "Оценка при опоздании", value: late ? nf(late.score, 2) : "—", sub: late ? `плохих оценок (1–2): ${pct(late.low_share)}` : "" },
            ]}
          />

          <div className="grid g2 mt">
            <Panel title="Где возникла задержка" hint="Только опоздавшие заказы. В данных есть этап, но не причина — виноватых не называем.">
              {st && st.late_n > 0 ? (
                <>
                  <div className="stack" style={{ height: 14 }}>
                    <div style={{ width: (st.handover_late / st.late_n) * 100 + "%", background: C.sand }} />
                    <div style={{ width: (st.after_handover / st.late_n) * 100 + "%", background: C.ink }} />
                  </div>
                  <table style={{ marginTop: 12 }}>
                    <tbody>
                      <tr><td><i className="sw" style={{ background: C.sand }} />Продавец передал в доставку позже своего срока</td><td className="n">{nf(st.handover_late)}</td><td className="n"><b>{pct(st.handover_late / st.late_n)}</b></td></tr>
                      <tr><td><i className="sw" style={{ background: C.ink }} />Передал вовремя, задержка уже в доставке</td><td className="n">{nf(st.after_handover)}</td><td className="n"><b>{pct(st.after_handover / st.late_n)}</b></td></tr>
                      {st.unknown_stage > 0 && <tr><td className="dim">Этап не определить</td><td className="n">{nf(st.unknown_stage)}</td><td className="n">{pct(st.unknown_stage / st.late_n)}</td></tr>}
                      <tr className="total"><td>Всего опоздавших</td><td className="n">{nf(st.late_n)}</td><td className="n">100 %</td></tr>
                    </tbody>
                  </table>
                </>
              ) : <div className="empty">В этом срезе нет опозданий</div>}
            </Panel>
            <Panel title="Срок доставки" hint="Столбцы — заказы по числу дней от покупки до вручения, линия — доля опозданий в группе"
              csv={{ name: "srok_dostavki", columns: [{ key: "bucket", label: "Дней" }, { key: "n", label: "Заказов" }, { key: "late_share", label: "Доля опозданий" }], rows: data.buckets }}>
              <ResponsiveContainer width="100%" height={230}>
                <ComposedChart data={data.buckets} margin={{ top: 8, right: 0, left: 0 }}>
                  <CartesianGrid stroke={C.grid} vertical={false} />
                  <XAxis dataKey="bucket" {...axis} />
                  <YAxis yAxisId="n" {...axis} width={54} tickFormatter={(v) => nf(v)} />
                  <YAxis yAxisId="s" orientation="right" {...axis} width={40} tickFormatter={(v) => nf(v * 100, 0) + "%"} />
                  <Tooltip {...tip} formatter={(v: number, n: string) => (n === "n" ? [nf(v), "заказов"] : [pct(v), "опоздали"])} />
                  <Bar yAxisId="n" dataKey="n" fill={C.silver} radius={[2, 2, 0, 0]} />
                  <Line yAxisId="s" dataKey="late_share" stroke={C.accent} strokeWidth={2} dot={{ r: 3 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </Panel>
          </div>

          <Panel
            className="mt"
            title="Штаты покупателей"
            hint="Нажмите на строку, чтобы отфильтровать дашборд по штату. Доли нельзя складывать или усреднять между штатами."
            controls={<Seg value={small} onChange={setSmall} options={[{ id: "hide", label: `От ${MIN_N} заказов` }, { id: "show", label: "Все штаты" }]} />}
            csv={{ name: "shtaty", columns: stateCols.map((c) => ({ key: c.key, label: c.label })), rows: data.states }}
            flush
          >
            <DataTable cols={stateCols} rows={states} initialSort={{ key: "late_share", desc: true }} maxHeight={360}
              onRow={(s) => set({ state: f.state === s.state ? "" : s.state })} active={(s) => s.state === f.state} />
          </Panel>

          <Panel
            className="mt"
            title="Опоздавшие заказы"
            hint="60 заказов с самым большим опозданием в текущем срезе — для разбора с логистикой и продавцами"
            csv={lo.data ? { name: "opozdavshie_zakazy", columns: lateCols.map((c) => ({ key: c.key, label: c.label })), rows: lo.data.rows } : undefined}
            flush
          >
            {lo.data ? <DataTable cols={lateCols} rows={lo.data.rows} maxHeight={420} /> : <Loading />}
          </Panel>
        </>
      )}
    </Page>
  );
}
