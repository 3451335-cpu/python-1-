from __future__ import annotations

import tempfile
import time

from src.client import RPCClient, RPCError
from src.server import RPCServer


def main() -> None:
    with tempfile.NamedTemporaryFile(prefix='v30-', suffix='.log', delete=False) as f:
        journal = f.name

    server = RPCServer(port=0, journal_path=journal)
    server.start()
    client = RPCClient(port=server.port)

    now = int(time.time())
    person = {
        'key': 1, 'datetime': now, 'platform': 'web', 'user_agent': 'DemoBrowser'
    }
    message = {
        'key': 1, 'datetime': now, 'data': 'Hello from TCP RPC',
        'person': 1, 'tags': 'demo', 'done': 0, 'started': 1
    }
    feedback = {
        'key': 1, 'datetime': now, 'response': 'ok',
        'status': 'ok', 'failure': '', 'message': 1
    }

    try:
        print('1 ', client.create_person(person))
        print('2 ', client.get_person(1))
        print('3 ', client.get_all_persons())
        print('4 ', client.create_message(message))
        print('5 ', client.get_message(1))
        print('6 ', client.get_all_messages())
        print('7 ', client.create_feedback(feedback))
        print('8 ', client.get_feedback(1))
        print('9 ', client.get_all_feedbacks())
        print('10', client.recent_message_data())
        client.delete_feedback(1)
        print('11', client.get_all_feedbacks())
        client.delete_message(1)
        print('12', client.get_all_messages())
        client.delete_person(1)
        print('13', client.get_all_persons())

        try:
            client.get_person(999)
        except RPCError as exc:
            print('Error handling:', exc)

        print('Journal:', journal)
    finally:
        server.stop()


if __name__ == '__main__':
    main()
