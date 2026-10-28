import { useApi, useFilters, monthLabel } from "./lib";

type Meta = { states: { state: string; orders: number }[]; categories: { key: string; name: string }[]; months: string[] };

export default function Filters({ category = true }: { category?: boolean }) {
  const { f, set } = useFilters();
  const { data } = useApi<Meta>("/api/meta");
  const months = data?.months || [];
  return (
    <div className="filters">
      <label>
        Период с
        <select value={f.from} onChange={(e) => set({ from: e.target.value })}>
          {months.map((m) => (
            <option key={m} value={m} disabled={m > f.to}>{monthLabel(m)}</option>
          ))}
        </select>
      </label>
      <label>
        по
        <select value={f.to} onChange={(e) => set({ to: e.target.value })}>
          {months.map((m) => (
            <option key={m} value={m} disabled={m < f.from}>{monthLabel(m)}</option>
          ))}
        </select>
      </label>
      <label>
        Штат покупателя
        <select value={f.state} onChange={(e) => set({ state: e.target.value })}>
          <option value="">все</option>
          {data?.states.map((s) => (
            <option key={s.state} value={s.state}>{s.state} · {s.orders.toLocaleString("ru-RU")}</option>
          ))}
        </select>
      </label>
      {category && (
        <label>
          Категория
          <select value={f.category} onChange={(e) => set({ category: e.target.value })}>
            <option value="">все</option>
            {data?.categories.map((c) => (
              <option key={c.key} value={c.key}>{c.name}</option>
            ))}
          </select>
        </label>
      )}
      <button className="chip-btn" onClick={() => set({ from: "2016-09", to: "2018-08", state: "", category: "" })}>
        Сбросить
      </button>
      <span className="active-filters">Окно вопроса 1 по умолчанию: сен 2016 — авг 2018</span>
    </div>
  );
}
