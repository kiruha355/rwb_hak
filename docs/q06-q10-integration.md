# Интеграция Q6–Q10

## Ownership

Ветка `t3/integrate-q6-q10-marts` владеет только `answers/q06-q10/**`, новым `model/55_answers_block_b.sql`, подключением этого stage в `model/build.sql`, подключением ответов в `scripts/build-model.sh`, точной копией upstream `hack-context/hackathon-students/docs/tasks.md` и этим handoff. Общий `docs/workstreams.md` обновляет координатор через своего writer.

Источник реализации: `99bcbb366720f912ef6017a40aa5dbd6a671a8a4`, база `81058b1`. Серьёзные вопросы семантики ожидают отдельного review и решения пользователя; утверждение человеком и результаты полного Olist не заявляются.
