import { useState } from "react";
import { ErrorBox, Loading, PageHead, useApi } from "../lib";

type Metric = {
  name: string; grain: string; formula_sql: string; status_rule: string; time_basis: string; window: string;
  denominator: string; null_policy: string; unit: string; additive_over: string; non_additive_over: string; description: string;
};

export default function Metrics() {
  const { data, error } = useApi<Metric[]>("/api/metrics");
  const [q, setQ] = useState("");
  const list = (data || []).filter((m) => (m.name + m.description + m.formula_sql).toLowerCase().includes(q.toLowerCase()));
  return (
    <>
      <PageHead
        eyebrow="07 · Одна формула — в одном месте"
        title="Паспорта метрик"
        lead="Каждая метрика описана один раз: формула, уровень, какие статусы, окно, знаменатель и по каким срезам её можно складывать. Дашборд и ответы опираются на эти определения."
      />
      {error && <ErrorBox error={error} />}
      {!data && !error && <Loading />}
      {data && (
        <>
          <div className="search">
            <input className="text" placeholder="Поиск: revenue, late, buyers…" value={q} onChange={(e) => setQ(e.target.value)} />
            <span className="dim" style={{ marginLeft: 12, fontSize: 12 }}>{list.length} из {data.length}</span>
          </div>
          <div className="grid g2">
            {list.map((m) => (
              <div key={m.name} className="card">
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <h3 className="mono" style={{ fontSize: 14 }}>{m.name}</h3>
                  <span className="pill acc">уровень: {m.grain}</span>
                </div>
                <p className="sub" style={{ marginTop: 6 }}>{m.description}</p>
                <pre className="sql" style={{ maxHeight: 90, whiteSpace: "pre-wrap" }}>{m.formula_sql}</pre>
                <div className="kv" style={{ marginTop: 10 }}>
                  <span className="k">статусы</span><span className="v">{m.status_rule}</span>
                  <span className="k">время</span><span className="v">{m.time_basis} · {m.window}</span>
                  <span className="k">знаменатель</span><span className="v">{m.denominator}</span>
                  <span className="k">пропуски</span><span className="v">{m.null_policy}</span>
                  <span className="k good">складывается</span><span className="v">{m.additive_over || "—"}</span>
                  <span className="k bad">не складывается</span><span className="v">{m.non_additive_over || "—"}</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}
