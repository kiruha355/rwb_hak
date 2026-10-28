import { ReactNode, useEffect, useState } from "react";
import { adaptBlockB, BlockBData } from "./block-b/contract";
import { BlockBContent } from "./block-b/components";
import "./block-b/styles.css";

export type BlockBState = { status: "loading" } | { status: "legacy" } | { status: "error"; message: string } | { status: "ready"; data: BlockBData };

// Independent of Q1–Q5 and business filters: these views cover the whole snapshot.
export default function BlockBAnswers({ fallback }: { fallback?: ReactNode }) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<BlockBState>({ status: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    const load = async () => {
      try {
        const response = await fetch("/api/answers-block-b", { signal: controller.signal });
        if (response.status === 404 && fallback) {
          if (!controller.signal.aborted) setState({ status: "legacy" });
          return;
        }
        if (!response.ok) {
          if (response.status === 404) throw new Error("Раздел Q6–Q10 ещё не подключён к API (HTTP 404).");
          throw new Error(`API не вернул данные Q6–Q10 (HTTP ${response.status}). Проверьте доступность новых витрин.`);
        }
        const data = adaptBlockB(await response.json());
        if (!controller.signal.aborted) setState({ status: "ready", data });
      } catch (error) {
        if (!controller.signal.aborted) setState({ status: "error", message: error instanceof Error ? error.message : "Не удалось загрузить Q6–Q10." });
      }
    };
    void load();
    return () => controller.abort();
  }, [attempt, !!fallback]);
  // One existing block-B slot: keep the colleague's UI as a compatibility path.
  // Its reduced API cannot supply the missing denominators or coverage counters.
  if (state.status === "legacy") return <>
    <p className="bb-compat">Дополнительные данные об охвате Q6–Q10 пока недоступны. Показана существующая версия отчёта.</p>
    {fallback}
  </>;
  return <BlockBView state={state} retry={() => setAttempt(v => v + 1)} />;
}

// Pure view exported for deterministic visual QA, including loading/error states.
export function BlockBView({ state, retry }: { state: BlockBState; retry: () => void }) {
  return <section className="block-b" aria-label="Блок Б: вопросы Q6–Q10" aria-busy={state.status === "loading"}>
    <p className="bb-scope">Весь снимок данных; платежи по штатам — покупки 2018 года. Фильтры месяца, категории и штата из других отчётов здесь не применяются. Варианты расчёта показаны отдельно.</p>
    {state.status === "loading" && <div className="bb-loading" role="status">Загрузка Q6–Q10…</div>}
    {state.status === "error" && <div className="bb-error" role="alert"><p>{state.message}</p><button className="btn" type="button" onClick={retry}>Повторить загрузку</button></div>}
    {state.status === "ready" && <BlockBContent data={state.data} />}
  </section>;
}
