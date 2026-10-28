import { useLayoutEffect, useRef, useState } from "react";
import { ErrorBox, Loading, PageHead, nf, useApi } from "../lib";

type Key = { tbl: string; type: string; def: string };
type Col = { name: string; type: string };
type ModelData = {
  raw: { raw: string | null; core: string[]; rule: string; rows: number | null }[];
  core: { name: string; comment: string; rows: number; keys: Key[]; columns: Col[] }[];
  mart: { name: string; kind: string; comment: string | null; uses: string[]; columns: Col[] }[];
  balance: { check_name: string; expected: string; actual: string; ok: boolean }[];
};
type Sel = { layer: "raw" | "core" | "mart"; name: string } | null;

const GRAIN: Record<string, string> = {
  fact_order: "одна строка = один заказ, даже без товаров, платежей или отзывов",
  fact_order_item: "одна строка = одна единица товара в заказе",
  fact_payment: "одна строка = один платёж заказа",
  fact_review: "одна строка = пара «отзыв + заказ»",
  dim_customer: "одна строка = один реальный человек",
  dim_customer_context: "одна строка = покупатель в конкретном заказе (адрес на тот момент)",
  dim_seller: "одна строка = один продавец",
  dim_product: "одна строка = один товар",
  dim_category: "одна строка = одна категория, плюс unknown",
  dim_date: "одна строка = один день календаря",
  dim_order_status: "одна строка = один статус и правило «даёт ли выручку»",
  data_issues: "одна строка = одна найденная аномалия в исходных данных",
  check_results: "одна строка = одна самопроверка последней сборки",
};
const MART: Record<string, string> = {
  q01_revenue_monthly: "Ответ Q1: выручка и заказы по месяцам",
  q02_sellers_top10: "Ответ Q2: топ-10 продавцов",
  q03_average_order: "Ответ Q3: средний чек и строки на заказ",
  q04_buyers_repeat: "Ответ Q4: покупатели и повторные покупки",
  q04_buyers_repeat_q1_window: "Q4 в окне Q1 — для сравнения",
  q05_category_revenue: "Ответ Q5: выручка по категориям",
  v_orders: "Широкая витрина заказов: суммы, покрытие денег, отзывы",
  v_order_items: "Широкая витрина товаров с заказом, категорией и продавцом",
  v_order_delivery_variants: "Опоздания и сроки доставки по заказу",
  v_order_payment_reconciliation: "Сверка платежей и товаров по заказу",
  v_payment_reconciliation: "Сводная сверка денег по группам",
  v_review: "Отзыв как сущность (производная от пар)",
  v_review_payload_variants: "Разные версии одного отзыва",
  v_review_weighting: "Средняя оценка при разных весах",
  metric_definitions: "Паспорта метрик: формула, уровень, складывается ли",
};
const KIND: Record<string, string> = { fact: "событие", dim: "справочник", data: "служебная", check: "служебная" };
const norm = (s: string) => (s.includes(".") ? s : "core." + s);
const ORDER = ["fact_order", "fact_order_item", "fact_payment", "fact_review", "dim_customer", "dim_customer_context", "dim_product", "dim_category", "dim_seller", "dim_order_status", "dim_date", "data_issues", "check_results"];
const rank = (n: string) => {
  const i = ORDER.indexOf(n);
  if (i >= 0) return i;
  return n.startsWith("q0") ? 0 : n.startsWith("v_") ? 1 : 2;
};

export default function Model() {
  const { data, error } = useApi<ModelData>("/api/model");
  const [sel, setSel] = useState<Sel>(null);
  const box = useRef<HTMLDivElement>(null);
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const [lines, setLines] = useState<{ x1: number; y1: number; x2: number; y2: number }[]>([]);

  // related nodes for the current selection
  const related = new Set<string>();
  if (data && sel) {
    if (sel.layer === "raw") data.raw.find((r) => r.raw === sel.name)?.core.forEach((c) => related.add("core:" + c));
    if (sel.layer === "core") {
      data.raw.filter((r) => r.core.includes(sel.name) && r.raw).forEach((r) => related.add("raw:" + r.raw));
      data.mart.filter((m) => m.uses.map(norm).includes("core." + sel.name)).forEach((m) => related.add("mart:" + m.name));
    }
    if (sel.layer === "mart") {
      const m = data.mart.find((x) => x.name === sel.name);
      m?.uses.map(norm).forEach((u) => related.add(u.replace(/^core\./, "core:").replace(/^mart\./, "mart:")));
      data.mart.filter((x) => x.uses.map(norm).includes("mart." + sel.name)).forEach((x) => related.add("mart:" + x.name));
    }
  }

  useLayoutEffect(() => {
    const draw = () => {
      if (!sel || !box.current) return setLines([]);
      const b = box.current.getBoundingClientRect();
      const from = refs.current[sel.layer + ":" + sel.name];
      if (!from) return setLines([]);
      const fr = from.getBoundingClientRect();
      const out: typeof lines = [];
      related.forEach((k) => {
        const el = refs.current[k];
        if (!el) return;
        const r = el.getBoundingClientRect();
        const leftToRight = r.left > fr.left;
        const sameCol = Math.abs(r.left - fr.left) < 5;
        out.push({
          x1: (sameCol ? fr.right : leftToRight ? fr.right : fr.left) - b.left,
          y1: fr.top + fr.height / 2 - b.top,
          x2: (sameCol ? r.right : leftToRight ? r.left : r.right) - b.left,
          y2: r.top + r.height / 2 - b.top,
        });
      });
      setLines(out);
    };
    draw();
    window.addEventListener("resize", draw);
    return () => window.removeEventListener("resize", draw);
  }, [sel, data]);

  const node = (layer: "raw" | "core" | "mart", name: string, right: string, kind?: string) => {
    const key = layer + ":" + name;
    const isSel = sel?.layer === layer && sel.name === name;
    const cls = "node" + (isSel ? " sel" : related.has(key) ? " rel" : sel ? " fade" : "");
    return (
      <button key={key} ref={(el) => (refs.current[key] = el)} className={cls} onClick={() => setSel(isSel ? null : { layer, name })}>
        <span>
          {kind && <div className="kind">{kind}</div>}
          <span className="nm">{name}</span>
        </span>
        <span className="cnt">{right}</span>
      </button>
    );
  };

  return (
    <>
      <PageHead
        eyebrow="04 · Логика реализации"
        title="Как устроена модель"
        lead="Нажмите на сырую таблицу — увидите, во что она превратилась в модели. Нажмите на таблицу модели — увидите, какие витрины её читают. Нажмите на витрину — увидите её SQL и результат."
      />
      {error && <ErrorBox error={error} />}
      {!data && !error && <Loading text="Читаем каталог базы…" />}
      {data && (
        <>
          <div className="card">
            <div className="lineage" ref={box}>
              <svg className="links">
                {lines.map((l, i) => {
                  const mx = (l.x1 + l.x2) / 2;
                  const d = Math.abs(l.x1 - l.x2) < 5
                    ? `M${l.x1},${l.y1} C${l.x1 + 40},${l.y1} ${l.x2 + 40},${l.y2} ${l.x2},${l.y2}`
                    : `M${l.x1},${l.y1} C${mx},${l.y1} ${mx},${l.y2} ${l.x2},${l.y2}`;
                  return <path key={i} d={d} fill="none" stroke="#63b3e3" strokeWidth={2} strokeOpacity={0.9} />;
                })}
              </svg>
              <div>
                <div className="col-title">raw</div>
                <div className="col-sub">как пришло · 8 файлов, всё текстом</div>
                {data.raw.filter((r) => r.raw).map((r) => node("raw", r.raw!, nf(r.rows)))}
                <div className="note">dim_date не из файла: календарь генерируется самой сборкой.</div>
              </div>
              <div>
                <div className="col-title chrome">core — модель</div>
                <div className="col-sub">4 события + 7 справочников + 2 служебные</div>
                {[...data.core].sort((a, b) => rank(a.name) - rank(b.name)).map((c) => node("core", c.name, nf(c.rows), KIND[c.name.split("_")[0]]))}
              </div>
              <div>
                <div className="col-title">mart — витрины</div>
                <div className="col-sub">сохранённые запросы: ответы и данные дашборда</div>
                {[...data.mart].sort((a, b) => rank(a.name) - rank(b.name) || a.name.localeCompare(b.name)).map((m) => node("mart", m.name, m.kind === "view" ? "запрос" : "таблица"))}
              </div>
            </div>
          </div>
          {sel ? <Detail sel={sel} data={data} /> : <Hint />}
          <Trace />
        </>
      )}
    </>
  );
}

function Hint() {
  return (
    <div className="card detail row" style={{ gap: 18 }}>
      <img className="sticker" src="/img/face_right.png" alt="" />
      <div className="muted">
        Начните с любой таблицы слева. Например, <b className="acc">order_reviews</b>: в модели она становится <b>fact_review</b> с ключом «отзыв + заказ», а его читают витрины про отзывы и заказы.
      </div>
    </div>
  );
}

function Preview({ schema, name }: { schema: string; name: string }) {
  const { data, error } = useApi<{ columns: string[]; rows: Record<string, unknown>[] }>(`/api/table/${schema}/${name}`);
  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading text="Загружаем строки…" />;
  return <Rows columns={data.columns} rows={data.rows} />;
}

export function Rows({ columns, rows }: { columns: string[]; rows: Record<string, unknown>[] }) {
  return (
    <div className="table-wrap" style={{ maxHeight: 320 }}>
      <table>
        <thead><tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>{columns.map((c) => <td key={c} className="mono">{fmt(r[c])}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
const fmt = (v: unknown) => (v === null || v === undefined ? "∅" : typeof v === "object" ? JSON.stringify(v) : String(v).slice(0, 60));

function Detail({ sel, data }: { sel: NonNullable<Sel>; data: ModelData }) {
  if (sel.layer === "raw") {
    const r = data.raw.find((x) => x.raw === sel.name)!;
    const targets = data.core.filter((c) => r.core.includes(c.name));
    const bal = data.balance.filter((b) => b.check_name.includes(sel.name.replace("order_", "")) || b.check_name.includes(sel.name));
    return (
      <div className="card detail">
        <div className="eyebrow">raw · {sel.name}</div>
        <h3>{nf(r.rows)} строк, все колонки — текст</h3>
        <p className="sub">Что делает сборка: {r.rule}.</p>
        <div className="row" style={{ marginBottom: 14 }}>
          {targets.map((t) => <span key={t.name} className="pill acc">→ core.{t.name} · {nf(t.rows)}</span>)}
        </div>
        {bal.length > 0 && (
          <div className="row" style={{ marginBottom: 14 }}>
            {bal.slice(0, 4).map((b) => (
              <span key={b.check_name} className={"pill " + (b.ok ? "ok" : "no")} title={`${b.expected} → ${b.actual}`}>{b.ok ? "✓" : "✗"} {b.check_name}</span>
            ))}
          </div>
        )}
        <Preview schema="raw" name={sel.name} />
      </div>
    );
  }
  if (sel.layer === "core") {
    const c = data.core.find((x) => x.name === sel.name)!;
    const users = data.mart.filter((m) => m.uses.map(norm).includes("core." + sel.name));
    return (
      <div className="card detail">
        <div className="eyebrow">core · {sel.name}</div>
        <h3>{GRAIN[c.name] || c.comment}</h3>
        <p className="sub">{nf(c.rows)} строк · в базе записано: «{c.comment}»</p>
        <div className="grid g2" style={{ marginBottom: 14 }}>
          <div>
            <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>Ключ и связи (база их охраняет)</div>
            {c.keys.length === 0 && <div className="dim">ключей нет — служебная таблица</div>}
            {c.keys.map((k) => <div key={k.def} className="mono" style={{ marginBottom: 4 }}><span className={k.type === "p" ? "acc" : "muted"}>{k.type === "p" ? "PK" : "FK"}</span> {k.def}</div>)}
          </div>
          <div>
            <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>Кто читает эту таблицу в mart</div>
            <div className="row">{users.length ? users.map((u) => <span key={u.name} className="pill">{u.name}</span>) : <span className="dim">напрямую — никто</span>}</div>
            <div className="muted" style={{ fontSize: 12, margin: "12px 0 6px" }}>Колонки</div>
            <div className="mono dim" style={{ lineHeight: 1.7 }}>{c.columns.map((x) => x.name).join(" · ")}</div>
          </div>
        </div>
        <Preview schema="core" name={sel.name} />
      </div>
    );
  }
  const m = data.mart.find((x) => x.name === sel.name)!;
  return <MartDetail m={m} />;
}

function MartDetail({ m }: { m: ModelData["mart"][number] }) {
  const { data, error } = useApi<{ sql: string | null; rows: Record<string, unknown>[] }>(`/api/view/${m.name}`);
  return (
    <div className="card detail">
      <div className="eyebrow">mart · {m.name}</div>
      <h3>{MART[m.name] || m.name}</h3>
      <p className="sub">
        {m.kind === "view" ? "Витрина ничего не хранит: при каждом запросе считает заново по модели. " : "Таблица паспортов. "}
        Читает: {m.uses.length ? m.uses.join(", ") : "—"}
      </p>
      {error && <ErrorBox error={error} />}
      {!data && !error && <Loading text="Выполняем витрину…" />}
      {data && (
        <div className="grid g2">
          {data.sql && (
            <div>
              <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>SQL витрины (из базы)</div>
              <pre className="sql">{data.sql.trim()}</pre>
            </div>
          )}
          <div className={data.sql ? "" : "span2"}>
            <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>Результат (первые строки)</div>
            <Rows columns={data.rows[0] ? Object.keys(data.rows[0]) : []} rows={data.rows} />
          </div>
        </div>
      )}
    </div>
  );
}

const SAMPLE = "f41397c4cf4c8a67f5f540472acbfe4f";
type TraceData = { raw: Record<string, Record<string, unknown>[]>; core: Record<string, Record<string, unknown>[]>; mart: Record<string, Record<string, unknown>[]> };

function Trace() {
  const [input, setInput] = useState(SAMPLE);
  const [id, setId] = useState(SAMPLE);
  const { data, error } = useApi<TraceData>(`/api/trace/${id}`);
  return (
    <div className="card detail">
      <div className="eyebrow">Сквозной путь одного заказа</div>
      <h3>Как один заказ проходит raw → core → mart</h3>
      <p className="sub">
        Пример — настоящий заказ: 3 товара от 2 продавцов, рассрочка, опоздание на 5 дней и отзыв на 1 звезду. Можно вставить любой order_id.
      </p>
      <div className="row" style={{ marginBottom: 16 }}>
        <input className="text" value={input} onChange={(e) => setInput(e.target.value.trim())} />
        <button className="chip-btn" onClick={() => setId(input)}>Проследить</button>
      </div>
      {error && <ErrorBox error={error} />}
      {data && (
        <div className="trace">
          {(["raw", "core", "mart"] as const).map((layer) => (
            <div key={layer}>
              <div className={"layer-h " + (layer === "core" ? "chrome" : "")}>{layer === "raw" ? "raw — как пришло (текст)" : layer === "core" ? "core — модель (типы, ключи)" : "mart — посчитано для ответов"}</div>
              {Object.entries(data[layer]).map(([t, rows]) => (
                <div key={t} className="trace-block">
                  <div className="t">{t} · {rows.length} {rows.length === 1 ? "строка" : "строк"}</div>
                  {rows.slice(0, 3).map((r, i) => (
                    <div key={i} className="kv" style={{ marginBottom: rows.length > 1 ? 8 : 0 }}>
                      {Object.entries(r).filter(([k]) => !k.startsWith("_")).map(([k, v]) => (
                        <FragmentKV key={k} k={k} v={v} />
                      ))}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function FragmentKV({ k, v }: { k: string; v: unknown }) {
  return (
    <>
      <span className="k">{k}</span>
      <span className="v">{fmt(v)}</span>
    </>
  );
}
