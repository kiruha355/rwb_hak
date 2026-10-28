import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { useApi } from "./lib";
import Summary from "./pages/Summary";
import Delivery from "./pages/Delivery";
import Commerce from "./pages/Commerce";
import DataPage from "./pages/DataPage";

const WORK = [
  { to: "/", label: "Сводка" },
  { to: "/delivery", label: "Доставка" },
  { to: "/sales", label: "Продажи" },
];

type Meta = { build: { built_at: string; checks: number; passed: number; failed_errors: number } };

export default function App() {
  const { data } = useApi<Meta>("/api/meta");
  const { search } = useLocation();
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">
          <img src="/img/face_left.png" alt="" />
          <div>
            <div className="name">Capibara</div>
            <div className="team">команда «Скажите "мяу"»</div>
          </div>
        </div>
        <nav className="nav">
          <div className="sect">Работа</div>
          {WORK.map((n) => (
            <NavLink key={n.to} to={n.to + search} end={n.to === "/"}>
              <span className="dot" />
              {n.label}
            </NavLink>
          ))}
          <div className="sect" style={{ marginTop: 18 }}>Для аналитиков</div>
          <NavLink to="/data">
            <span className="dot" />
            Данные и модель
          </NavLink>
        </nav>
        <div className="side-foot">
          {data && (
            <div className="status">
              <span className="ok" />
              <span>Обновлено {new Date(data.build.built_at).toLocaleDateString("ru-RU")} · {data.build.failed_errors === 0 ? "проверки пройдены" : "есть ошибки"}</span>
            </div>
          )}
        </div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Summary />} />
          <Route path="/delivery" element={<Delivery />} />
          <Route path="/sales" element={<Commerce />} />
          <Route path="/data" element={<DataPage />} />
        </Routes>
      </main>
    </div>
  );
}
