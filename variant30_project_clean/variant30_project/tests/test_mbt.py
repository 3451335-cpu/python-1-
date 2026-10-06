"""Model-based tests for all 13 variant 30 RPC methods."""

import time

from hypothesis import HealthCheck, settings, strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
)

from src.client import RPCClient, RPCError
from src.server import RPCServer

MAX_KEY = 1000
MAX_DT = 2_000_000_000
BASE_KEY = 10_000


class Variant30Machine(RuleBasedStateMachine):
    """Compare a Python reference model with the real TCP RPC service."""

    @initialize()
    def start(self) -> None:
        """Start the server and initialize the reference model."""
        self.server = RPCServer(port=0, journal_path="mbt-journal.log")
        self.server.start()
        self.client = RPCClient(port=self.server.port)
        self.persons: dict[int, dict] = {}
        self.messages: dict[int, dict] = {}
        self.feedbacks: dict[int, dict] = {}

    def teardown(self) -> None:
        """Stop the server after a generated scenario."""
        self.server.stop()

    @staticmethod
    def _fresh_key(requested: int, table: dict) -> int:
        """Return a free positive key."""
        key = abs(requested) + 1
        while key in table:
            key += 1
        return key

    @staticmethod
    def _sorted(table: dict) -> list[dict]:
        """Return reference records in key order."""
        return [table[key] for key in sorted(table)]

    @rule(
        key=st.integers(0, MAX_KEY),
        platform=st.sampled_from(["web", "android", "ios"]),
        user_agent=st.text(max_size=20),
        dt=st.integers(0, MAX_DT),
    )
    def create_person(self, key, platform, user_agent, dt) -> None:
        """Create a Person through RPC."""
        key = self._fresh_key(key, self.persons)
        record = {
            "key": key,
            "datetime": dt,
            "platform": platform,
            "user_agent": user_agent,
        }
        assert self.client.create_person(record) == record
        self.persons[key] = record

    @rule(key=st.integers(0, MAX_KEY))
    def delete_person(self, key) -> None:
        """Delete a generated Person."""
        if self.persons:
            key = sorted(self.persons)[key % len(self.persons)]
            self.client.delete_person(key)
            del self.persons[key]

    @rule()
    def get_all_persons(self) -> None:
        """Read all Person records through RPC."""
        assert self.client.get_all_persons() == self._sorted(self.persons)

    @rule(key=st.integers(0, MAX_KEY))
    def get_person(self, key) -> None:
        """Read one generated Person through RPC."""
        if self.persons:
            key = sorted(self.persons)[key % len(self.persons)]
            assert self.client.get_person(key) == self.persons[key]

    @rule(
        key=st.integers(0, MAX_KEY),
        data=st.text(max_size=30),
        tags=st.text(max_size=20),
        done=st.integers(0, 1),
        started=st.integers(0, 1),
        dt=st.integers(0, MAX_DT),
    )
    def create_message(self, key, data, tags, done, started, dt) -> None:
        """Create a Message linked to a generated Person."""
        if not self.persons:
            return
        key = self._fresh_key(key, self.messages)
        person = sorted(self.persons)[key % len(self.persons)]
        record = self._message_record(
            key, data, person, tags, done, started, dt
        )
        assert self.client.create_message(record) == record
        self.messages[key] = record

    @staticmethod
    def _message_record(key, data, person, tags, done, started, dt) -> dict:
        """Build a Message record."""
        return {
            "key": key,
            "datetime": dt,
            "data": data,
            "person": person,
            "tags": tags,
            "done": done,
            "started": started,
        }

    @rule(key=st.integers(0, MAX_KEY))
    def delete_message(self, key) -> None:
        """Delete a generated Message."""
        if self.messages:
            key = sorted(self.messages)[key % len(self.messages)]
            self.client.delete_message(key)
            del self.messages[key]

    @rule()
    def get_all_messages(self) -> None:
        """Read all Message records through RPC."""
        assert self.client.get_all_messages() == self._sorted(self.messages)

    @rule(key=st.integers(0, MAX_KEY))
    def get_message(self, key) -> None:
        """Read one generated Message through RPC."""
        if self.messages:
            key = sorted(self.messages)[key % len(self.messages)]
            assert self.client.get_message(key) == self.messages[key]

    @rule(
        key=st.integers(0, MAX_KEY),
        response=st.text(max_size=20),
        status=st.sampled_from(["ok", "failed", "pending"]),
        failure=st.text(max_size=20),
        dt=st.integers(0, MAX_DT),
    )
    def create_feedback(self, key, response, status, failure, dt) -> None:
        """Create Feedback linked to a generated Message."""
        if not self.messages:
            return
        key = self._fresh_key(key, self.feedbacks)
        message = sorted(self.messages)[key % len(self.messages)]
        record = self._feedback_record(
            key, response, status, failure, message, dt
        )
        assert self.client.create_feedback(record) == record
        self.feedbacks[key] = record

    @staticmethod
    def _feedback_record(key, response, status, failure, message, dt) -> dict:
        """Build a Feedback record."""
        return {
            "key": key,
            "datetime": dt,
            "response": response,
            "status": status,
            "failure": failure,
            "message": message,
        }

    @rule(key=st.integers(0, MAX_KEY))
    def delete_feedback(self, key) -> None:
        """Delete a generated Feedback record."""
        if self.feedbacks:
            key = sorted(self.feedbacks)[key % len(self.feedbacks)]
            self.client.delete_feedback(key)
            del self.feedbacks[key]

    @rule()
    def get_all_feedbacks(self) -> None:
        """Read all Feedback records through RPC."""
        assert self.client.get_all_feedbacks() == self._sorted(self.feedbacks)

    @rule(key=st.integers(0, MAX_KEY))
    def get_feedback(self, key) -> None:
        """Read one generated Feedback through RPC."""
        if self.feedbacks:
            key = sorted(self.feedbacks)[key % len(self.feedbacks)]
            assert self.client.get_feedback(key) == self.feedbacks[key]

    @rule()
    def recent_message_data(self) -> None:
        """Check the eight-minute relational-algebra selection."""
        now = int(time.time())
        cutoff = now - 8 * 60
        expected = self._recent_rows(cutoff)
        assert self.client.recent_message_data() == expected

    def _recent_rows(self, cutoff: int) -> list[dict[str, str]]:
        """Build the reference result for recent_message_data."""
        rows = []
        for message in self.messages.values():
            if message["datetime"] <= cutoff:
                continue
            person = self.persons.get(message["person"])
            if person is not None:
                rows.append({
                    "data": message["data"],
                    "platform": person["platform"],
                })
        return sorted(rows, key=lambda row: (row["data"], row["platform"]))

    @rule(base=st.integers(BASE_KEY, BASE_KEY + MAX_KEY))
    def exercise_all_13_rpcs(self, base) -> None:
        """Invoke every RPC method from one generated state transition."""
        keys = self._make_complete_state(base)
        self._check_complete_state(keys)
        self._delete_complete_state(keys)

    def _make_complete_state(self, base: int) -> tuple[int, int, int]:
        """Create one Person, Message and Feedback for the full RPC check."""
        person_key = self._fresh_key(base, self.persons)
        message_key = self._fresh_key(base + 1, self.messages)
        feedback_key = self._fresh_key(base + 2, self.feedbacks)
        person, message, feedback = self._complete_records(
            person_key, message_key, feedback_key
        )
        assert self.client.create_person(person) == person
        self.persons[person_key] = person
        assert self.client.create_message(message) == message
        self.messages[message_key] = message
        assert self.client.create_feedback(feedback) == feedback
        self.feedbacks[feedback_key] = feedback
        return person_key, message_key, feedback_key

    @staticmethod
    def _complete_records(person_key, message_key, feedback_key):
        """Build the records used by the complete RPC check."""
        now = int(time.time())
        person = {
            "key": person_key,
            "datetime": now,
            "platform": "web",
            "user_agent": "MBT",
        }
        message = {
            "key": message_key,
            "datetime": now,
            "data": "hello",
            "person": person_key,
            "tags": "mbt",
            "done": 0,
            "started": 0,
        }
        feedback = {
            "key": feedback_key,
            "datetime": now,
            "response": "ok",
            "status": "ok",
            "failure": "",
            "message": message_key,
        }
        return person, message, feedback

    def _check_complete_state(self, keys: tuple[int, int, int]) -> None:
        """Check all read and selection RPC methods."""
        person_key, message_key, feedback_key = keys
        assert self.client.get_person(person_key) == self.persons[person_key]
        assert self.client.get_all_persons() == self._sorted(self.persons)
        assert (
            self.client.get_message(message_key)
            == self.messages[message_key]
        )
        assert self.client.get_all_messages() == self._sorted(self.messages)
        assert (
            self.client.get_feedback(feedback_key)
            == self.feedbacks[feedback_key]
        )
        assert self.client.get_all_feedbacks() == self._sorted(self.feedbacks)
        self.client.recent_message_data()

    def _delete_complete_state(self, keys: tuple[int, int, int]) -> None:
        """Check all three delete RPC methods."""
        person_key, message_key, feedback_key = keys
        self.client.delete_feedback(feedback_key)
        self.client.delete_message(message_key)
        self.client.delete_person(person_key)
        del self.feedbacks[feedback_key]
        del self.messages[message_key]
        del self.persons[person_key]

    @rule()
    def error_handling(self) -> None:
        """Check a server-side RPC error."""
        if self.persons:
            missing = max(self.persons) + 1
        else:
            missing = BASE_KEY
        try:
            self.client.get_person(missing)
        except RPCError as exc:
            assert "KeyError" in str(exc)
        else:
            raise AssertionError("missing Person did not raise RPCError")

    @invariant()
    def tables_match(self) -> None:
        """Keep the remote and reference collections synchronized."""
        assert self.client.get_all_persons() == self._sorted(self.persons)
        assert self.client.get_all_messages() == self._sorted(self.messages)
        assert self.client.get_all_feedbacks() == self._sorted(self.feedbacks)


TestVariant30 = Variant30Machine.TestCase
TestVariant30.settings = settings(
    max_examples=10,
    stateful_step_count=20,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
