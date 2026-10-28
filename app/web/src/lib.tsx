import { useEffect, useState } from "react";
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
export const monthLabel = (m: string) => {
  const [y, mm] = m.split("-");
  return ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"][Number(mm) - 1] + " " + y.slice(2);
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

export function useFilters() {
  const [sp, setSp] = useSearchParams();
  const f = {
    from: sp.get("from") || "2016-09",
    to: sp.get("to") || "2018-08",
    state: sp.get("state") || "",
    category: sp.get("category") || "",
  };
  const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v) as [string, string][]).toString();
  const set = (patch: Partial<typeof f>) => {
    const next = { ...f, ...patch };
    setSp(new URLSearchParams(Object.entries(next).filter(([, v]) => v) as [string, string][]), { replace: true });
  };
  return { f, qs, set };
}

export function Loading({ text = "Считаем по модели…" }: { text?: string }) {
  return (
    <div className="loading">
      <img src="/img/face_left.png" alt="" />
      {text}
    </div>
  );
}

export function ErrorBox({ error }: { error: string }) {
  return <div className="error">Не удалось получить данные: {error}. Запущен ли API (npm run dev в app/)?</div>;
}

export function PageHead({ eyebrow, title, lead, right }: { eyebrow: string; title: string; lead?: string; right?: React.ReactNode }) {
  return (
    <div className="page-head">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1 className="title chrome">{title}</h1>
        {lead && <p className="lead">{lead}</p>}
      </div>
      {right}
    </div>
  );
}

export function Kpi({ label, value, hint, formula, additive, tone, small }: {
  label: string; value: string; hint?: string; formula?: string; additive?: boolean; tone?: "bad" | "good" | "acc"; small?: boolean;
}) {
  const help = [formula, additive === undefined ? "" : additive ? "Можно складывать по срезам." : "Нельзя складывать по срезам — только пересчитывать."]
    .filter(Boolean)
    .join("\n");
  return (
    <div className={"card kpi" + (small ? " small" : "")}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <span className="label">{label}</span>
        {help && <span className="info" title={help}>i</span>}
      </div>
      <div className={"value " + (tone || "")}>{value}</div>
      {hint && <div className="hint">{hint}</div>}
    </div>
  );
}

export function Ring({ value, label, size = 132, color = "#63b3e3", track = "#eceef1" }: {
  value: number; label: string; size?: number; color?: string; track?: string;
}) {
  const r = size / 2 - 10;
  const c = 2 * Math.PI * r;
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeWidth={14} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={14} strokeLinecap="round"
          strokeDasharray={`${c * Math.max(0, Math.min(1, value))} ${c}`} style={{ transition: "stroke-dasharray .6s ease" }} />
      </svg>
      <div className="center">
        <b>{nf(value * 100, 0)}%</b>
        <span>{label}</span>
      </div>
    </div>
  );
}
