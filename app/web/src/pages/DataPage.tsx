import { useSearchParams } from "react-router-dom";
import Model from "./Model";
import Quality from "./Quality";
import Answers from "./Answers";
import Metrics from "./Metrics";

const TABS = [
  { id: "model", label: "Как устроена модель", el: <Model /> },
  { id: "checks", label: "Проверки и качество", el: <Quality /> },
  { id: "answers", label: "Ответы Q1–Q5", el: <Answers /> },
  { id: "metrics", label: "Формулы метрик", el: <Metrics /> },
];

export default function DataPage() {
  const [sp, setSp] = useSearchParams();
  const tab = TABS.find((t) => t.id === sp.get("tab")) || TABS[0];
  return (
    <>
      <div className="seg">
        {TABS.map((t) => (
          <button key={t.id} className={t.id === tab.id ? "on" : ""} onClick={() => setSp({ tab: t.id }, { replace: true })}>
            {t.label}
          </button>
        ))}
      </div>
      {tab.el}
    </>
  );
}
