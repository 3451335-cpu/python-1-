# Практическое задание №1 — вариант 30

Проект реализует требования варианта №30:

- 3 сущности в памяти: `Person`, `Message`, `Feedback`;
- 12 CRUD-функций (по 4 на сущность);
- 13-я функция — выборка по реляционной алгебре;
- REPL;
- TCP RPC;
- бинарный заголовок по таблице 30;
- little-endian;
- журнал RPC-запросов в `journal.log`;
- RPC-клиент с теми же именами методов, что и функции слоя данных;
- MBT через `hypothesis.stateful.RuleBasedStateMachine`;
- проверка branch coverage через `coverage`.

## 1. Структура

```text
variant30/
├── README.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── model.py       # слой данных
│   ├── protocol.py    # TCP-протокол
│   ├── server.py      # RPC-сервер
│   ├── client.py      # RPC-клиент
│   └── repl.py        # REPL
└── tests/
    └── test_mbt.py    # MBT
```

## 2. Установка

Python 3.11+:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Затем:

```bash
pip install -r requirements.txt
```

## 3. Запуск сервера

Из корня проекта:

```bash
python -m src.server
```

Сервер слушает:

```text
127.0.0.1:5000
```

Каждый RPC-запрос записывается в:

```text
journal.log
```

## 4. REPL

В отдельном терминале:

```bash
python -m src.repl
```

Пример:

```text
v30> call create_person {"record":{"key":1,"datetime":1770000000,"platform":"web","user_agent":"Chrome"}}
{"key": 1, "datetime": 1770000000, "platform": "web", "user_agent": "Chrome"}

v30> call get_all_persons {}
[{"key":1,"datetime":1770000000,"platform":"web","user_agent":"Chrome"}]
```

Для завершения:

```text
quit
```

## 5. 13 RPC-операций

Коды выбраны в проекте последовательно; задание задаёт формат пакета, но не задаёт конкретные значения operation code.

| Код | Метод |
|---:|---|
| 1 | `create_person` |
| 2 | `delete_person` |
| 3 | `get_all_persons` |
| 4 | `get_person` |
| 5 | `create_message` |
| 6 | `delete_message` |
| 7 | `get_all_messages` |
| 8 | `get_message` |
| 9 | `create_feedback` |
| 10 | `delete_feedback` |
| 11 | `get_all_feedbacks` |
| 12 | `get_feedback` |
| 13 | `recent_message_data` |

## 6. Формат TCP-пакета

### Request

```text
offset 0, size 2 bytes  -> operation code
offset 2, size 3 bytes  -> JSON body size
offset 5, variable      -> JSON body
```

### Response

```text
offset 0, size 1 byte   -> protocol version = 1
offset 1, size 2 bytes  -> operation code
offset 3, size 5 bytes  -> JSON body size
offset 8, variable      -> JSON body
```

Все целые числа заголовка передаются little-endian.

Особенно важно: размер тела запроса занимает **3 байта**, а размер тела ответа — **5 байт**. Поэтому обычный `struct.pack("<I", ...)` здесь использовать напрямую нельзя.

## 7. Реляционная алгебра

Требуемая выборка:

```text
π_{M.data, P.platform}
(
    σ_{M.datetime > now - 8 min}
    (
        P ⋈_{P.key=M.person} M
    )
)
```

В `recent_message_data()` это реализовано так:

1. вычисляется `cutoff = now - 8 * 60`;
2. перебираются `Message`;
3. остаются сообщения, у которых `datetime > cutoff`;
4. находится соответствующий `Person` по `Person.key == Message.person`;
5. возвращаются только:
   - `Message.data`;
   - `Person.platform`.

## 8. Model-Based Testing

Запуск:

```bash
pytest -q
```

Тест `tests/test_mbt.py` использует:

```python
RuleBasedStateMachine
```

и выполняет реальные TCP-вызовы через `RPCClient`.

Есть отдельное сгенерированное Hypothesis-правило `exercise_all_13_rpcs`, которое за один generated step вызывает все 13 RPC-методов.

## 9. Coverage

```bash
coverage run --branch -m pytest -q
coverage report -m
```

или:

```bash
coverage html
```

После этого HTML-отчёт находится в:

```text
htmlcov/index.html
```

## 10. Что показать преподавателю

### Этап 1

Показать:

- создание записей;
- получение одной записи;
- получение всех записей;
- удаление;
- ошибку при обращении к отсутствующему ключу;
- выборку последних сообщений;
- REPL.

### Этап 2

Показать:

- запущенный TCP-сервер;
- клиент;
- удалённые вызовы всех 13 методов;
- `journal.log`;
- при необходимости разобрать первые 5/8 байт пакета.

### Этап 3

Показать:

```bash
pytest -q
coverage run --branch -m pytest -q
coverage report -m
```

и файл `tests/test_mbt.py`.

## 11. Примечание об ограничениях

Задание требует хранения данных в памяти, поэтому после перезапуска сервера записи исчезают.

Для связей ER-диаграммы проект дополнительно проверяет:

- `Message.person` должен ссылаться на существующий `Person`;
- `Feedback.message` должен ссылаться на существующий `Message`.

Удаление родительской записи автоматически не удаляет дочерние записи — это сознательно оставлено простым и явно не задано в варианте.
