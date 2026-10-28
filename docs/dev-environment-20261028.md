# Локальное окружение разработки RWB на Mac

Repository: `kiruha355/rwb_hak` · task: W-07 · owner: подготовка dev-окружения (Codex / Sol).
Input `origin/main`: `1939068295d7203a15cbb0a1ab5d407caca90f58`; local base:
`2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`. Сверка начата `2026-10-28T09:06:39Z`;
проверки ниже выполнены до `2026-10-28T09:14:28Z`.

Команды и Python-зависимость подготовлены. **Запуск PostgreSQL заблокирован ресурсным
preflight; работающая БД пока не подтверждена.** Изменений `raw`, `core`, `mart`,
реализации модели и бизнес-запросов этот пакет не содержит.

## Что реально проверено

| Компонент | Результат |
|---|---|
| Docker CLI / Compose | `29.1.3` / `v2.40.3-desktop.1`, команды установлены |
| Docker daemon | Недоступен через текущий context `desktop-linux`; контейнеры/volumes проверить не удалось |
| PostgreSQL | В compose выбран `postgres:16-alpine`, порт только `127.0.0.1:5432`; работа сервера не проверена |
| Локальный SQL-клиент | `psql 17.11 (Homebrew)` установлен |
| Python | `3.11.9`; отдельный venv `$HOME/.local/share/rwb-hak-dev/venv` создан |
| Драйвер загрузчика | `psycopg2-binary==2.9.13` установлен в venv, импорт проходит; global Python не изменён |
| Входные CSV | Все 8 файлов, 550 759 записей; SHA-256, заголовки и counts совпали с закреплённым baseline |
| Порт 5432 | При проверке listener отсутствовал; это не доказывает отсутствия остановленного `fast-vpn-db` |
| Скрипт проверки | `bash -n` и offline-проверка прошли; обычный запуск вернул `3` на недоступном Docker |

Preflight от `2026-10-28T09:06:47Z` вернул **78**: свободно 30,42 ГиБ при минимуме
35 ГиБ, `memory_pressure_level=2`, swap 1,26 ГиБ. Новые VM, контейнеры, тяжёлые
установки и сборки не запускались. Сохранённые лимиты Docker: 4 CPU, 4096 MiB RAM,
1024 MiB swap, build cache 4GB, Kubernetes выключен. Локальный daemon config уже
содержит `log-driver=local`, `max-size=10m`, `max-file=3`; применение этих настроек
живым daemon и логирование существующих контейнеров ещё не проверены.

## Команды повседневной работы

Из корня checkout:

```sh
bash scripts/dev-check.sh --offline
bash scripts/dev-check.sh
source "$HOME/.local/share/rwb-hak-dev/venv/bin/activate"
docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U hack -d marketplace
```

Первая команда проверяет локальные инструменты, конфигурацию и CSV. Вторая дополнительно
проверяет Docker, владельца контейнера, PostgreSQL 16 и `raw` в транзакции read-only.
Она не запускает сервисы, не устанавливает зависимости и не загружает данные. Проверка
покрывает counts и `_source_file`; полное равенство значений CSV↔raw и корректность
будущей модели — отдельные проверки. Коды выхода: `0` — выбранные проверки прошли,
`2` — локальная предпосылка/вход изменились, `3` — runtime недоступен или не прошёл проверку.

Ожидаемый endpoint из compose: `127.0.0.1:5432`, database `marketplace`, user `hack`;
учебный пароль указан в [docker-compose.yml](../docker-compose.yml). Альтернативный
venv задаётся через `RWB_DEV_PYTHON=/path/to/venv/bin/python`.

## Первый следующий шаг для запуска БД

После наблюдаемого освобождения ресурсов первым выполнить:

```sh
"$HOME/bin/dev-job" preflight
```

Продолжать запуск только при коде `0`; код `78` не обходить отключением guard,
изменением лимитов или очисткой RAM. Сейчас повторная тяжёлая попытка не выполнялась.

1. Если daemon по-прежнему недоступен, запустить установленный Docker Desktop обычным
   `open -a Docker`, дождаться готовности и проверить `docker info`. Не перезапускать
   работающий Docker или другие приложения ради подготовки стенда.
2. Выполнить `docker ps -a` и проверить порт `lsof -nP -iTCP:5432 -sTCP:LISTEN`.
   Если порт/имя заняты чужим контейнером, не останавливать его и не менять root compose
   автоматически. У остановленного `hack_postgres` проверить Compose labels/working directory.
3. Для существующего контейнера этого checkout: `docker compose start postgres`.
   Затем `bash scripts/dev-check.sh`. Состояние `raw` сохранить.
4. Если собственного контейнера нет, сначала проверить существующие volumes и cached image
   `postgres:16-alpine`. Создание только после проверки ownership и свободного порта:
   `docker compose up -d --no-recreate --no-build --pull never postgres`. Команда не
   скачивает образ; отсутствие образа требует отдельного обычного pull при успешном guard.
   Проверить реальные log options: `docker inspect hack_postgres --format '{{json .HostConfig.LogConfig}}'`.
   Существующие контейнеры ради применения log defaults не пересоздавать.
5. **Только для новой пустой БД**, после подтверждения пустоты всех восьми raw-таблиц
   и отсутствия чужих данных, допускается первоначальная загрузка:
   `"$HOME/.local/share/rwb-hak-dev/venv/bin/python" scripts/load_raw.py --skip-ddl`.
   Затем обычная `dev-check.sh` должна пройти. Для существующего raw эту команду не запускать.

`scripts/setup.sh` непригоден как ежедневный запуск: он всегда вызывает загрузчик,
а загрузчик очищает raw через `TRUNCATE` и без `--skip-ddl` выполняет DDL с `DROP TABLE`.
`setup.sh --reset` дополнительно удаляет Docker volumes. Эти команды в W-07 не выполнялись.

## Как воспроизвести малую Python-зависимость

Для этого Mac venv уже существует. На другой машине создать новый изолированный venv
на Python 3.10+ и установить [requirements-dev.txt](../requirements-dev.txt):

```sh
python3 -m venv "$HOME/.local/share/rwb-hak-dev/venv"
"$HOME/.local/share/rwb-hak-dev/venv/bin/python" -m pip install --only-binary=:all: -r requirements-dev.txt
```

Текущая установка выполнена `uv venv` и `uv pip install --no-cache --only-binary=:all:`;
объём файлов venv — 9 790 269 байт. Загружен готовый wheel
`psycopg2_binary-2.9.13-cp311-cp311-macosx_11_0_arm64.whl`, 3 817 384 байт,
SHA-256 `32cd049095135d2b69e824aea9056745a4aaaa9115a9febbc65584793665d0d0`.
Версия и wheel сверены по [PyPI API](https://pypi.org/pypi/psycopg2-binary/2.9.13/json).
Версия закреплена manifest-файлом; эта команда не является hash-locked установкой
всех платформ. Venv находится вне Git и сохранён для продолжения разработки.

CSV baseline: официальный Olist ref `d9e49802f3e92d09ee94ab9ccc5e457f207a8959`;
хеши и число записей закреплены в `dev-check.sh`. Утилита читает перечень колонок
через AST существующего loader без его выполнения. Смена данных или появление вброса
требует явного обновления baseline; проверка не подменяет вход mutable `master`.

## Передача и границы

Новые файлы: этот runbook, [read-only check](../scripts/dev-check.sh) и manifest зависимости.
Нужна адресная публикация W-01 в `proposal/dev-environment-20261028` от свежего main;
index, ветки и общие файлы автор W-07 не меняет. `ready_for_review` относится к этому
пакету; DB runtime остаётся `blocked` до успешного обычного `dev-check.sh`.

Не проверены: Docker daemon/container/volume state, DB/raw contents, права и транзакции
на живом PG16, сетевое подключение драйвера, сборка core/mart, clean rebuild и benchmark.
Ветка runtime скрипта прочитана и проходит syntax check, но без daemon не исполнялась до БД.
Архитектурные решения и необязательные инструменты дашборда этим пакетом не выбираются.
