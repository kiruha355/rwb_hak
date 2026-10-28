# Адресная проверка для requirements panel

Owner: Sol xhigh. UTC: 2026-10-28 08:03:40. Repository `kiruha355/rwb_hak`, main, input SHA `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`.
Метод: чтение handout/tasks/README, Git history/remotes, текста и страниц PDF 8–10, адресный web search и открытие official Claude Code docs. Ни Claude, ни БД/Docker не запускались. Корневые инструкции не менялись.

## Подтверждённые узкие результаты

**Обновление 2026-10-28 после находки коллеги:** candidate source `daniilivanovp-droid/hackathon-students` существует, default main/HEAD `3da32d149bfa14dca3fdb0c5863d0771c38efbfc`. На этом ref README/handout/tasks побайтно равны нашим копиям; [metadata/hash evidence](evidence/organizer-candidate.json), [pinned tasks](https://github.com/daniilivanovp-droid/hackathon-students/blob/3da32d149bfa14dca3fdb0c5863d0771c38efbfc/docs/tasks.md). На default ref только Q1–Q5; точные сроки/формат защиты/канал сдачи не установлены. Полномочия владельца как официального организатора и иные ветки/каналы не подтверждены. Ниже сохранён результат прежнего адресного поиска: unknown URL был его историческим пределом, а не нынешним состоянием.

**CLAUDE import.** Официальная документация прямо описывает импорт `@AGENTS.md` из соседнего `CLAUDE.md` и рекомендует этот способ совместного использования одного файла инструкций. Импорт надо писать вне inline/fenced code; относительный путь разрешается от импортирующего файла. Текстовый указатель «прочти AGENTS.md» требует, чтобы агент сам решил открыть файл. Предложение writer: однострочный `CLAUDE.md` с буквальным `@AGENTS.md`. Это документированный механизм, не проверка установленной у команды версии/конфигурации. [Official docs, Share one file with other coding tools](https://code.claude.com/docs/en/memory#share-one-file-with-other-coding-tools), [Import additional files](https://code.claude.com/docs/en/memory#import-additional-files).

**Письменная рубрика.** Визуально проверены [страница 8](evidence/case-rubric-08.png) и [страница 9](evidence/case-rubric-09.png) первичного PDF: 30+30+15+25+20+15+20 = **155**. [Текст PDF](evidence/case-pdf.txt) сохраняет содержание переносимо. Очищенная стенограмма: строки 81 и 92 говорят 150 и меняют состав критериев. Конфликт не разрешён ответом организаторов; 155 — подтверждённая сумма слайдов, а не доказательство текущего окончательного регламента.

**Upstream/регламент не установлен.** [Страница 10](evidence/case-rubric-10.png) содержит только `github.com`, без owner/repo; `pdfinfo -url` не показал ссылок. Remotes/history текущего repo не содержат upstream организаторов. `kiruha355/rwb_hak` — командный origin. Адресный поиск по `hackathon-students`, `Capibara`, точному названию кейса и `handout.md` не идентифицировал первичный organizer repo. Это ограничение поиска, не доказательство его отсутствия/закрытости.

Последний подтверждённый **локальный** снимок [tasks.md](../../../hack-context/hackathon-students/docs/tasks.md) — [team snapshot на SHA](https://github.com/kiruha355/rwb_hak/blob/2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e/hack-context/hackathon-students/docs/tasks.md), строки 85–93: ещё 5 и вброс обещаны в середине хакатона. Онлайн-публикация 6–10/вброса **unknown**, а не «ещё не опубликованы». Deadline, точное время экватора/длительность, минуты защиты и канал сдачи в исследованных письменных материалах не установлены. Нужны URL/owner/repo и прямое актуальное разъяснение организаторов. Olist README описывает отдельный hiring test с 7 днями; этот срок к RWB не переносится.

## Недоопределённости метрик (не решать подбором к контролю)

- **Q1, tasks:6–18:** период и revenue control заданы; статусная популяция столбца «число заказов» отдельно от revenue не уточнена. Возможны все оформленные заказы периода и только revenue-eligible; календарный ноль не разрешает эту развилку.
- **Q2, tasks:22–33:** revenue принадлежит конкретным seller items. Популяция count orders/units и временной диапазон не указаны явно; один order с несколькими продавцами входит в seller order counts несколько раз, поэтому итог по продавцам неаддитивен. Нельзя переносить Q1 date window автоматически.
- **Q3, tasks:37–49:** задан order grain, контроль 159.88, ошибочные line averages. Но `items+freight` vs `payments`, статус/период, обработка orders без children и знаменатель требуют явного контракта. [Profiling:60,66–67](../../../docs/profiling.md) содержит выбранное объяснение control, но не заменяет первичное уточнение.
- **Payment comparator, profiling:44:** точные SQL, population, missing children и NULL/zero не сохранены. Не объявлять 366 воспроизведённым и не приписывать ваучеры/округления как установленную причину.

Эти пункты можно передать организаторам как точные вопросы; до ответа показывать альтернативы и выбранное временное допущение. Модель должна сохранять исходные величины, чтобы изменение контракта не требовало подмены raw.

## Поиск: реальные запросы и пробелы

Запросы web search 2026-10-28: `"hackathon-students" "Capibara"`; `"Модель маркетплейса" "github"`; `site:code.claude.com/docs CLAUDE.md import @ file AGENTS.md`; `"hackathon-students" "handout.md"`; `"Capibara" "550 759"`. Первичный organizer URL не найден; нерелевантные результаты не использованы. Прочитана официальная страница memory/imports, получены section locators. API Olist `/commits/master` был недоступен в web-open; это не доказательство отсутствия commit, query и billing не связаны. Pinned README/LICENSE открылись, но current upstream head ещё не подтверждён Sol.
