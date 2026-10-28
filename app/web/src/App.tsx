import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { Icon, useApi } from "./lib";
import Summary from "./pages/Summary";
import Delivery from "./pages/Delivery";
import Commerce from "./pages/Commerce";
import DataPage from "./pages/DataPage";

const WORK = [
  { to: "/", icon: "overview", label: "Обзор", desc: "главные цифры и динамика" },
  { to: "/sales", icon: "sales", label: "Продажи", desc: "категории, продавцы, оплата" },
  { to: "/delivery", icon: "delivery", label: "Доставка", desc: "сроки, опоздания, оценки" },
];

type Meta = { months: string[]; build: { built_at: string; checks: number; passed: number; failed_errors: number } };

// keep only the business filters when switching pages; view settings belong to a page
const carry = (search: string) => {
  const sp = new URLSearchParams(search);
  const keep = new URLSearchParams();
  ["from", "to", "state", "category"].forEach((k) => sp.get(k) && keep.set(k, sp.get(k)!));
  const s = keep.toString();
  return s ? "?" + s : "";
};

export default function App() {
  const { data } = useApi<Meta>("/api/meta");
  const { search } = useLocation();
  const b = data?.build;
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">
          <img src="/img/face_left.png" alt="" />
          <div>
            <div className="name">Скажите «мяу»</div>
            <div className="team">Аналитика маркетплейса</div>
          </div>
        </div>
        <nav className="nav">
          <div className="sect">Отчёты</div>
          {WORK.map((n) => (
            <NavLink key={n.to} to={n.to + carry(search)} end={n.to === "/"}>
              <Icon name={n.icon} />
              <span>{n.label}<span className="desc">{n.desc}</span></span>
            </NavLink>
          ))}
          <div className="sect">Для аналитиков</div>
          <NavLink to="/data">
            <Icon name="data" />
            <span>Данные и модель<span className="desc">откуда цифры, проверки</span></span>
          </NavLink>
        </nav>
        <div className="side-foot">
          <div className="h">Источник данных</div>
          {b ? (
            <>
              <div className="kvrow"><span>Заказы</span><b>09.2016 — 10.2018</b></div>
              <div className="kvrow"><span>Модель собрана</span><b>{new Date(b.built_at).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}</b></div>
              <div className="kvrow">
                <span title={`${b.checks} проверок модели; ${b.checks - b.passed} предупреждений`}>Проверки ({b.checks})</span>
                <Link to="/data?tab=checks">
                  <span className={"status-dot" + (b.failed_errors ? " err" : "")} />
                  {b.failed_errors ? `ошибок: ${b.failed_errors}` : "ошибок нет"}
                </Link>
              </div>
            </>
          ) : <span className="dim">загрузка…</span>}
        </div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Summary />} />
          <Route path="/sales" element={<Commerce />} />
          <Route path="/delivery" element={<Delivery />} />
          <Route path="/data" element={<DataPage />} />
        </Routes>
      </main>
    </div>
  );
}
