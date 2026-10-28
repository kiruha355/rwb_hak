import { ErrorBox, Loading, PageHead, nf, useApi } from "../lib";

type Answers = {
  q1: { rows: { month: string; orders_placed: number; orders_delivered: number; item_revenue: number }[]; total: number; control: { rows: number; total: number } };
  q2: { rows: { revenue_rank: number; seller_id: string; seller_city: string; seller_state: string; orders_delivered: number; units_delivered: number; orders_all_statuses: number; item_revenue: number }[]; control: { top1: number } };
  q3: { row: { n_delivered_orders: number; avg_order_gmv_rounded: number; avg_payment_amount_rounded: number; avg_source_rows: number; avg_units: number; avg_distinct_product_seller_lines: number }; control: { avg_check: number } };
  q4: { row: { buyers: number; repeat_buyers: number; repeat_buyer_pct_rounded: number }; window: { buyers: number; repeat_buyers: number; repeat_buyer_pct_rounded: number }; control: { buyers: number; pct: number } };
  q5: { rows: { category_key: string; name: string; item_revenue: number; revenue_pct_rounded: number }[]; total: number; control: { categories: number; top: number; total: number } };
};

const Ok = ({ ok }: { ok: boolean }) => <span className={"pill " + (ok ? "ok" : "no")}>{ok ? "✓ совпало с контролем" : "✗ не совпало"}</span>;
const near = (a: number, b: number) => Math.abs(a - b) < 0.006;

export default function AnswersPage() {
  const { data, error } = useApi<Answers>("/api/answers");
  return (
    <>
      <PageHead
        eyebrow="06 · Ответы из модели"
        title="Вопросы Q1–Q5"
        lead="Каждый ответ — витрина mart, которая читает одну и ту же модель core. Рядом — контрольная цифра из задания."
      />
      {error && <ErrorBox error={error} />}
      {!data && !error && <Loading />}
      {data && (
        <div className="grid g2">
          <div className="card">
            <div className="row" style={{ justifyContent: "space-between" }}><h3>Q1 · Выручка и заказы по месяцам</h3><Ok ok={data.q1.rows.length === 24 && near(data.q1.total, data.q1.control.total)} /></div>
            <p className="sub">{data.q1.rows.length} месяцев · итого {nf(data.q1.total, 2)} · две колонки заказов: оформлено и доставлено</p>
            <div className="table-wrap" style={{ maxHeight: 300 }}>
              <table>
                <thead><tr><th>Месяц</th><th className="n">Оформлено</th><th className="n">Доставлено</th><th className="n">Выручка</th></tr></thead>
                <tbody>
                  {data.q1.rows.map((r) => (
                    <tr key={r.month} className={r.orders_placed === 0 ? "hl" : ""}>
                      <td>{r.month}</td><td className="n">{nf(r.orders_placed)}</td><td className="n">{nf(r.orders_delivered)}</td><td className="n">{nf(r.item_revenue, 2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="card">
            <div className="row" style={{ justifyContent: "space-between" }}><h3>Q2 · Топ-10 продавцов</h3><Ok ok={near(data.q2.rows[0]?.item_revenue, data.q2.control.top1)} /></div>
            <p className="sub">Выручка только по товарам продавца; заказы и единицы — доставленные, рядом — все статусы.</p>
            <div className="table-wrap" style={{ maxHeight: 300 }}>
              <table>
                <thead><tr><th>#</th><th>Продавец</th><th>Город</th><th className="n">Заказы</th><th className="n">Ед.</th><th className="n">Все статусы</th><th className="n">Выручка</th></tr></thead>
                <tbody>
                  {data.q2.rows.map((r) => (
                    <tr key={r.seller_id}><td>{r.revenue_rank}</td><td className="mono">{r.seller_id.slice(0, 8)}…</td><td>{r.seller_city}, {r.seller_state}</td><td className="n">{nf(r.orders_delivered)}</td><td className="n">{nf(r.units_delivered)}</td><td className="n">{nf(r.orders_all_statuses)}</td><td className="n">{nf(r.item_revenue, 2)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="card">
            <div className="row" style={{ justifyContent: "space-between" }}><h3>Q3 · Средний чек</h3><Ok ok={near(data.q3.row.avg_order_gmv_rounded, data.q3.control.avg_check)} /></div>
            <div className="big-num chrome" style={{ margin: "12px 0" }}>{nf(data.q3.row.avg_order_gmv_rounded, 2)}</div>
            <p className="sub">Σ (товары + доставка) ÷ {nf(data.q3.row.n_delivered_orders)} доставленных заказов. По платежам вышло бы {nf(data.q3.row.avg_payment_amount_rounded, 2)} — контроль различает.</p>
            <div className="grid g3">
              <div><div className="dim" style={{ fontSize: 12 }}>строк на заказ</div><b>{nf(data.q3.row.avg_source_rows, 3)}</b></div>
              <div><div className="dim" style={{ fontSize: 12 }}>единиц на заказ</div><b>{nf(data.q3.row.avg_units, 3)}</b></div>
              <div><div className="dim" style={{ fontSize: 12 }}>разных «товар × продавец»</div><b>{nf(data.q3.row.avg_distinct_product_seller_lines, 3)}</b></div>
            </div>
          </div>
          <div className="card">
            <div className="row" style={{ justifyContent: "space-between" }}><h3>Q4 · Покупатели и повторные покупки</h3><Ok ok={data.q4.row.buyers === data.q4.control.buyers && near(data.q4.row.repeat_buyer_pct_rounded, data.q4.control.pct)} /></div>
            <div className="row" style={{ gap: 30, margin: "12px 0" }}>
              <div><div className="big-num chrome" style={{ fontSize: 48 }}>{nf(data.q4.row.buyers)}</div><div className="dim">покупателей</div></div>
              <div><div className="big-num acc" style={{ fontSize: 48 }}>{nf(data.q4.row.repeat_buyer_pct_rounded, 2)} %</div><div className="dim">вернулись · {nf(data.q4.row.repeat_buyers)} человек</div></div>
            </div>
            <p className="sub">Человек — customer_unique_id, по всему периоду. Только в окне Q1 было бы {nf(data.q4.window.repeat_buyer_pct_rounded, 2)} %.</p>
          </div>
          <div className="card span2">
            <div className="row" style={{ justifyContent: "space-between" }}><h3>Q5 · Выручка по категориям</h3><Ok ok={data.q5.rows.length === data.q5.control.categories && near(data.q5.total, data.q5.control.total)} /></div>
            <p className="sub">{data.q5.rows.length} категорий, включая unknown · сумма по категориям {nf(data.q5.total, 2)} = общей выручке</p>
            <div className="table-wrap" style={{ maxHeight: 280 }}>
              <table>
                <thead><tr><th>Категория</th><th className="n">Выручка</th><th className="n">Доля</th></tr></thead>
                <tbody>
                  {data.q5.rows.map((r) => (
                    <tr key={r.category_key} className={r.category_key === "unknown" ? "hl" : ""}><td>{r.name}</td><td className="n">{nf(r.item_revenue, 2)}</td><td className="n">{nf(r.revenue_pct_rounded, 2)} %</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
