import { ReactNode, useState } from "react";
import Filters from "./Filters";
import { Icon } from "./lib";

// ---------- page frame: title, purpose, filters, actions ----------
export default function Page({ title, lead, filters = true, category = true, tabs, children }: {
  title: string; lead: string; filters?: boolean; category?: boolean; tabs?: ReactNode; children: ReactNode;
}) {
  const [toast, setToast] = useState("");
  const copy = () => {
    navigator.clipboard?.writeText(window.location.href).then(() => {
      setToast("Ссылка на этот вид скопирована");
      setTimeout(() => setToast(""), 1800);
    });
  };
  return (
    <>
      <div className="topbar">
        <div className="head">
          <div>
            <h1 className="title">{title}</h1>
            <p className="lead">{lead}</p>
          </div>
          <div className="actions">
            <button className="btn" onClick={copy} title="Ссылка сохраняет фильтры и настройки графиков">
              <Icon name="link" /> Ссылка на вид
            </button>
            <button className="btn" onClick={() => window.print()} title="Печать или сохранение страницы в PDF">
              <Icon name="print" /> PDF
            </button>
          </div>
        </div>
        {filters ? <Filters category={category} /> : <div style={{ height: 4 }} />}
        {tabs}
      </div>
      <div className="content">{children}</div>
      {toast && <div className="toast">{toast}</div>}
    </>
  );
}
