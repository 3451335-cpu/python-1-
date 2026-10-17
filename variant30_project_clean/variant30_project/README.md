# Вариант №30 — TCP RPC

## 1. Описание

Проект реализует прототип веб-приложения с удалённым вызовом процедур
по TCP. Данные хранятся только в памяти. Реализованы сущности `Person`,
`Message` и `Feedback`, 12 CRUD-операций и одна реляционная выборка.

Проект выполнен в соответствии с вариантом №30 практического задания.

## 2. Структура

```text
variant30_project/
├── README.md
├── .gitignore
├── requirements.txt
├── pytest.ini
├── run.bat
├── src/
│   ├── __init__.py
│   ├── model.py
│   ├── protocol.py
│   ├── server.py
│   ├── client.py
│   └── repl.py
├── scripts/
│   └── demo.py
└── tests/
    └── test_mbt.py
```

## 3. Этап 1

Слой данных использует словари в памяти.

Для каждой сущности доступны:

- создание записи;
- удаление записи;
- получение всех записей;
- получение одной записи по `key`.

Дополнительная функция `recent_message_data` выполняет выборку:
сообщения за последние 8 минут соединяются с `Person` по `key = person`,
после чего возвращаются `Message.data` и `Person.platform`.

REPL запускается командой:

```text
python -m src.repl
```

## 4. Этап 2

TCP RPC использует бинарный заголовок из задания.

Запрос:

```text
2 байта — код операции
3 байта — размер JSON
JSON — тело запроса
```

Ответ:

```text
1 байт — версия протокола
2 байта — код операции
5 байт — размер JSON
JSON — тело ответа
```

Числа передаются в little-endian. Запросы журналируются в `journal.log`.

Сервер запускается командой:

```text
python -m src.server
```

Демонстрация всех RPC:

```text
python -m scripts.demo
```

## 5. Этап 3

Используется `RuleBasedStateMachine` из Hypothesis. Состояние эталонной
модели сравнивается с состоянием реального TCP RPC-сервера.

Тесты запускаются командой:

```text
python -m pytest -q
```

Проверка покрытия:

```text
coverage run --branch -m pytest -q
coverage report -m
```

## 6. Установка

Установить зависимости:

```text
python -m pip install -r requirements.txt
```

## 7. Скрипт запуска

В Windows можно выполнить:

```text
run.bat
```

## 8. Функции

`DataStore` предоставляет 13 функций:

```text
create_person
 delete_person
get_all_persons
get_person
create_message
delete_message
get_all_messages
get_message
create_feedback
delete_feedback
get_all_feedbacks
get_feedback
recent_message_data
```

`RPCClient` предоставляет те же имена для удалённого вызова.
