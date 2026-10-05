from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class DataStore:
    """In-memory data access layer for Variant 30."""

    def __init__(self) -> None:
        self.persons: dict[int, dict[str, Any]] = {}
        self.messages: dict[int, dict[str, Any]] = {}
        self.feedbacks: dict[int, dict[str, Any]] = {}

    @staticmethod
    def _validate_id(value: int) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("key must be int")

    @staticmethod
    def _copy(record: dict[str, Any]) -> dict[str, Any]:
        return dict(record)

    def _create(self, table: dict[int, dict[str, Any]], record: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(record, dict):
            raise ValueError("record must be object")
        if "key" not in record:
            raise ValueError("record must contain key")
        key = record["key"]
        self._validate_id(key)
        if key in table:
            raise ValueError(f"record with key={key} already exists")
        table[key] = dict(record)
        return self._copy(table[key])

    def _delete(self, table: dict[int, dict[str, Any]], key: int) -> None:
        self._validate_id(key)
        if key not in table:
            raise KeyError(f"record with key={key} not found")
        del table[key]

    @staticmethod
    def _all(table: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
        # Sorting makes RPC/MBT results deterministic.
        return [dict(table[key]) for key in sorted(table)]

    def _get(self, table: dict[int, dict[str, Any]], key: int) -> dict[str, Any]:
        self._validate_id(key)
        if key not in table:
            raise KeyError(f"record with key={key} not found")
        return self._copy(table[key])

    # Person
    def create_person(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._create(self.persons, record)

    def delete_person(self, key: int) -> None:
        self._delete(self.persons, key)

    def get_all_persons(self) -> list[dict[str, Any]]:
        return self._all(self.persons)

    def get_person(self, key: int) -> dict[str, Any]:
        return self._get(self.persons, key)

    # Message
    def create_message(self, record: dict[str, Any]) -> dict[str, Any]:
        person_key = record.get("person")
        self._validate_id(person_key)
        if person_key not in self.persons:
            raise KeyError(f"person={person_key} not found")
        return self._create(self.messages, record)

    def delete_message(self, key: int) -> None:
        self._delete(self.messages, key)

    def get_all_messages(self) -> list[dict[str, Any]]:
        return self._all(self.messages)

    def get_message(self, key: int) -> dict[str, Any]:
        return self._get(self.messages, key)

    # Feedback
    def create_feedback(self, record: dict[str, Any]) -> dict[str, Any]:
        message_key = record.get("message")
        self._validate_id(message_key)
        if message_key not in self.messages:
            raise KeyError(f"message={message_key} not found")
        return self._create(self.feedbacks, record)

    def delete_feedback(self, key: int) -> None:
        self._delete(self.feedbacks, key)

    def get_all_feedbacks(self) -> list[dict[str, Any]]:
        return self._all(self.feedbacks)

    def get_feedback(self, key: int) -> dict[str, Any]:
        return self._get(self.feedbacks, key)

    # Relational algebra query:
    # pi_{M.data, P.platform}( sigma_{M.datetime > now - 8 min}
    #                           (P join_{P.key=M.person} M) )
    def recent_message_data(self, now: int | None = None) -> list[dict[str, str]]:
        if now is None:
            now = int(datetime.now(timezone.utc).timestamp())
        cutoff = now - 8 * 60

        result: list[dict[str, str]] = []
        for message in self.messages.values():
            if message["datetime"] <= cutoff:
                continue
            person = self.persons.get(message["person"])
            if person is None:
                continue
            result.append({
                "data": message["data"],
                "platform": person["platform"],
            })

        # Projection contains two attributes; sorting is only for deterministic output.
        return sorted(result, key=lambda row: (row["data"], row["platform"]))
