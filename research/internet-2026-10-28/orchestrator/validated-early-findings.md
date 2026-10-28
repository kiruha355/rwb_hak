# Ранняя порция проверенных наблюдений

Repository `kiruha355/rwb_hak`; исходные документы на `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`. Проверка 2026-10-28 UTC, Sol xhigh. Это наблюдения CSV/источников, не принятое решение модели и не проверка PostgreSQL raw/core/mart.

## Денежный comparator и fanout

Sol выполнил [новый независимый скрипт](evidence/validate_local.py) на локальных CSV стандартной библиотекой и Decimal. [Результат](evidence/sol-independent-check.json) содержит SHA-256/header/count каждого из восьми входов, всего **550759 CSV records** (не физических строк). Terra B02 отдельно выполнил [streaming pinned URLs](../corpus/02_money_reconciliation/evidence/reproduce.py) и сохранил [результаты](../corpus/02_money_reconciliation/evidence/results.json). Соответствие этих CSV фактически загруженному `raw` не проверено.

На **98665 заказах с items и payments**, все статусы, `delta = sum(payment_value) − sum(price+freight_value)` при независимой агрегации каждой стороны:

| Фильтр одного и того же набора delta | Count | Sum delta |
|---|---:|---:|
| exact nonzero | 639 | −1819.51 |
| abs(delta) > 0.01 | 366 | −1818.84 |

Пара из profiling **366 / −1819.51** воспроизводится как count с допуском плюс sum всех delta, но не как count и sum одного указанного фильтра. Исходный SQL коллеги неизвестен: это возможная реконструкция, не установленное происхождение. Причины расхождений не установлены. У одного заказа есть items без payment, у 775 — payment без items; ноль вместо отсутствующей стороны даёт другую задачу (в evidence отдельно маркирована гипотеза zero substitution).

Прямой items×payments join на том же пересечении даёт **117601 строку**: item+freight **15848099.68 → 16571528.43**, payment **15846280.17 → 20308134.71**. Расчёт по multiplicities, без материализации join/DB. Наличие constellation не делает такой query безопасным; общий grain и cardinality надо доказывать.

## Reviews, identity, время

- **99224 review-pairs уникальны**, distinct review_id **98410**, конфликтов полного tuple пяти payload fields **0**. Sol сравнивал точные декодированные CSV values включая пустую строку, B01 — также по каждому полю. Следовательно review entity+bridge может восстановить пары на этом снимке; pair fact тоже допустим. SQL NULL semantics, будущие конфликты и выбор веса review/association/order требуют отдельной проверки. Причина общих ID и история NPS/split-order не доказаны.
- **99441 customer_id, 96096 customer_unique_id**, у **250** unique IDs несколько ZIP prefixes. Это наблюдение адресов, не доказательство переезда или residential history. Интерпретации office/gifts тоже возможные объяснения, не установленные факты.
- В purchase months нет 2016-11; после 2018-09-01 **20** заказов (**16 Sep, 4 Oct**), delivered status **0**. Max purchase `2018-10-17 17:30:18`, max present delivered timestamp `2018-10-17 13:22:46`. Эти maxima не доказывают extraction as-of/полноту последующих событий; cutoff покупки не равен cutoff наблюдения. Универсальное отсечение всех метрик на Aug31 и обязательные 90 дней не установлены.

## Адресный upstream и документы

Найденный коллегой [daniilivanovp-droid/hackathon-students](https://github.com/daniilivanovp-droid/hackathon-students) проверен непосредственно: default `main`, HEAD `3da32d149bfa14dca3fdb0c5863d0771c38efbfc`; raw README/handout/tasks на этом ref побайтно совпали с нашими копиями. [Compact evidence](evidence/organizer-candidate.json), [tasks на ref](https://github.com/daniilivanovp-droid/hackathon-students/blob/3da32d149bfa14dca3fdb0c5863d0771c38efbfc/docs/tasks.md). По этому ref опубликованы Q1–Q5, далее обещание ещё5/вброса. Официальное полномочие владельца, другие каналы и будущие публикации не доказаны. Точные сроки/защита/канал сдачи в трёх файлах не найдены.

PDF страницы 8–9 дают 155, очищенная стенограмма — 150: проверен конфликт, не получено окончательное разъяснение организаторов. [Адресный отчёт](requirements-targeted-check.md) также фиксирует документированный `@AGENTS.md` import без запуска Claude.

## Исправление собственного раннего вывода

В раннем сообщении Sol отсутствие вывода `rg --files data` было ошибочно принято за отсутствие CSV. Команда учитывала ignore; `rg --files --no-ignore data` показала восемь файлов, затем они были прочитаны. Артефакты расчётов содержат фактический метод и hashes. Ошибка не должна распространяться как факт о рабочем checkout.
