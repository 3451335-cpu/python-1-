from __future__ import annotations

import threading
import time

from hypothesis import HealthCheck, given, settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule

from src.client import RPCClient, RPCError
from src.server import RPCServer


def normalize(rows):
    return sorted(rows, key=lambda row: json_key(row))


def json_key(row):
    return tuple((k, str(row[k])) for k in sorted(row))


class Variant30Machine(RuleBasedStateMachine):
    """Model-based tests that exercise the real TCP RPC client/server."""

    @initialize()
    def start(self):
        self.server = RPCServer(port=0, journal_path="mbt-journal.log")
        self.server.start()
        self.client = RPCClient(port=self.server.port)
        self.persons = {}
        self.messages = {}
        self.feedbacks = {}
        self.lock = threading.Lock()

    def teardown(self):
        self.server.stop()

    def fresh_key(self, requested: int, table: dict) -> int:
        key = abs(requested) + 1
        while key in table:
            key += 1
        return key

    @rule(key=st.integers(min_value=0, max_value=1000),
          platform=st.sampled_from(["web", "android", "ios"]),
          user_agent=st.text(min_size=0, max_size=20),
          dt=st.integers(min_value=0, max_value=2_000_000_000))
    def create_person(self, key, platform, user_agent, dt):
        key = self.fresh_key(key, self.persons)
        record = {
            "key": key, "datetime": dt,
            "platform": platform, "user_agent": user_agent,
        }
        assert self.client.create_person(record) == record
        self.persons[key] = record

    @rule(key=st.integers(min_value=0, max_value=1000))
    def delete_person(self, key):
        if not self.persons:
            return
        key = sorted(self.persons)[key % len(self.persons)]
        self.client.delete_person(key)
        del self.persons[key]

    @rule()
    def get_all_persons(self):
        assert self.client.get_all_persons() == [self.persons[k] for k in sorted(self.persons)]

    @rule(key=st.integers(min_value=0, max_value=1000))
    def get_person(self, key):
        if not self.persons:
            return
        key = sorted(self.persons)[key % len(self.persons)]
        assert self.client.get_person(key) == self.persons[key]

    @rule(key=st.integers(min_value=0, max_value=1000),
          data=st.text(max_size=30),
          tags=st.text(max_size=20),
          done=st.integers(min_value=0, max_value=1),
          started=st.integers(min_value=0, max_value=1),
          dt=st.integers(min_value=0, max_value=2_000_000_000))
    def create_message(self, key, data, tags, done, started, dt):
        if not self.persons:
            return
        key = self.fresh_key(key, self.messages)
        person = sorted(self.persons)[key % len(self.persons)]
        record = {
            "key": key, "datetime": dt, "data": data, "person": person,
            "tags": tags, "done": done, "started": started,
        }
        assert self.client.create_message(record) == record
        self.messages[key] = record

    @rule(key=st.integers(min_value=0, max_value=1000))
    def delete_message(self, key):
        if not self.messages:
            return
        key = sorted(self.messages)[key % len(self.messages)]
        self.client.delete_message(key)
        del self.messages[key]

    @rule()
    def get_all_messages(self):
        assert self.client.get_all_messages() == [self.messages[k] for k in sorted(self.messages)]

    @rule(key=st.integers(min_value=0, max_value=1000))
    def get_message(self, key):
        if not self.messages:
            return
        key = sorted(self.messages)[key % len(self.messages)]
        assert self.client.get_message(key) == self.messages[key]

    @rule(key=st.integers(min_value=0, max_value=1000),
          response=st.text(max_size=20),
          status=st.sampled_from(["ok", "failed", "pending"]),
          failure=st.text(max_size=20),
          dt=st.integers(min_value=0, max_value=2_000_000_000))
    def create_feedback(self, key, response, status, failure, dt):
        if not self.messages:
            return
        key = self.fresh_key(key, self.feedbacks)
        message = sorted(self.messages)[key % len(self.messages)]
        record = {
            "key": key, "datetime": dt, "response": response,
            "status": status, "failure": failure, "message": message,
        }
        assert self.client.create_feedback(record) == record
        self.feedbacks[key] = record

    @rule(key=st.integers(min_value=0, max_value=1000))
    def delete_feedback(self, key):
        if not self.feedbacks:
            return
        key = sorted(self.feedbacks)[key % len(self.feedbacks)]
        self.client.delete_feedback(key)
        del self.feedbacks[key]

    @rule()
    def get_all_feedbacks(self):
        assert self.client.get_all_feedbacks() == [self.feedbacks[k] for k in sorted(self.feedbacks)]

    @rule(key=st.integers(min_value=0, max_value=1000))
    def get_feedback(self, key):
        if not self.feedbacks:
            return
        key = sorted(self.feedbacks)[key % len(self.feedbacks)]
        assert self.client.get_feedback(key) == self.feedbacks[key]

    @rule()
    def recent_message_data(self):
        # Server and test run in the same process, so using current epoch seconds
        # gives a stable boundary for records generated near "now".
        now = int(time.time())
        expected = []
        cutoff = now - 8 * 60
        for message in self.messages.values():
            if message["datetime"] > cutoff and message["person"] in self.persons:
                expected.append({
                    "data": message["data"],
                    "platform": self.persons[message["person"]]["platform"],
                })
        assert self.client.recent_message_data() == sorted(
            expected, key=lambda row: (row["data"], row["platform"])
        )

    @rule(base=st.integers(min_value=10_000, max_value=20_000))
    def exercise_all_13_rpcs(self, base):
        """One generated rule deliberately invokes every RPC method."""
        p = self.fresh_key(base, self.persons)
        m = self.fresh_key(base + 1, self.messages)
        f = self.fresh_key(base + 2, self.feedbacks)

        person = {
            "key": p, "datetime": int(time.time()),
            "platform": "web", "user_agent": "MBT",
        }
        message = {
            "key": m, "datetime": int(time.time()), "data": "hello",
            "person": p, "tags": "mbt", "done": 0, "started": 0,
        }
        feedback = {
            "key": f, "datetime": int(time.time()), "response": "ok",
            "status": "ok", "failure": "", "message": m,
        }

        assert self.client.create_person(person) == person
        self.persons[p] = person
        assert self.client.get_person(p) == person
        assert self.client.get_all_persons() == [self.persons[k] for k in sorted(self.persons)]

        assert self.client.create_message(message) == message
        self.messages[m] = message
        assert self.client.get_message(m) == message
        assert self.client.get_all_messages() == [self.messages[k] for k in sorted(self.messages)]

        assert self.client.create_feedback(feedback) == feedback
        self.feedbacks[f] = feedback
        assert self.client.get_feedback(f) == feedback
        assert self.client.get_all_feedbacks() == [self.feedbacks[k] for k in sorted(self.feedbacks)]

        self.client.recent_message_data()

        self.client.delete_feedback(f)
        del self.feedbacks[f]
        self.client.delete_message(m)
        del self.messages[m]
        self.client.delete_person(p)
        del self.persons[p]

    @invariant()
    def all_lists_are_sorted(self):
        assert self.client.get_all_persons() == [self.persons[k] for k in sorted(self.persons)]
        assert self.client.get_all_messages() == [self.messages[k] for k in sorted(self.messages)]
        assert self.client.get_all_feedbacks() == [self.feedbacks[k] for k in sorted(self.feedbacks)]


TestVariant30 = Variant30Machine.TestCase
TestVariant30.settings = settings(
    max_examples=10,
    stateful_step_count=20,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
