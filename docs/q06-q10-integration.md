# Интеграция Q6–Q10

## Ownership

Ветка `t3/integrate-q6-q10-marts` владеет только `answers/q06-q10/**`, новым `model/55_answers_block_b.sql`, подключением этого stage в `model/build.sql`, подключением ответов в `scripts/build-model.sh`, точной копией upstream `hack-context/hackathon-students/docs/tasks.md` и этим handoff. Общий `docs/workstreams.md` обновляет координатор через своего writer.

Источник реализации: `99bcbb366720f912ef6017a40aa5dbd6a671a8a4`, база `81058b1`. Серьёзные вопросы семантики ожидают отдельного review и решения пользователя; утверждение человеком и результаты полного Olist не заявляются.

## Результат

База интеграции: `origin/main` `bbbfab8a67aa9c9920c250dc4f638e66ffbc4fc4`. Исходные восемь файлов взяты из `99bcbb366720f912ef6017a40aa5dbd6a671a8a4`; SQL-определения перенесены в `model/55_answers_block_b.sql`, который вызывается внутри атомарной сборки до `90_checks.sql`. Ответы читают именованные представления:

- Q6: `mart.q06_price_history`; Q7: `mart.q07_delivery_by_state`; Q8: `mart.q08_status_snapshot`.
- Q9: `mart.q09_payments_2018_by_state` и `mart.q09_payment_methods` — два отдельных результата.
- Q10: `mart.q10_review_delivery` и отдельная диагностика `mart.q10_review_coverage`.

Варианты популяций, периодов, оценок и правил опоздания остаются в результатах. Для Q7 представление содержит все группы, а SELECT применяет порог 500 к `orders_count`; это позволяет менять порог, не переопределяя представление. `scripts/build-model.sh answers` включает оба результата Q9 и отдельный coverage Q10, сохраняя существующие ответы Q1–Q5. Копия `tasks.md` побайтно совпадает с `docs/tasks.md` организаторов на `558f0f6a38110acc9fcf4386a7e53ece973aedf5`.

## Проверки и ограничения

- `python3 answers/q06-q10/test_wiring.py`: fake `psql` принимает SQL, развёрнутый реальным wrapper. Проверены последовательность фактических stages, семь имён представлений, наличие Q1–Q10 и обоих результатов Q9 и coverage; отсутствие нового stage или файла coverage приводит к ошибке до запуска `psql`. База не использовалась.
- `bash -n scripts/build-model.sh` и компиляция двух Python-проверок прошли. Сравнение семи определений с SQL на `99bcbb3` подтвердило перенос текста без изменения вычислений, кроме переноса порога Q7 из HAVING во внешний SELECT; проверены `git diff --check` и побайтовое совпадение upstream tasks.
- PostgreSQL, полный Olist, атомарный rollback/rebuild и поведение интегрированных представлений на fixture не запускались. Прежний fixture PASS PostgreSQL 17.11 относится к `99bcbb3`, а не к этим байтам; здесь нет нового DB PASS и новых чисел.
- Независимый Astra review исходного SHA идёт отдельно. Семантические замечания, выбор бизнес-правил и человеческое утверждение остаются открытыми. После review — решить замечания, затем при разрешённых ресурсах выполнить fixture и полную сборку/проверки на согласованной базе.

## Адресные исправления координатора

Код `2e8eff9ce94b4640c0c80e6257ebdb142cd723e5`: семь новых views включены в явный RESTRICT drop inventory для повторной сборки. Усилены проверки средних/долей/знаменателей, повторных одинаковых оценок и точной границы порога. На PostgreSQL16.15 прошли 16-order behavior fixture и отдельный 10-order synthetic lifecycle: реальный wrapper build/rebuild, equality fingerprints, late failure rollback, raw unchanged, answers и invariants. Два мутанта (> вместо >=, неправильный знаменатель late) тест обнаружил. [Evidence с хешами](phase-20261028/evidence/pg16-small-02/summary.json), [мутации](phase-20261028/evidence/mutation-results.json). Это не full Olist и не CSV/raw equality.

Ранние вопросы Q7/Q10 сняты по отзыву пользователя: сначала исследования и проверка, к человеку — остаточная равнозначная развилка. Ни одного approval по ним нет. [Текущая объяснялка](phase-20261028/index.html) содержит контекст, варианты, CSV-эксперименты и ограничения.
