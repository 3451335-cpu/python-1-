"""Demonstration of all 13 RPC methods."""

import tempfile
import time

from src.client import RPCClient, RPCError
from src.server import RPCServer


def make_records(now: int) -> tuple[dict, dict, dict]:
    """Create demonstration Person, Message and Feedback records."""
    person = {
        "key": 1,
        "datetime": now,
        "platform": "web",
        "user_agent": "DemoBrowser",
    }
    message = {
        "key": 1,
        "datetime": now,
        "data": "Hello from TCP RPC",
        "person": 1,
        "tags": "demo",
        "done": 0,
        "started": 1,
    }
    feedback = {
        "key": 1,
        "datetime": now,
        "response": "ok",
        "status": "ok",
        "failure": "",
        "message": 1,
    }
    return person, message, feedback


def show_crud(
    client: RPCClient,
    person: dict,
    message: dict,
    feedback: dict,
) -> None:
    """Demonstrate the twelve CRUD RPC methods."""
    print("1", client.create_person(person))
    print("2", client.get_person(person["key"]))
    print("3", client.get_all_persons())
    print("4", client.create_message(message))
    print("5", client.get_message(message["key"]))
    print("6", client.get_all_messages())
    print("7", client.create_feedback(feedback))
    print("8", client.get_feedback(feedback["key"]))
    print("9", client.get_all_feedbacks())
    client.delete_feedback(feedback["key"])
    print("10", client.get_all_feedbacks())
    client.delete_message(message["key"])
    print("11", client.get_all_messages())
    client.delete_person(person["key"])
    print("12", client.get_all_persons())


def show_selection(client: RPCClient, person: dict, message: dict) -> None:
    """Demonstrate the relational-algebra selection RPC."""
    client.create_person(person)
    client.create_message(message)
    print("13", client.recent_message_data())


def show_error(client: RPCClient) -> None:
    """Demonstrate RPC error handling."""
    try:
        client.get_person(999)
    except RPCError as exc:
        print("Error handling:", exc)


def main() -> None:
    """Run the complete RPC demonstration."""
    with tempfile.NamedTemporaryFile(
        prefix="v30-", suffix=".log", delete=False
    ) as journal_file:
        journal = journal_file.name
    server = RPCServer(port=0, journal_path=journal)
    server.start()
    client = RPCClient(port=server.port)
    person, message, feedback = make_records(int(time.time()))
    try:
        show_crud(client, person, message, feedback)
        show_selection(client, person, message)
        show_error(client)
        print("Journal:", journal)
    finally:
        server.stop()


if __name__ == "__main__":
    main()
