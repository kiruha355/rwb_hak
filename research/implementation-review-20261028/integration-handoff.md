# Интеграция root fixes и двух реальных HTML-показов

Repository: `kiruha355/rwb_hak`. Input main: `bcd4a9d67ec2f9da0cc20b151fb1b967ae7f417e`.
Owner: координатор реализации. Готовая адресная порция: [manifest](integration-publication.json).
Публикация — W-01; наличие этого файла само по себе не утверждает remote SHA.

## Разрешение пересечений

- Основные `dashboard/index.html`, `dashboard/data.js`, `dashboard/export.sql`,
  `scripts/export-dashboard.sh`, Makefile и весь `dashboard/sample/**` сохранены
  побайтно из input main. Они не включены в изменяемую порцию.
- `dashboard/README.md` сохраняет полный текст коллеги и добавляет автономный реальный
  показ. Root не возвращает перемещённые root-level sample/exporter пути.
- Наш экспортёр, шесть offline-проверок и шаблон находятся в `dashboard/subset/**`.
  `dashboard/olist.html` — один HTML с настоящей выборкой и lossless gzip JSON.
- `model/20_facts.sql` содержит одновременно root POSIX key guards и ANALYZE коллеги;
  объединённая версия проверена повторно в PG16. Остальные R1–R5 описаны в
  [протоколе исправлений](review-fixes.md). Оригинальный Astra review не переписан.

## Фактически выполненные проверки

| Область | Проверка и результат |
|---|---|
| Полный UI коллеги | Native html_preview, ширина 728: 99 441 заказ / 112 650 позиций; 14/14 сверок против SQL этой же выгрузки; console errors 0; horizontal overflow false. [Evidence](full-dashboard-check.json). |
| Полные SQL-результаты | Извлечены из опубликованного `data.js` с commit, hash, export time и source views. [Q1–Q5](full-model-answers.json). Не выдаются за отдельный прогон последних root SQL. |
| Исправленные SQL | 21/21 native PG16 fixtures; 17 unittest, включая 3 реальных PG CSV/comparator regressions. [Отчёт](review-fixes-pg-cases.json), [лог](review-fixes-pg-tests.txt). |
| Реальная выборка | Существующие 1 000 заказов со всеми детьми; 8/8 CSV/raw, build/check/answers/rebuild, 201 invariant: 0 errors / 0 warnings; поздняя реальная ошибка 22012 сохранила fingerprints raw/core/mart. [Validation](olist-subset-validation.json), [rollback](olist-subset-rollback.json). |
| Автономный HTML | Декодирован gzip/base64: payload точно равен read-only JSON; ID и multiplicity позиций/отзывов равны subset CSV; все 1 037 платежей учтены; отсутствующий платёж NULL; synthetic reset отсутствует. [Export check](olist-subset-export-check.json). |
| Остальные малые проверки | Шесть exporter tests; static19; bash syntax; make dry-run; W-10 93 DuckDB rerun ранее по тем же mart/answer bytes. |
| Комплект | Manifest 24 файлов, 377 local links, 4 HTML; записка 185 слов. README, короткая речь и [сценарий показа](../../docs/submission/live-demo.md) отражают оба реальных объёма. |

Собственный малый PostgreSQL после проверки остановлен, его данные сохранены.
Docker, новые зависимости, полный fixture и обход resource guard не использовались.

## Границы и публикация

Полный UI пересчитывается из полного модельного экспорта коллеги; его внутренняя
сверка не доказывает равенство всех CSV и live raw. Наша независимая проверка
source/raw/model/rebuild/rollback относится к 1 000 реальных заказов. Полный
source binding, lifecycle/concurrency и прогон полного снимка с последними root
исправлениями остаются отдельной работой. Условия Q6–Q10 не выдумывались.

W-01: проверить все `files` нового manifest, применить только изменённые пути
через согласованный временный index от свежего main, проверить diff/ссылки/remote
SHA. Если main продвинулся, сверить влияние на эти пути и сохранённые входы.
Старый локальный 39-file `post-review-publication.json` заменён новым handoff;
по его старым dashboard paths публиковать нельзя.
