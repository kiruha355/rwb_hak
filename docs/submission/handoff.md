# W-15 · Передача README и обновлённого комплекта W-12

**Ready for publication через W-01.** Разрешённая область: `README.md`, `docs/submission/**`. Основной код и первый комплект опубликованы в main `aca34f5b693b794fc2a0ea8c2623293b462b6089`; эта передача касается доработки перед выступлением. Git index/add/commit/push/checkout/pull/reset/merge не использовались. Fetch выполнен; чужие кодовые пути, explainer и реестры не изменялись. Новых агентов, серверов, зависимостей и тяжёлых запусков нет.

## Что открыть сейчас

1. [Root README](../../README.md): задача, требования, 7 dims/4 facts, 5 из10 SQL, метрики, build prerequisites, evidence, AI и развитие.
2. [Короткий экран](checkpoint-now.html), [речь](checkpoint-now.md): 226 русских слов, пять обязательных результатов, семь критериев PDF. Речь занимает примерно две минуты; человеком не репетировалась.
3. [Единый hub](index.html) → [расширенный показ](presentation.html) и [чекпоинт 5–7 минут](checkpoint-1330.md) → детали. Нового реестра решений/ownership нет.

Принятый пакет и HTML отражены в README, index, обоих presentation, checkpoint, memo, dashboard concept и evidence. Открыты только именованные late/reviewweight/smoothing и их параметры; counts/windows/dashboard area/HTML не названы полностью pending. [Связанный CSV-заказ](order-example.json):1 item/3 payments/1 review; price29.99 +freight8.72 =GMV38.71 =payments38.71; наивный JOIN price89.97. Core SQL этого заказа не выполнялся.

## Публикационная порция

`README.md`; в `docs/submission/`: `README.md`, `checkpoint-now.md`, `checkpoint-now.html`, `checkpoint-1330.md`, `index.html`, `presentation.md`, `presentation.html`, `decisions-note.md`, `decisions-note.html`, `dashboard-concept.md`, `defense.md`, `evidence.md`, `ai-log.md`, `input-evidence.json`, `qa.json`, `verify_pack.py`, `handoff.md`, `manifest.sha256`.

Все актуальные hashes — [manifest.sha256](manifest.sha256); root README включён ключом `../../README.md`. Manifest не хеширует сам себя. Неизменённые файлы W-12 также сохранены в manifest для целостности комплекта. Верификатор проверяет root README и новые входные точки, относительные ссылки/anchors, HTML/Python/JSON syntax, переносимость и hashes. Только W-01 делает адресный add/commit/push; файлы чужих зон в порцию не включать.

## Что проверил W-15

| Метод / команда | Наблюдаемый результат и граница |
|---|---|
| `python3 docs/submission/verify_pack.py --write-manifest`, затем без флага | PASS static-only; 23 файла с root README,4 HTML; manifest обновлён/проверен. Это не SQL runtime |
| `python3 answers/static-check.py` | Exit0,19 files; no DB executed |
| `python3 scripts/verify-model.py --plan` | Exit0,16 cases, missing_stages=[]; сам план не исполняет SQL |
| Нативный `html_preview` | Короткий экран1440×756; hub728 и390; изменённые sections9/11/12 presentation; memo642×448. Console errors нет; [qa.json](qa.json) |
| Нативный `html_render` | Короткий экран показан в треде после preview; локальный HTML остаётся переносимым |
| Записка | 185 whitespace words с заголовком;448px при ширине642 меньше≈486px половины печатной области A4 с20mm полями. PDF-пагинация не проверялась |

Старые записи QA/input evidence сохранены как исторические; добавлен отдельный W-15 snapshot с hashes прочитанных PG/Astra/source-артефактов. [AI log](ai-log.md) разделяет работу ИИ, принятые пользователем решения и методы проверки.

## Переданное runtime evidence и оставшиеся gates

Координатор сообщил14 Python и93 DuckDB PASS. W-14 выполнил **16/16 реальных малых PostgreSQL16.15 cases**:4 positive,12 expected failures; fixture CLI0.944424s, полный отчёт1.975227s; сервер остановлен, cluster сохранён. [PG report](../../research/implementation-review-20261028/pg-smoke.md), [JSON](../../research/implementation-review-20261028/pg-smoke.json). W-15 эти прогоны не повторял и себе не присваивает.

[Astra review](../../research/implementation-review-20261028/astra-review.md):1 P1+4 P2. Суть findings — в [technical evidence](evidence.md#независимый-review); фиксы отдельно ведёт parent. Они не объявлены закрытыми этой документацией.

**Pending:** полная Olist-build, CSV↔live raw binding, pinned control, clean/rebuild/late rollback/concurrency, full-data Q1–Q5 exports, опубликованные условия и ответы Q6–Q10, UI↔full-data SQL parity, нагрузочный benchmark и живая репетиция. Общий production/DB pass и финальная готовность всех10 ответов не заявлены. Mac guard78 соблюдён.

## Следующие команды

Сейчас, без БД:

```sh
python3 docs/submission/verify_pack.py
```

Для разрешённого подготовленного PG16 endpoint, **только после** подтверждённого raw reload pause и проверки правильного endpoint:

```sh
RWB_RAW_RELOAD_PAUSED=1 RWB_DB_MODE=host make build
```

Дальнейшие check/answers/rebuild/control и условия input binding — [runbook](../build-runbook.md) и [evidence](evidence.md#следующий-шаг). `setup.sh` выполняет TRUNCATE/reload; `--reset` удаляет volumes: это не ежедневная команда сборки модели. На заблокированном Mac её не запускать.
