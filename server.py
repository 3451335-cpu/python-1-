from __future__ import annotations

import logging
import socket
import threading
from typing import Any, Callable

from .model import DataStore
from .protocol import decode_request, encode_response, PROTOCOL_VERSION

HOST = "127.0.0.1"
PORT = 5000

OPERATION_CODES = {
    "create_person": 1,
    "delete_person": 2,
    "get_all_persons": 3,
    "get_person": 4,
    "create_message": 5,
    "delete_message": 6,
    "get_all_messages": 7,
    "get_message": 8,
    "create_feedback": 9,
    "delete_feedback": 10,
    "get_all_feedbacks": 11,
    "get_feedback": 12,
    "recent_message_data": 13,
}
DISPATCH = {code: name for name, code in OPERATION_CODES.items()}


def configure_logging(path: str = "journal.log") -> None:
    logging.basicConfig(
        filename=path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        force=True,
    )


def make_dispatch(store: DataStore) -> dict[int, Callable[..., Any]]:
    return {
        code: getattr(store, method_name)
        for method_name, code in OPERATION_CODES.items()
    }


def serve_client(
    conn: socket.socket,
    addr: tuple[str, int],
    store: DataStore,
    journal: logging.Logger,
) -> None:
    dispatch = make_dispatch(store)
    with conn:
        while True:
            try:
                operation, body = decode_request(conn)
            except ConnectionError:
                return
            except Exception as exc:
                journal.exception("Malformed request from %s: %s", addr, exc)
                return

            journal.info("RPC request addr=%s op=%s body=%r", addr, operation, body)

            try:
                if operation not in dispatch:
                    raise ValueError(f"unknown operation code: {operation}")
                if not isinstance(body, dict):
                    raise ValueError("request JSON body must be an object")

                result = dispatch[operation](**body)
                response = {"ok": True, "result": result}
            except Exception as exc:
                journal.exception("RPC error op=%s: %s", operation, exc)
                response = {
                    "ok": False,
                    "error": type(exc).__name__,
                    "message": str(exc),
                }

            conn.sendall(encode_response(operation, response))


class RPCServer:
    """TCP server. It is also convenient to start/stop from automated tests."""

    def __init__(
        self,
        host: str = HOST,
        port: int = PORT,
        journal_path: str = "journal.log",
    ) -> None:
        self.host = host
        self.requested_port = port
        self.port = port
        self.journal_path = journal_path
        self.store = DataStore()
        self.stop_event = threading.Event()
        self.ready_event = threading.Event()
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        configure_logging(self.journal_path)
        self.journal = logging.getLogger(f"variant30.rpc.{id(self)}")

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self.host, self.requested_port))
        self.port = self._socket.getsockname()[1]
        self._socket.listen()
        self._socket.settimeout(0.2)

        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        self.ready_event.wait(timeout=2)

    def _serve(self) -> None:
        assert self._socket is not None
        self.ready_event.set()
        self.journal.info(
            "server started host=%s port=%s protocol=%s",
            self.host,
            self.port,
            PROTOCOL_VERSION,
        )

        while not self.stop_event.is_set():
            try:
                conn, addr = self._socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            threading.Thread(
                target=serve_client,
                args=(conn, addr, self.store, self.journal),
                daemon=True,
            ).start()

    def stop(self) -> None:
        self.stop_event.set()
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=1)


def run_server(
    host: str = HOST,
    port: int = PORT,
    journal_path: str = "journal.log",
) -> None:
    server = RPCServer(host, port, journal_path)
    server.start()
    try:
        while True:
            threading.Event().wait(3600)
    except KeyboardInterrupt:
        server.stop()


def main() -> None:
    run_server()


if __name__ == "__main__":
    main()
