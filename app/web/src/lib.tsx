import { ReactNode, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

export const nf = (v: number | null | undefined, d = 0) =>
  v === null || v === undefined || Number.isNaN(v)
    ? "—"
    : Number(v).toLocaleString("ru-RU", { minimumFractionDigits: d, maximumFractionDigits: d });
export const pct = (v: number | null | undefined, d = 1) => (v === null || v === undefined ? "—" : nf(v * 100, d) + " %");
export const money = (v: number | null | undefined) => {
  if (v === null || v === undefined) return "—";
  if (Math.abs(v) >= 1e6) return nf(v / 1e6, 2) + " млн";
  if (Math.abs(v) >= 1e3) return nf(v / 1e3, 1) + " тыс.";
  return nf(v, 2);
};
const MONTHS = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];
export const monthLabel = (m: string) => {
  const [y, mm] = m.split("-");
  return MONTHS[Number(mm) - 1] + " " + y.slice(2);
};

export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!path) return;
    let alive = true;
    setLoading(true);
    setError(null);
    fetch(path)
      .then(async (r) => {
        const j = await r.json();
        if (!r.ok) throw new Error(j.error || r.statusText);
        return j;
      })
      .then((j) => alive && setData(j))
      .catch((e) => alive && setError(String(e.message || e)))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [path]);
  return { data, error, loading };
}

export const DEFAULT_PERIOD = { from: "2016-09", to: "2018-08" };

export function useFilters() {
  const [sp, setSp] = useSearchParams();
  const f = {
    from: sp.get("from") || DEFAULT_PERIOD.from,
    to: sp.get("to") || DEFAULT_PERIOD.to,
    state: sp.get("state") || "",
    category: sp.get("category") || "",
  };
  const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v) as [string, string][]).toString();
  // other URL params (view settings like ?metric=) are kept when filters change
  const set = (patch: Partial<typeof f>) => {
    const next = new URLSearchParams(sp);
    Object.entries(patch).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    setSp(next, { replace: true });
  };
  return { f, qs, set };
}

// View settings live in the URL, so a copied link reproduces the exact view.
export function useViewParam<T extends string>(name: string, def: T): [T, (v: T) => void] {
  const [sp, setSp] = useSearchParams();
  const v = (sp.get(name) as T) || def;
  const set = (nv: T) => {
    const next = new URLSearchParams(sp);
    nv === def ? next.delete(name) : next.set(name, nv);
    setSp(next, { replace: true });
  };
  return [v, set];
}

export function Loading({ text = "Загружаю данные…" }: { text?: string }) {
  return (
    <div className="loading">
      <span className="spin" />
      {text}
    </div>
  );
}

export function ErrorBox({ error }: { error: string }) {
  return <div className="error">Не удалось получить данные: {error}. Проверьте, что API запущен (npm run dev в app/).</div>;
}

// Section heading inside the analyst pages.
export function PageHead({ title, lead }: { eyebrow?: string; title: string; lead?: string; right?: ReactNode }) {
  return (
    <div className="page-head">
      <h2 style={{ fontSize: 16, fontWeight: 600 }}>{title}</h2>
      {lead && <p className="lead">{lead}</p>}
    </div>
  );
}

// ---------- KPI strip ----------
export type KpiItem = { label: string; value: string; sub?: string; help?: string; spark?: ReactNode };
export function KpiStrip({ items }: { items: KpiItem[] }) {
  return (
    <div className="kpis">
      {items.map((k) => (
        <div className="k" key={k.label}>
          <div className="l">
            <span>{k.label}</span>
            {k.help && <span className="info" title={k.help}>i</span>}
          </div>
          <div className="v">{k.value}</div>
          {k.sub && <div className="s" title={k.sub}>{k.sub}</div>}
          {k.spark && <div className="spark">{k.spark}</div>}
        </div>
      ))}
    </div>
  );
}

// ---------- panel ----------
export function Panel({ title, hint, controls, csv, footer, flush, children, className = "" }: {
  title: string; hint?: string; controls?: ReactNode; csv?: Csv; footer?: ReactNode; flush?: boolean; children: ReactNode; className?: string;
}) {
  return (
    <section className={"panel " + className}>
      <div className="panel-h">
        <div>
          <h3>{title}</h3>
          {hint && <div className="hint">{hint}</div>}
        </div>
        <div className="ctrl">
          {controls}
          {csv && (
            <button className="btn sm" onClick={() => downloadCsv(csv)} title="Скачать данные этого блока для Excel">
              <Icon name="download" /> CSV
            </button>
          )}
        </div>
      </div>
      <div className={"panel-b" + (flush ? " flush" : "")}>{children}</div>
      {footer && <div className="panel-f">{footer}</div>}
    </section>
  );
}

export function Seg<T extends string>({ value, options, onChange, small = true }: {
  value: T; options: { id: T; label: string }[]; onChange: (v: T) => void; small?: boolean;
}) {
  return (
    <div className={"seg" + (small ? " sm" : "")}>
      {options.map((o) => (
        <button key={o.id} className={o.id === value ? "on" : ""} onClick={() => onChange(o.id)}>{o.label}</button>
      ))}
    </div>
  );
}

// ---------- CSV export (Excel-friendly: BOM, ";" separator, decimal comma) ----------
export type Csv = { name: string; columns: { key: string; label: string }[]; rows: Record<string, any>[] };
export function downloadCsv({ name, columns, rows }: Csv) {
  const cell = (v: any) => {
    if (v === null || v === undefined) return "";
    const s = typeof v === "number" ? String(v).replace(".", ",") : String(v);
    return /[;"\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const text = [columns.map((c) => cell(c.label)).join(";"), ...rows.map((r) => columns.map((c) => cell(r[c.key])).join(";"))].join("\r\n");
  const url = URL.createObjectURL(new Blob(["﻿" + text], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  const q = new URLSearchParams(window.location.search);
  a.href = url;
  a.download = `${name}_${q.get("from") || DEFAULT_PERIOD.from}_${q.get("to") || DEFAULT_PERIOD.to}${q.get("state") ? "_" + q.get("state") : ""}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ---------- sortable table ----------
export type Col<T> = {
  key: string; label: string; num?: boolean; bar?: boolean;
  fmt?: (row: T) => ReactNode; value?: (row: T) => number | string | null;
};
export function DataTable<T extends Record<string, any>>({ cols, rows, initialSort, onRow, active, maxHeight = 440, total, limit }: {
  cols: Col<T>[]; rows: T[]; initialSort?: { key: string; desc: boolean }; onRow?: (r: T) => void;
  active?: (r: T) => boolean; maxHeight?: number; total?: Partial<Record<string, ReactNode>>; limit?: number;
}) {
  const [sort, setSort] = useState(initialSort || null);
  const [all, setAll] = useState(false);
  const val = (c: Col<T>, r: T) => (c.value ? c.value(r) : r[c.key]);
  const sorted = useMemo(() => {
    if (!sort) return rows;
    const c = cols.find((x) => x.key === sort.key);
    if (!c) return rows;
    return [...rows].sort((a, b) => {
      const va = val(c, a), vb = val(c, b);
      if (va === vb) return 0;
      if (va === null || va === undefined) return 1;
      if (vb === null || vb === undefined) return -1;
      const r = typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb), "ru");
      return sort.desc ? -r : r;
    });
  }, [rows, sort, cols]);
  const shown = limit && !all ? sorted.slice(0, limit) : sorted;
  const maxes: Record<string, number> = {};
  cols.filter((c) => c.bar).forEach((c) => (maxes[c.key] = Math.max(...rows.map((r) => Number(val(c, r)) || 0), 0)));
  const click = (c: Col<T>) =>
    setSort((s) => (s && s.key === c.key ? { key: c.key, desc: !s.desc } : { key: c.key, desc: !!c.num }));
  return (
    <>
      <div className="table-wrap" style={{ maxHeight }}>
        <table>
          <thead>
            <tr>
              {cols.map((c) => (
                <th key={c.key} className={"sort" + (c.num ? " n" : "")} onClick={() => click(c)}>
                  {c.label}
                  {sort?.key === c.key && <span className="arr">{sort.desc ? "↓" : "↑"}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((r, i) => (
              <tr key={i} className={(onRow ? "click " : "") + (active?.(r) ? "hl" : "")} onClick={onRow ? () => onRow(r) : undefined}>
                {cols.map((c) => {
                  const content = c.fmt ? c.fmt(r) : r[c.key];
                  return (
                    <td key={c.key} className={c.num ? "n" : ""}>
                      {c.bar ? (
                        <div className="cellbar">
                          {content}
                          <div className="tr"><div className="fl" style={{ width: (maxes[c.key] ? (Number(val(c, r)) / maxes[c.key]) * 100 : 0) + "%" }} /></div>
                        </div>
                      ) : content}
                    </td>
                  );
                })}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={cols.length} className="empty">Нет данных в этом срезе</td></tr>
            )}
          </tbody>
          {total && (
            <tfoot>
              <tr className="total">
                {cols.map((c) => <td key={c.key} className={c.num ? "n" : ""}>{total[c.key] ?? ""}</td>)}
              </tr>
            </tfoot>
          )}
        </table>
      </div>
      {limit !== undefined && rows.length > limit && (
        <div className="tbl-foot">
          <span>Показано {nf(shown.length)} из {nf(rows.length)}</span>
          <button className="btn ghost sm" onClick={() => setAll(!all)}>{all ? "Свернуть" : "Показать все"}</button>
        </div>
      )}
    </>
  );
}

// ---------- icons (plain strokes, no icon library) ----------
const PATHS: Record<string, string> = {
  overview: "M3 13h4v8H3zM10 8h4v13h-4zM17 3h4v18h-4z",
  sales: "M3 7h18l-2 11H5L3 7zm5 0V5a4 4 0 0 1 8 0v2",
  delivery: "M2 6h12v10H2zM14 10h4l3 3v3h-7zM6 19a2 2 0 1 0 0-.01M17 19a2 2 0 1 0 0-.01",
  data: "M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zm0 0v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3",
  link: "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
  download: "M12 3v12m0 0l-4-4m4 4l4-4M4 17v3h16v-3",
  print: "M6 9V3h12v6M6 18H4v-7h16v7h-2M7 14h10v7H7z",
};
export function Icon({ name }: { name: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      <path d={PATHS[name]} />
    </svg>
  );
}
