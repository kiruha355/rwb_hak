import { ErrorBox, Loading, PageHead, nf, useApi } from "../lib";

type Checks = {
  summary: { grp: string; severity: string; total: number; passed: number }[];
  failed: { check_name: string; check_group: string; severity: string; expected: string; actual: string }[];
  issues: { issue_code: string; entity_type: string; n: number; example?: { entity_key: unknown; details: unknown } }[];
  balance: { check_name: string; expected: string; actual: string; ok: boolean }[];
};

const GROUP: Record<string, string> = {
  key: "ключи уникальны", field: "каждое поле перенесено", balance: "строки raw = core", fk: "связи не ведут в пустоту",
  money: "суммы денег сходятся", calendar: "календарь без дыр", coverage: "покрытие", typing: "типы данных",
  fd: "повторы отзывов совпадают", quality: "качество данных",
};
const ISSUE: Record<string, string> = {
  carrier_before_approval: "передан перевозчику раньше подтверждения оплаты",
  order_without_items: "заказ без товаров",
  order_without_reviews: "заказ без отзыва",
  payment_item_exact_mismatch: "платёж ≠ товары + доставка (точно)",
  product_missing_category: "товар без категории",
  product_name_lenght_missing: "нет длины названия",
  product_photos_qty_missing: "нет числа фото",
  product_description_lenght_missing: "нет длины описания",
  carrier_before_purchase: "передан перевозчику раньше покупки",
  delivery_before_carrier: "вручён раньше передачи перевозчику",
  delivered_missing_approval_date: "доставлен, но нет даты подтверждения",
  payment_zero_value: "платёж на 0",
  delivered_missing_delivery_date: "доставлен, но нет даты вручения",
  delivery_date_on_other_status: "дата вручения у недоставленного",
  product_weight_g_zero: "вес товара 0",
  unrecognized_payment_type: "неизвестный способ оплаты",
  payment_nonpositive_installments: "рассрочка на 0 частей",
  category_missing_translation: "категория без перевода",
  order_without_payments: "заказ без платежа",
};

export default function Quality() {
  const { data, error } = useApi<Checks>("/api/checks");
  const total = data?.summary.reduce((s, x) => s + x.total, 0) || 0;
  const errors = data?.summary.filter((x) => x.severity === "error") || [];
  const errOk = errors.reduce((s, x) => s + x.passed, 0);
  const errTotal = errors.reduce((s, x) => s + x.total, 0);
  return (
    <>
      <PageHead
        eyebrow="05 · Как мы убедились, что ничего не потеряли"
        title="Проверки и качество"
        lead="Сборка сама сверяет сырые данные с моделью. Ошибка в сборке — откат всего. Странности в исходных данных — не удаляем, а записываем в журнал."
      />
      {error && <ErrorBox error={error} />}
      {!data && !error && <Loading />}
      {data && (
        <>
          <div className="hero">
            <div className="grid g2">
              <div className="card kpi">
                <span className="label">Блокирующих проверок</span>
                <div className={"value " + (errOk === errTotal ? "good" : "bad")}>{errOk} / {errTotal}</div>
                <div className="hint">не сошлась хоть одна — вся сборка откатывается</div>
              </div>
              <div className="card kpi">
                <span className="label">Всего самопроверок</span>
                <div className="value chrome">{nf(total)}</div>
                <div className="hint">ключи, поля, связи, деньги, календарь, отзывы</div>
              </div>
              <div className="card span2">
                <h3>Группы проверок</h3>
                <div className="grid g2" style={{ marginTop: 10 }}>
                  {data.summary.map((g) => (
                    <div key={g.grp + g.severity} className="row" style={{ justifyContent: "space-between" }}>
                      <span>{GROUP[g.grp] || g.grp} <span className="dim">· {g.severity === "error" ? "блокирует" : "предупреждает"}</span></span>
                      <span className={"pill " + (g.passed === g.total ? "ok" : g.severity === "error" ? "no" : "acc")}>{g.passed}/{g.total}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="paw-photo">
              <img src="/img/leopards.jpg" alt="Два барса" />
              <span className="paw" style={{ left: "23.5%", top: "70%" }}>raw</span>
              <span className="paw" style={{ left: "77.5%", top: "70%" }}>= core</span>
            </div>
          </div>

          <div className="grid g2">
            <div className="card">
              <h3>Баланс raw ↔ core и деньги</h3>
              <p className="sub">Ожидали — получили. Количества и суммы каждого денежного поля.</p>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Проверка</th><th className="n">Ожидали</th><th className="n">Получили</th><th></th></tr></thead>
                  <tbody>
                    {data.balance.map((b) => (
                      <tr key={b.check_name}>
                        <td className="mono">{b.check_name}</td>
                        <td className="n mono">{b.expected?.slice(0, 18)}</td>
                        <td className="n mono">{b.actual?.slice(0, 18)}</td>
                        <td className={b.ok ? "good" : "bad"}>{b.ok ? "✓" : "✗"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="card">
              <h3>Журнал аномалий источника</h3>
              <p className="sub">Предупреждения: строки не удалены, а помечены. Заказ выпадает только из той метрики, которую портит.</p>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Что найдено</th><th>Объект</th><th className="n">Случаев</th></tr></thead>
                  <tbody>
                    {data.issues.map((i) => (
                      <tr key={i.issue_code + i.entity_type} title={JSON.stringify(i.example?.entity_key)}>
                        <td>{ISSUE[i.issue_code] || i.issue_code}</td>
                        <td className="dim">{i.entity_type}</td>
                        <td className="n">{nf(i.n)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          {data.failed.length > 0 && (
            <div className="card detail">
              <h3>Сработавшие предупреждения</h3>
              <p className="sub">Не блокируют сборку — сообщают о данных.</p>
              {data.failed.map((f) => <div key={f.check_name} className="mono">{f.check_name}: ожидали {f.expected}, получили {f.actual}</div>)}
            </div>
          )}
        </>
      )}
    </>
  );
}
