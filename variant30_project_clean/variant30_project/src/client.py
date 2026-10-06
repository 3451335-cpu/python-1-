"""TCP RPC client for variant 30."""

import socket
from typing import Any

from .protocol import PROTOCOL_VERSION, decode_response, encode_request
from .server import OPERATION_CODES


class RPCError(RuntimeError):
    """Error returned by the RPC server or detected by the client."""


class RPCClient:
    """Client whose public methods match the server data-layer functions."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        timeout: float = 5.0,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def _call(self, method_name: str, **body: Any) -> Any:
        """Send one RPC request and return its result."""
        operation = OPERATION_CODES[method_name]
        response = self._send_checked(operation, body)
        self._validate_response(operation, response)
        return response.get("result")

    @staticmethod
    def _validate_response(
        operation: int,
        response: dict[str, Any],
    ) -> None:
        """Validate protocol response metadata and RPC status."""
        if response.get("_version") != PROTOCOL_VERSION:
            raise RPCError("unsupported protocol version")
        if response.get("_operation") != operation:
            raise RPCError("operation mismatch")
        if not response.get("ok"):
            raise RPCError(
                f"{response.get('error')}: {response.get('message')}"
            )

    def _send_checked(
        self, operation: int, body: dict[str, Any]
    ) -> dict[str, Any]:
        """Send a request while retaining response version metadata."""
        with socket.create_connection(
            (self.host, self.port), timeout=self.timeout
        ) as sock:
            sock.sendall(encode_request(operation, body))
            version, response_operation, response = decode_response(sock)
        response["_version"] = version
        response["_operation"] = response_operation
        return response

    def create_person(self, record: dict[str, Any]) -> dict[str, Any]:
        """Create a Person record remotely."""
        return self._call_checked("create_person", record=record)

    def delete_person(self, key: int) -> None:
        """Delete a Person record remotely."""
        self._call_checked("delete_person", key=key)

    def get_all_persons(self) -> list[dict[str, Any]]:
        """Get all Person records remotely."""
        return self._call_checked("get_all_persons")

    def get_person(self, key: int) -> dict[str, Any]:
        """Get one Person record remotely."""
        return self._call_checked("get_person", key=key)

    def create_message(self, record: dict[str, Any]) -> dict[str, Any]:
        """Create a Message record remotely."""
        return self._call_checked("create_message", record=record)

    def delete_message(self, key: int) -> None:
        """Delete a Message record remotely."""
        self._call_checked("delete_message", key=key)

    def get_all_messages(self) -> list[dict[str, Any]]:
        """Get all Message records remotely."""
        return self._call_checked("get_all_messages")

    def get_message(self, key: int) -> dict[str, Any]:
        """Get one Message record remotely."""
        return self._call_checked("get_message", key=key)

    def create_feedback(self, record: dict[str, Any]) -> dict[str, Any]:
        """Create a Feedback record remotely."""
        return self._call_checked("create_feedback", record=record)

    def delete_feedback(self, key: int) -> None:
        """Delete a Feedback record remotely."""
        self._call_checked("delete_feedback", key=key)

    def get_all_feedbacks(self) -> list[dict[str, Any]]:
        """Get all Feedback records remotely."""
        return self._call_checked("get_all_feedbacks")

    def get_feedback(self, key: int) -> dict[str, Any]:
        """Get one Feedback record remotely."""
        return self._call_checked("get_feedback", key=key)

    def recent_message_data(self) -> list[dict[str, str]]:
        """Run the relational-algebra selection remotely."""
        return self._call_checked("recent_message_data")

    def _call_checked(self, method_name: str, **body: Any) -> Any:
        """Send a request and validate its complete response."""
        operation = OPERATION_CODES[method_name]
        response = self._send_checked(operation, body)
        self._validate_response(operation, response)
        return response.get("result")
