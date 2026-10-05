from __future__ import annotations

import socket
from typing import Any

from .protocol import decode_response, encode_request, PROTOCOL_VERSION
from .server import OPERATION_CODES


class RPCError(RuntimeError):
    pass


class RPCClient:
    """Client whose public method names match the server data-layer functions."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5000, timeout: float = 5.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def _call(self, method_name: str, **body: Any) -> Any:
        operation = OPERATION_CODES[method_name]
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.sendall(encode_request(operation, body))
            version, response_operation, response = decode_response(sock)

        if version != PROTOCOL_VERSION:
            raise RPCError(f"unsupported protocol version: {version}")
        if response_operation != operation:
            raise RPCError(
                f"operation mismatch: requested {operation}, got {response_operation}"
            )
        if not response.get("ok"):
            raise RPCError(f"{response.get('error')}: {response.get('message')}")
        return response.get("result")

    def create_person(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._call("create_person", record=record)

    def delete_person(self, key: int) -> None:
        self._call("delete_person", key=key)

    def get_all_persons(self) -> list[dict[str, Any]]:
        return self._call("get_all_persons")

    def get_person(self, key: int) -> dict[str, Any]:
        return self._call("get_person", key=key)

    def create_message(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._call("create_message", record=record)

    def delete_message(self, key: int) -> None:
        self._call("delete_message", key=key)

    def get_all_messages(self) -> list[dict[str, Any]]:
        return self._call("get_all_messages")

    def get_message(self, key: int) -> dict[str, Any]:
        return self._call("get_message", key=key)

    def create_feedback(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._call("create_feedback", record=record)

    def delete_feedback(self, key: int) -> None:
        self._call("delete_feedback", key=key)

    def get_all_feedbacks(self) -> list[dict[str, Any]]:
        return self._call("get_all_feedbacks")

    def get_feedback(self, key: int) -> dict[str, Any]:
        return self._call("get_feedback", key=key)

    def recent_message_data(self) -> list[dict[str, str]]:
        return self._call("recent_message_data")
