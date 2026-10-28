# W-12 · Передача комплекта

**Предварительный комплект готов к review первого чекпоинта 13:30 МСК / 10:30 UTC.** Owned path: `docs/submission/**`, без правок вне него. Публикация адресно через W-01; Git index/add/commit/push/checkout/pull/reset/merge и PR не использовались. Новых делегатов, сервисов, Docker/VM, установок или тяжёлых fixtures не запускалось.

## Что открыть

- [Чекпоинт5–7 минут](checkpoint-1330.md): роли, точные команды, ожидаемые выводы, восемь решений и ответы жюри.
- [HTML-hub](index.html) и [HTML-показ из 12 разделов](presentation.html), без сервера/зависимостей.
- [README](README.md): критерий→артефакт→evidence→состояние; реальные model/build/answers/checks ссылки.
- [Настоящий заказ](order-example.json), [CSV-reader](order-example.py), [подготовленный core SQL](order-example.sql):1 item/3 payments/1 review, GMV38.71. SQL не выполнялся.
- [Записка](decisions-note.md), [дашборд](dashboard-concept.md), [рост](growth-strategy.md), [защита](defense.md), [AI log](ai-log.md), [runtime gates](evidence.md).

Все changed paths и SHA256 — [manifest.sha256](manifest.sha256), кроме самого manifest. [input-evidence.json](input-evidence.json) фиксирует прочитанные чужие байты и атрибуцию проверки. Input local HEAD`2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`; main synthesis`1939068295d7203a15cbb0a1ab5d407caca90f58`; research`72c1fb6ffe43e95b2ba539dc1b396374f4bfde3a`. Публикационный SHA W-12 назначает W-01 после публикации; он не выдуман здесь.

## Фактически проверено W-12

| Фактическая команда / инструмент | Результат и предел |
|---|---|
| `python3 docs/submission/order-example.py --output docs/submission/order-example.json` | Exit0; прочитан связанный пример восьми CSV: 1 item /3 payments /1 review, GMV=payment=38.71; не raw/core |
| `python3 answers/static-check.py` | Exit0; `OK (19 files); no DB executed` |
| `python3 scripts/verify-model.py --plan` | Exit0; 16 cases, `missing_stages=[]`, `status=pending_db_execution` |
| Лёгкий Python/regex inventory DDL | 47 бизнес-полей восьми raw sources, 7 dims, 4 facts; не SQL execution |
| Сверка SHA256 отчёта W-10 | 15/15 recorded hashes совпали с актуальными файлами на `2026-10-28T09:56:30Z`; сам fixture W-12 не повторял |
| `python3 docs/submission/verify_pack.py --write-manifest`, затем `python3 docs/submission/verify_pack.py` | Exit0; локальные ссылки/anchors, переносимость 3 HTML, Python/JSON syntax и manifest; метод `static_only` |
| Нативный `html_preview` | Осмотр hub728/390, презентации по частям и записки642; console errors нет; подробности [qa.json](qa.json) |
| Записка | 178 whitespace words вместе с заголовком; макет12pt/170mm занимает468px, меньше половины печатной области A4 с20mm полями (≈486px); PDF/PowerPoint не проверялись |

Команды и метод каждого свидетельства отделены от PostgreSQL runtime. Проверки 14/93/static19/dry-run/plan16 независимого координатора отражены по его прямому сообщению; W-12 дополнительно выполнил только static19 и plan16, не присваивает себе остальные прогоны. Живая клавиатурная проверка браузера/человеческая репетиция не выполнены.

## Что не проверено

PostgreSQL build/core, input CSV↔live raw binding, DB checks/control, повторная сборка/rollback/concurrency и actual Q1–Q5 model exports; Q6–Q10 ждут опубликованных условий. Живая репетиция людей, полный dashboard runtime, нагрузочный benchmark и человеческое принятие параметров не заявлены.

Блокеры SQL runtime по полученному handoff: guard exit78 на Mac (SSD30.42GiB<35, pressure2), Docker daemon отсутствует. Guard и системы не менялись. Это не препятствие писать код и выполнять малые static/offline проверки.

## Следующая точная команда

Сейчас, из корня checkout:

```sh
python3 docs/submission/verify_pack.py
```

Для непосредственного показа:

```sh
python3 docs/submission/order-example.py
```

Затем открыть [checkpoint-1330.md](checkpoint-1330.md) и HTML-файлы локально, без сервера. Код7dims+4facts и Q1–Q5 готов; pending относится к реальному PostgreSQL-результату, а не ко всем артефактам.

После готовности разрешённого PG16 endpoint и выполнения raw/model pause protocol:

```sh
RWB_RAW_RELOAD_PAUSED=1 RWB_DB_MODE=host make build check answers rebuild-check
```

Условия, write effects check/rebuild и отдельный pinned control — [build-runbook](../build-runbook.md). Не запускать эту DB-команду на заблокированном Mac и не превращать известный hash в фиктивное input binding.
