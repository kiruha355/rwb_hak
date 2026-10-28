import { DEFAULT_PERIOD, useApi, useFilters, monthLabel } from "./lib";

type Meta = { states: { state: string; orders: number }[]; categories: { key: string; name: string }[]; months: string[] };

const PRESETS = [
  { id: "all", label: "Весь период", from: DEFAULT_PERIOD.from, to: DEFAULT_PERIOD.to },
  { id: "2017", label: "2017", from: "2017-01", to: "2017-12" },
  { id: "2018", label: "2018 (янв–авг)", from: "2018-01", to: "2018-08" },
];

export default function Filters({ category = true }: { category?: boolean }) {
  const { f, set } = useFilters();
  const { data } = useApi<Meta>("/api/meta");
  const months = data?.months || [];
  const preset = PRESETS.find((p) => p.from === f.from && p.to === f.to)?.id;
  const catName = data?.categories.find((c) => c.key === f.category)?.name || f.category;
  const dirty = f.from !== DEFAULT_PERIOD.from || f.to !== DEFAULT_PERIOD.to || f.state || f.category;
  return (
    <div className="toolbar">
      <div className="seg">
        {PRESETS.map((p) => (
          <button key={p.id} className={preset === p.id ? "on" : ""} onClick={() => set({ from: p.from, to: p.to })}>{p.label}</button>
        ))}
      </div>
      <label className="field">
        <span>с</span>
        <select value={f.from} onChange={(e) => set({ from: e.target.value })}>
          {months.map((m) => <option key={m} value={m} disabled={m > f.to}>{monthLabel(m)}</option>)}
        </select>
      </label>
      <label className="field">
        <span>по</span>
        <select value={f.to} onChange={(e) => set({ to: e.target.value })}>
          {months.map((m) => <option key={m} value={m} disabled={m < f.from}>{monthLabel(m)}</option>)}
        </select>
      </label>
      <label className="field">
        <span>Штат покупателя</span>
        <select value={f.state} onChange={(e) => set({ state: e.target.value })}>
          <option value="">все</option>
          {data?.states.map((s) => <option key={s.state} value={s.state}>{s.state} · {s.orders.toLocaleString("ru-RU")} заказов</option>)}
        </select>
      </label>
      {category && (
        <label className="field">
          <span>Категория</span>
          <select value={f.category} onChange={(e) => set({ category: e.target.value })}>
            <option value="">все</option>
            {data?.categories.map((c) => <option key={c.key} value={c.key}>{c.name}</option>)}
          </select>
        </label>
      )}
      <div className="chips">
        {f.state && <span className="chip">Штат: {f.state}<button onClick={() => set({ state: "" })} title="Убрать">×</button></span>}
        {f.category && <span className="chip">Категория: {catName}<button onClick={() => set({ category: "" })} title="Убрать">×</button></span>}
      </div>
      {dirty && (
        <button className="btn ghost sm" onClick={() => set({ ...DEFAULT_PERIOD, state: "", category: "" })}>Сбросить фильтры</button>
      )}
    </div>
  );
}
