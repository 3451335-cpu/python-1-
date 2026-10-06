"""Binary protocol defined by table 30."""

import json
import socket
from typing import Any

PROTOCOL_VERSION = 1
REQUEST_OPERATION_SIZE = 2
REQUEST_BODY_SIZE = 3
RESPONSE_VERSION_SIZE = 1
RESPONSE_OPERATION_SIZE = 2
RESPONSE_BODY_SIZE = 5


def _pack_uint(value: int, size: int) -> bytes:
    """Pack an unsigned integer using little-endian byte order."""
    max_value = 1 << (size * 8)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("header value must be int")
    if not 0 <= value < max_value:
        raise ValueError(f"value does not fit into {size} bytes")
    return value.to_bytes(size, "little", signed=False)


def _read_exact(sock: socket.socket, size: int) -> bytes:
    """Read exactly the requested number of bytes from a socket."""
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("connection closed before full message")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _json_bytes(payload: Any) -> bytes:
    """Serialize a payload to compact UTF-8 JSON."""
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def encode_request(operation: int, body: Any) -> bytes:
    """Encode a request according to table 30."""
    raw = _json_bytes(body)
    return _pack_uint(operation, REQUEST_OPERATION_SIZE) + _pack_uint(
        len(raw), REQUEST_BODY_SIZE
    ) + raw


def decode_request(sock: socket.socket) -> tuple[int, Any]:
    """Decode a request received from a socket."""
    operation = int.from_bytes(
        _read_exact(sock, REQUEST_OPERATION_SIZE), "little"
    )
    size = int.from_bytes(_read_exact(sock, REQUEST_BODY_SIZE), "little")
    body = json.loads(_read_exact(sock, size).decode("utf-8"))
    return operation, body


def encode_response(operation: int, body: Any) -> bytes:
    """Encode a response according to table 30."""
    raw = _json_bytes(body)
    return (
        bytes([PROTOCOL_VERSION])
        + _pack_uint(operation, RESPONSE_OPERATION_SIZE)
        + _pack_uint(len(raw), RESPONSE_BODY_SIZE)
        + raw
    )


def decode_response(sock: socket.socket) -> tuple[int, int, Any]:
    """Decode a response received from a socket."""
    version = _read_exact(sock, RESPONSE_VERSION_SIZE)[0]
    operation = int.from_bytes(
        _read_exact(sock, RESPONSE_OPERATION_SIZE), "little"
    )
    size = int.from_bytes(_read_exact(sock, RESPONSE_BODY_SIZE), "little")
    body = json.loads(_read_exact(sock, size).decode("utf-8"))
    return version, operation, body
