# Дашборд Capibara (HTML)

Реализация [концепции дашборда](../docs/submission/dashboard-concept.md) на HTML вместо Streamlit
(решение — [implementation-brief §10](../docs/implementation-brief-20261028.md)). Без сервера и зависимостей.

```sh
RWB_RAW_RELOAD_PAUSED=1 RWB_DB_MODE=docker make build   # core + mart из raw
RWB_DB_MODE=docker make dashboard                       # mart -> dashboard/data.js
open dashboard/index.html
```

- `export.sql` — одна read-only транзакция по `mart.v_orders`, `v_order_delivery_variants`, `v_order_items`,
  `v_payment_reconciliation`, `metric_definitions`, `core.data_issues` и ответам `mart.q01…q05`. `raw` не читается.
- `data.js` — сгенерирован, строки заказов и позиций в колоночном виде (~11 МБ). Страница пересчитывает
  показатели при любом фильтре: доли, перцентили и distinct-счёты не складываются из готовых агрегатов.
- Вкладка «Качество данных и сверка» сравнивает пересчёт страницы с SQL-ответами из той же выгрузки;
  бейдж «сверка с SQL» в шапке показывает итог (на выгрузке 2026-10-28: 14 из 14).

`sample/` — предыдущая версия W-16 (Mput13): тот же HTML на 24 синтетических заказах с импортом JSON
через `sample/export_data.py`. Сохранена без изменений логики, пути поправлены под новую папку.
