"""TCP RPC server for variant 30."""

import logging
import socket
import threading
from typing import Any, Callable

from .model import DataStore
from .protocol import PROTOCOL_VERSION, decode_request, encode_response

HOST = "127.0.0.1"
PORT = 5000
ACCEPT_TIMEOUT = 0.2
START_TIMEOUT = 2.0
STOP_TIMEOUT = 1.0
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


def configure_logging(path: str) -> None:
    """Configure the RPC journal."""
    logging.basicConfig(
        filename=path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        force=True,
    )


def make_dispatch(store: DataStore) -> dict[int, Callable[..., Any]]:
    """Build operation-code to data-layer method mapping."""
    return {
        code: getattr(store, name)
        for name, code in OPERATION_CODES.items()
    }


def _error_response(exc: Exception) -> dict[str, Any]:
    """Convert an exception to a JSON response object."""
    return {
        "ok": False,
        "error": type(exc).__name__,
        "message": str(exc),
    }


def _success_response(result: Any) -> dict[str, Any]:
    """Build a successful JSON response object."""
    return {"ok": True, "result": result}


def _execute(
    operation: int,
    body: Any,
    dispatch: dict[int, Callable[..., Any]],
) -> dict[str, Any]:
    """Validate and execute one RPC operation."""
    if operation not in dispatch:
        raise ValueError(f"unknown operation code: {operation}")
    if not isinstance(body, dict):
        raise ValueError("request JSON body must be an object")
    return _success_response(dispatch[operation](**body))


def serve_client(
    conn: socket.socket,
    addr: tuple[str, int],
    store: DataStore,
    journal: logging.Logger,
) -> None:
    """Serve requests from one TCP client connection."""
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
            journal.info(
                "RPC request addr=%s op=%s body=%r",
                addr,
                operation,
                body,
            )
            response = _execute_request(operation, body, dispatch, journal)
            conn.sendall(encode_response(operation, response))


def _execute_request(
    operation: int,
    body: Any,
    dispatch: dict[int, Callable[..., Any]],
    journal: logging.Logger,
) -> dict[str, Any]:
    """Execute one request and convert failures to error responses."""
    try:
        return _execute(operation, body, dispatch)
    except Exception as exc:
        journal.exception("RPC error op=%s: %s", operation, exc)
        return _error_response(exc)


class RPCServer:
    """Threaded TCP server used by the client and MBT tests."""

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
        self.journal = logging.getLogger("variant30.rpc")

    def start(self) -> None:
        """Start the server in a background thread."""
        if self._is_running():
            return
        configure_logging(self.journal_path)
        self._open_socket()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        self.ready_event.wait(timeout=START_TIMEOUT)

    def _is_running(self) -> bool:
        """Return whether the server thread is active."""
        return self._thread is not None and self._thread.is_alive()

    def _open_socket(self) -> None:
        """Create and bind the listening socket."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self.host, self.requested_port))
        self.port = self._socket.getsockname()[1]
        self._socket.listen()
        self._socket.settimeout(ACCEPT_TIMEOUT)

    def _serve(self) -> None:
        """Accept TCP clients until shutdown."""
        if self._socket is None:
            return
        self.ready_event.set()
        self.journal.info(
            "server started host=%s port=%s protocol=%s",
            self.host,
            self.port,
            PROTOCOL_VERSION,
        )
        while not self.stop_event.is_set():
            self._accept_client()

    def _accept_client(self) -> None:
        """Accept one client or handle an expected socket event."""
        if self._socket is None:
            return
        try:
            conn, addr = self._socket.accept()
        except socket.timeout:
            return
        except OSError:
            return
        threading.Thread(
            target=serve_client,
            args=(conn, addr, self.store, self.journal),
            daemon=True,
        ).start()

    def stop(self) -> None:
        """Stop the server and close its listening socket."""
        self.stop_event.set()
        self._close_socket()
        self._join_thread()

    def _close_socket(self) -> None:
        """Close the listening socket."""
        if self._socket is None:
            return
        try:
            self._socket.close()
        except OSError:
            pass

    def _join_thread(self) -> None:
        """Wait briefly for the server thread."""
        if self._thread is not None:
            self._thread.join(timeout=STOP_TIMEOUT)


def run_server(
    host: str = HOST,
    port: int = PORT,
    journal_path: str = "journal.log",
) -> None:
    """Run a blocking server until interrupted."""
    server = RPCServer(host, port, journal_path)
    server.start()
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.stop()


def main() -> None:
    """Start the default RPC server."""
    run_server()


if __name__ == "__main__":
    main()
