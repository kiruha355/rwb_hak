import { ReactNode } from "react";
import {
  BASES, POPULATIONS, POLICIES, PERIODS, BlockBData, DeliveryMetrics,
  PriceRow, ReviewRow, Population, number, percent, stateLabel,
  populationLabel, basisLabel, policyLabel, periodLabel,
  csvRows,
} from "./contract";

function Csv<T extends object>({ name, rows, label = "Скачать CSV" }: { name: string; rows: T[]; label?: string }) {
  return <button type="button" className="btn sm" disabled={!rows.length} aria-label={`${label}: ${name}`} onClick={() => {
    const url = URL.createObjectURL(new Blob([csvRows(rows)], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a"); a.href = url; a.download = `${name}.csv`; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }}>{label}</button>;
}

function Table({ label, heads, children }: { label: string; heads: string[]; children: ReactNode }) {
  return <div className="bb-table" role="region" aria-label={label} tabIndex={0}>
    <table aria-label={label}><thead><tr>{heads.map((h, i) => <th key={h} scope="col" className={i ? "n" : ""}>{h}</th>)}</tr></thead>
      <tbody>{children}</tbody></table>
  </div>;
}
const Empty = ({ children = "Витрина не вернула строк." }: { children?: ReactNode }) => <p className="bb-empty">{children}</p>;
const Value = ({ value, digits = 0, suffix = "" }: { value: number | null; digits?: number; suffix?: string }) =>
  <span className={value === null ? "bb-unknown" : undefined}>{number(value, digits)}{value === null ? "" : suffix}</span>;
function Measured({ value, denominator, total, lateOrders, suffix }: {
  value: number | null; denominator: number; total: number; lateOrders?: number; suffix?: string;
}) {
  return <><Value value={value} digits={2} suffix={suffix} /><span className="bb-denom">
    {lateOrders === undefined ? `измерено ${number(denominator)} из ${number(total)}` : `${number(lateOrders)} из ${number(denominator)} измеренных`}
  </span></>;
}

const dateLabel = (date: string) => new Date(`${date}T00:00:00Z`).toLocaleDateString("ru-RU", { timeZone: "UTC", day: "2-digit", month: "2-digit", year: "2-digit" });
function PriceChart({ rows, id }: { rows: PriceRow[]; id: string }) {
  const measured = rows.filter((r): r is PriceRow & { purchase_date: string; price: number } => r.purchase_date !== null && r.price !== null);
  if (measured.length === 0) return <Empty>Нет точек с известными датой и ценой. Неизвестные значения сохранены в таблице.</Empty>;
  const times = measured.map(r => Date.parse(r.purchase_date)), prices = measured.map(r => r.price);
  const minX = Math.min(...times), maxX = Math.max(...times), minY = Math.min(...prices), maxY = Math.max(...prices);
  const x = (v: number) => minX === maxX ? 255 : 62 + (v - minX) / (maxX - minX) * 390;
  const y = (v: number) => minY === maxY ? 105 : 168 - (v - minY) / (maxY - minY) * 130;
  return <svg className="bb-chart" viewBox="0 0 480 220" role="img" aria-labelledby={`${id}-title ${id}-desc`}>
    <title id={`${id}-title`}>{`История цены товара ${rows[0].product_id}`}</title>
    <desc id={`${id}-desc`}>Каждая точка — дата покупки и отдельная цена; размер точки — число единиц. Точные значения в таблице.</desc>
    {[minY, ...(minY === maxY ? [] : [maxY])].map(v => <g key={v}><line className="bb-grid" x1={62} x2={452} y1={y(v)} y2={y(v)} /><text x={54} y={y(v) + 4} textAnchor="end">{number(v, 2)}</text></g>)}
    <text x={62} y={18}>Цена, R$</text>
    <text x={62} y={196}>{dateLabel(new Date(minX).toISOString().slice(0, 10))}</text>
    {minX !== maxX && <text x={452} y={196} textAnchor="end">{dateLabel(new Date(maxX).toISOString().slice(0, 10))}</text>}
    {measured.map(r => <circle className="bb-point" key={JSON.stringify([r.purchase_date, r.price])} cx={x(Date.parse(r.purchase_date))} cy={y(r.price)} r={Math.min(7, 2.5 + Math.sqrt(r.units_sold))} opacity={.75}>
      <title>{`${dateLabel(r.purchase_date)}: ${number(r.price, 2)} R$; ${number(r.units_sold)} ед.`}</title>
    </circle>)}
  </svg>;
}
function PriceHistory({ data }: { data: BlockBData }) {
  return <section className="bb-section" aria-labelledby="bb-q6"><header><h3 id="bb-q6">Q6 · История цены товара</h3>
    <Csv name="q06-price-history" rows={data.q6.rows} />
    <p className="bb-note">Лидеры по числу разных известных цен. При равенстве показаны все товары; дата — покупка заказа. Цены одного дня остаются отдельными точками.</p></header>
    <div className="bb-pair">{POPULATIONS.map(pop => {
      const rows = data.q6.rows.filter(r => r.population === pop), products = [...new Set(rows.map(r => r.product_id))].sort();
      return <div className="panel bb-body" key={pop}><h4>{populationLabel[pop]}</h4>
        {products.length === 0 && <Empty>Нет товара с известной ценой в этой совокупности.</Empty>}
        {products.map((product, i) => {
          const history = rows.filter(r => r.product_id === product).sort((a, b) => (a.purchase_date ?? "9999").localeCompare(b.purchase_date ?? "9999") || (a.price ?? Infinity) - (b.price ?? Infinity));
          const first = history[0];
          return <div className="bb-variant" key={product}><code className="bb-code bb-product">{product}</code>
            <p className="bb-note">Разных цен: {number(first.distinct_prices)}. Единиц без цены: {number(first.units_with_unknown_price)} за весь снимок товара.</p>
            <PriceChart rows={history} id={`bb-price-${pop}-${i}`} />
            {history.some(r => r.price === null || r.purchase_date === null) && <p className="bb-note">Есть строки без даты или цены; они доступны в таблице, но не на графике.</p>}
            <details><summary>Дата, цена и единицы товара</summary><Table label={`История ${product}, ${populationLabel[pop]}`} heads={["Дата покупки", "Цена, R$", "Единицы"]}>
              {history.map(r => <tr key={JSON.stringify([r.purchase_date, r.price])}><td>{r.purchase_date ? dateLabel(r.purchase_date) : "Дата неизвестна"}</td><td className="n"><Value value={r.price} digits={2} /></td><td className="n">{number(r.units_sold)}</td></tr>)}
            </Table></details>
          </div>;
        })}
      </div>;
    })}</div>
  </section>;
}

function DeliveryCells({ row }: { row: DeliveryMetrics }) {
  return <><td className="n">{number(row.orders_count)}</td>
    <td className="n"><Measured value={row.avg_delivery_days} denominator={row.duration_denominator} total={row.orders_count} /></td>
    <td className="n"><span className="bb-share"><span className="bb-track" aria-hidden="true">{row.late_pct !== null && <i style={{ width: `${Math.max(0, Math.min(100, row.late_pct))}%` }} />}</span>
      <Value value={row.late_pct} digits={2} suffix=" %" /></span><span className="bb-denom">{number(row.late_orders)} из {number(row.late_denominator)} измеренных</span></td></>;
}
function DeliveryStates({ data }: { data: BlockBData }) {
  return <section className="bb-section" aria-labelledby="bb-q7"><header><h3 id="bb-q7">Q7 · Доставка по штатам покупателя</h3>
    <Csv name="q07-delivery-states" rows={data.q7.rows.filter(r => r.orders_count >= 500)} />
    <p className="bb-note">Штаты с ≥ 500 заказами в каждой совокупности. Срок — от покупки до вручения, в дробных сутках; измерим только для доставленных. Отрицательный срок исключён из среднего.</p></header>
    <div className="bb-pair">{POPULATIONS.map(pop => {
      const rows = data.q7.rows.filter(r => r.population === pop && r.orders_count >= 500).sort((a, b) => (a.customer_state ?? "я").localeCompare(b.customer_state ?? "я") || BASES.indexOf(a.late_basis) - BASES.indexOf(b.late_basis));
      return <div className="panel bb-body" key={pop}><h4>{populationLabel[pop]}</h4>
        {rows.length ? <Table label={`Доставка по штатам: ${populationLabel[pop]}`} heads={["Штат / опоздание", "Заказы", "Средний срок, дни", "Опоздали"]}>
          {rows.map(r => <tr key={JSON.stringify([r.customer_state, r.late_basis])}><td>{stateLabel(r.customer_state)}<span className="bb-denom">{basisLabel[r.late_basis]}</span></td><DeliveryCells row={r} /></tr>)}
        </Table> : <Empty>Нет штатов с ≥ 500 заказами в этой совокупности.</Empty>}
      </div>;
    })}</div>
    <p className="bb-note">«По дате» — вручение позже обещанного календарного дня; «по времени» — позже точного момента. У среднего срока и доли опозданий отдельные знаменатели. Варианты не складываются.</p>
  </section>;
}
const statusNames: Record<string, string> = { delivered: "Доставлен", shipped: "В пути", canceled: "Отменён", unavailable: "Недоступен", invoiced: "Выставлен счёт", processing: "В обработке", created: "Создан", approved: "Подтверждён" };
function Statuses({ data }: { data: BlockBData }) {
  const rows = [...data.q8.rows].sort((a, b) => b.orders_count - a.orders_count);
  return <section className="bb-section" aria-labelledby="bb-q8"><header><h3 id="bb-q8">Q8 · Текущие статусы заказов</h3>
    <Csv name="q08-statuses" rows={data.q8.rows} />
    <p className="bb-note">Доли от всех заказов снимка. Распределение не показывает переходы или конверсию между статусами.</p></header>
    <div className="panel bb-body">{rows.length ? <Table label="Текущие статусы заказов" heads={["Статус", "Заказы", "Доля", "Без позиций"]}>
      {rows.map(r => <tr key={r.order_status ?? "null"}><td>{r.order_status === null ? "Статус неизвестен" : statusNames[r.order_status] ?? r.order_status}<span className="bb-denom">{r.order_status}</span></td>
        <td className="n">{number(r.orders_count)}</td><td className="n"><span className="bb-share"><span className="bb-track" aria-hidden="true">{r.orders_pct !== null && <i style={{ width: `${Math.max(0, Math.min(100, r.orders_pct))}%` }} />}</span>{percent(r.orders_pct)}</span></td><td className="n">{number(r.orders_without_items)}</td></tr>)}
    </Table> : <Empty />}</div>
  </section>;
}
const methodNames: Record<string, string> = { credit_card: "Кредитная карта", debit_card: "Дебетовая карта", boleto: "Boleto", voucher: "Ваучер", not_defined: "Не определён" };
function Payments({ data }: { data: BlockBData }) {
  const states = [...data.q9.states].sort((a, b) => (a.customer_state ?? "я").localeCompare(b.customer_state ?? "я"));
  return <section className="bb-section" aria-labelledby="bb-q9"><header><h3 id="bb-q9">Q9 · Способы оплаты и число частей</h3>
    <p className="bb-note">Одна запись — один платёж. 2018 год определяется датой покупки заказа: даты платежа в источнике нет. Число частей не задаёт срок в месяцах.</p></header>
    <div className="panel bb-body"><div className="bb-subhead"><h4>Штаты покупателя · покупки 2018 года · все статусы</h4><Csv name="q09-payment-states-2018" rows={data.q9.states} /></div>
      {states.length ? <Table label="Платежи по штатам за покупки 2018 года" heads={["Штат", "Платежи", "Сумма, R$", "Известная часть, R$", "Частей: все типы", "Частей: кредитная карта"]}>
        {states.map(r => <tr key={r.customer_state ?? "null"}><td>{stateLabel(r.customer_state)}</td><td className="n">{number(r.payment_count)}</td>
          <td className="n"><Value value={r.payment_amount} digits={2} /><span className="bb-denom">сумма известна у {number(r.amount_denominator)} из {number(r.payment_count)}</span></td>
          <td className="n"><Value value={r.known_payment_amount_sum} digits={2} /></td>
          <td className="n"><Measured value={r.avg_installments_all_types} denominator={r.installments_denominator} total={r.payment_count} /></td>
          <td className="n"><Value value={r.avg_installments_credit_card} digits={2} /><span className="bb-denom">измерено {number(r.credit_installments_denominator)} платежей картой</span></td>
        </tr>)}
      </Table> : <Empty>Нет платежей заказов, купленных в 2018 году.</Empty>}
      <p className="bb-note">При неизвестной сумме хотя бы одного платежа итог не определён; известная часть показана отдельно.</p>
    </div>
    <div className="bb-pair" style={{ marginTop: 16 }}>{PERIODS.map(period => {
      const rows = data.q9.methods.filter(r => r.period === period).sort((a, b) => b.payment_count - a.payment_count);
      return <div className="panel bb-body" key={period}><div className="bb-subhead"><h4>Способы оплаты · {periodLabel[period].toLowerCase()}</h4><Csv name={`q09-payment-methods-${period}`} rows={rows} /></div>
        {rows.length ? <Table label={`Способы оплаты: ${periodLabel[period]}`} heads={["Способ оплаты", "Платежи", "Среднее число частей"]}>
          {rows.map(r => <tr key={r.payment_type ?? "null"}><td>{r.payment_type === null ? "Способ неизвестен" : methodNames[r.payment_type] ?? r.payment_type}</td><td className="n">{number(r.payment_count)}</td>
            <td className="n"><Measured value={r.avg_installments} denominator={r.installments_denominator} total={r.payment_count} /></td></tr>)}
        </Table> : <Empty />}
      </div>;
    })}</div>
    <p className="bb-note">Два периода пересекаются: платежи покупок 2018 года входят во весь снимок. Итоги этих таблиц нельзя складывать.</p>
  </section>;
}

function ReviewChart({ rows, pop }: { rows: ReviewRow[]; pop: Population }) {
  const known = rows.filter(r => r.late_pct !== null);
  if (known.length === 0) return <Empty>Нет измеримой доли опозданий. Все пять оценок сохранены в таблицах.</Empty>;
  const ymax = Math.max(1, ...known.map(r => r.late_pct!));
  const ceiling = Math.min(100, Math.ceil(ymax / 10) * 10);
  const x = (score: number) => 54 + (score - 1) * 98;
  const y = (value: number) => 170 - value / ceiling * 135;
  return <svg viewBox="0 0 480 218" className="bb-chart" role="img" aria-labelledby={`bb-review-${pop}-title bb-review-${pop}-desc`}>
    <title id={`bb-review-${pop}-title`}>{`Оценка и доля опозданий: ${populationLabel[pop]}`}</title>
    <desc id={`bb-review-${pop}-desc`}>Оценки от 1 до 5; два правила учёта оценок и два определения опоздания. Пробел означает отсутствие измерения. Числа и знаменатели в таблицах.</desc>
    {[0, ceiling / 2, ceiling].map(v => <g key={v}><line className="bb-grid" x1={54} x2={446} y1={y(v)} y2={y(v)} /><text x={45} y={y(v) + 4} textAnchor="end">{number(v, ceiling < 2 ? 1 : 0)}%</text></g>)}
    <text x={54} y={18}>Доля опозданий</text>
    {[1, 2, 3, 4, 5].map(score => <text key={score} x={x(score)} y={193} textAnchor="middle">{score}</text>)}
    <text x={446} y={213} textAnchor="end">Оценка</text>
    {POLICIES.flatMap(policy => BASES.map(basis => {
      const series = rows.filter(r => r.score_policy === policy && r.late_basis === basis).sort((a, b) => a.review_score - b.review_score);
      const cls = `${policy === "single_score_only" ? " bb-alt" : ""}${basis === "timestamp" ? " bb-timestamp" : ""}`;
      // Missing values break the line; they never become zero or get bridged.
      let path = "", connected = false;
      for (const row of series) {
        if (row.late_pct === null) { connected = false; continue; }
        path += `${connected ? "L" : "M"}${x(row.review_score)},${y(row.late_pct)} `;
        connected = true;
      }
      return <g key={`${policy}-${basis}`}><path className={`bb-line${cls}`} d={path} />
        {series.filter(r => r.late_pct !== null).map(r => <circle key={r.review_score} className={`bb-point${cls}`} cx={x(r.review_score)} cy={y(r.late_pct!)} r={basis === "timestamp" ? 2.5 : 4}>
          <title>{`${policyLabel[policy]}, ${basisLabel[basis].toLowerCase()}, оценка ${r.review_score}: ${percent(r.late_pct)} (${number(r.late_orders)} из ${number(r.late_denominator)})`}</title>
        </circle>)}
      </g>;
    }))}
  </svg>;
}
function Reviews({ data }: { data: BlockBData }) {
  return <section className="bb-section" aria-labelledby="bb-q10"><header><h3 id="bb-q10">Q10 · Оценка покупателя и доставка</h3>
    <Csv name="q10-review-delivery-variants" rows={data.q10.rows} />
    <p className="bb-note">«Каждая оценка заказа» учитывает заказ по одному разу в каждой его оценке: группы могут пересекаться. «Только одна оценка» исключает заказы с разными известными оценками.</p></header>
    <div className="bb-legend">{POLICIES.flatMap(policy => BASES.map(basis => <span key={`${policy}-${basis}`}><i aria-hidden="true" className={`bb-swatch${policy === "single_score_only" ? " bb-alt" : ""}${basis === "timestamp" ? " bb-timestamp" : ""}`} />{policyLabel[policy]} · {basisLabel[basis].toLowerCase()}</span>))}</div>
    <div className="bb-pair">{POPULATIONS.map(pop => {
      const rows = data.q10.rows.filter(r => r.population === pop);
      return <div className="panel bb-body" key={pop}><h4>{populationLabel[pop]}</h4>
        {rows.length ? <><ReviewChart rows={rows} pop={pop} />{POLICIES.map(policy => <div className="bb-variant" key={policy}><h4>{policyLabel[policy]}</h4>
          <Table label={`Оценки: ${populationLabel[pop]}, ${policyLabel[policy]}`} heads={["Оценка / опоздание", "Заказы", "Средний срок, дни", "Опоздали"]}>
            {rows.filter(r => r.score_policy === policy).sort((a, b) => a.review_score - b.review_score || BASES.indexOf(a.late_basis) - BASES.indexOf(b.late_basis)).map(r =>
              <tr key={`${r.review_score}-${r.late_basis}`}><td>{r.review_score}<span className="bb-denom">{basisLabel[r.late_basis]}</span></td><DeliveryCells row={r} /></tr>)}
          </Table></div>)}</> : <Empty />}
      </div>;
    })}</div>
    <p className="bb-note">Срок измеряется только у доставленных с датами и неотрицательной длительностью. У среднего срока и доли опозданий разные знаменатели. Наблюдаемая связь не доказывает причинность.</p>
    <div className="panel bb-body"><div className="bb-subhead"><h4>Охват оценок</h4><Csv name="q10-review-coverage" rows={data.q10.coverage} /></div>
      {data.q10.coverage.length ? <Table label="Охват оценок, причины могут пересекаться" heads={["Совокупность", "Всего заказов", "Без оценки", "Разные оценки", "Несколько оценок 1–5", "Оценка вне 1–5"]}>
        {data.q10.coverage.map(r => <tr key={r.population}><td>{populationLabel[r.population]}</td><td className="n">{number(r.orders_count)}</td><td className="n">{number(r.orders_without_score)}</td><td className="n">{number(r.orders_with_multiple_scores)}</td><td className="n">{number(r.orders_in_multiple_valid_score_groups)}</td><td className="n">{number(r.orders_with_out_of_range_score)}</td></tr>)}
      </Table> : <Empty>Диагностика охвата не вернула строк.</Empty>}
      <p className="bb-note">Причины пересекаются; их нельзя складывать. Число заказов по пяти оценкам также не является числом уникальных заказов для правила «Каждая оценка заказа».</p>
    </div>
  </section>;
}

export function BlockBContent({ data }: { data: BlockBData }) {
  return <><PriceHistory data={data} /><DeliveryStates data={data} /><Statuses data={data} /><Payments data={data} /><Reviews data={data} />
    <details className="bb-meta"><summary>Охват и источник ответа API</summary><pre>{JSON.stringify(data.meta, null, 2)}</pre></details>
  </>;
}
