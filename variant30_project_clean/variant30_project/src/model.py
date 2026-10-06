"""In-memory data access layer for practical assignment variant 30."""

from datetime import datetime, timezone
from typing import Any

PERSONS = "persons"
MESSAGES = "messages"
FEEDBACKS = "feedbacks"
EIGHT_MINUTES = 8 * 60


class DataStore:
    """Store Person, Message and Feedback records in memory."""

    def __init__(self) -> None:
        self.persons: dict[int, dict[str, Any]] = {}
        self.messages: dict[int, dict[str, Any]] = {}
        self.feedbacks: dict[int, dict[str, Any]] = {}

    @staticmethod
    def _validate_id(value: int) -> None:
        """Validate a record identifier."""
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("key must be int")

    @staticmethod
    def _copy(record: dict[str, Any]) -> dict[str, Any]:
        """Return a shallow copy of a record."""
        return dict(record)

    def _create(
        self,
        table: dict[int, dict[str, Any]],
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a record in the selected table."""
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
        """Delete a record from the selected table."""
        self._validate_id(key)
        if key not in table:
            raise KeyError(f"record with key={key} not found")
        del table[key]

    @staticmethod
    def _all(table: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
        """Return all records in key order."""
        return [dict(table[key]) for key in sorted(table)]

    def _get(
        self,
        table: dict[int, dict[str, Any]],
        key: int,
    ) -> dict[str, Any]:
        """Return one record by identifier."""
        self._validate_id(key)
        if key not in table:
            raise KeyError(f"record with key={key} not found")
        return self._copy(table[key])

    def create_person(self, record: dict[str, Any]) -> dict[str, Any]:
        """Create a Person record."""
        return self._create(self.persons, record)

    def delete_person(self, key: int) -> None:
        """Delete a Person record."""
        self._delete(self.persons, key)

    def get_all_persons(self) -> list[dict[str, Any]]:
        """Return all Person records."""
        return self._all(self.persons)

    def get_person(self, key: int) -> dict[str, Any]:
        """Return one Person record."""
        return self._get(self.persons, key)

    def create_message(self, record: dict[str, Any]) -> dict[str, Any]:
        """Create a Message linked to an existing Person."""
        person_key = record.get("person")
        self._validate_id(person_key)
        if person_key not in self.persons:
            raise KeyError(f"person={person_key} not found")
        return self._create(self.messages, record)

    def delete_message(self, key: int) -> None:
        """Delete a Message record."""
        self._delete(self.messages, key)

    def get_all_messages(self) -> list[dict[str, Any]]:
        """Return all Message records."""
        return self._all(self.messages)

    def get_message(self, key: int) -> dict[str, Any]:
        """Return one Message record."""
        return self._get(self.messages, key)

    def create_feedback(self, record: dict[str, Any]) -> dict[str, Any]:
        """Create Feedback linked to an existing Message."""
        message_key = record.get("message")
        self._validate_id(message_key)
        if message_key not in self.messages:
            raise KeyError(f"message={message_key} not found")
        return self._create(self.feedbacks, record)

    def delete_feedback(self, key: int) -> None:
        """Delete a Feedback record."""
        self._delete(self.feedbacks, key)

    def get_all_feedbacks(self) -> list[dict[str, Any]]:
        """Return all Feedback records."""
        return self._all(self.feedbacks)

    def get_feedback(self, key: int) -> dict[str, Any]:
        """Return one Feedback record."""
        return self._get(self.feedbacks, key)

    def recent_message_data(
        self, now: int | None = None
    ) -> list[dict[str, str]]:
        """Project recent Message data and Person platform fields."""
        current = self._current_time(now)
        cutoff = current - EIGHT_MINUTES
        rows = [
            self._project_message(message)
            for message in self.messages.values()
            if message["datetime"] > cutoff
        ]
        result = [row for row in rows if row is not None]
        return sorted(result, key=lambda row: (row["data"], row["platform"]))

    @staticmethod
    def _current_time(now: int | None) -> int:
        """Return supplied time or current UTC epoch seconds."""
        if now is not None:
            return now
        return int(datetime.now(timezone.utc).timestamp())

    def _project_message(
        self, message: dict[str, Any]
    ) -> dict[str, str] | None:
        """Build one projected row when the Person join succeeds."""
        person = self.persons.get(message["person"])
        if person is None:
            return None
        return {"data": message["data"], "platform": person["platform"]}
