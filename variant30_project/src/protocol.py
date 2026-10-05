from __future__ import annotations

import json
import socket
from typing import Any

PROTOCOL_VERSION = 1

REQUEST_HEADER_SIZE = 5
RESPONSE_HEADER_SIZE = 8


def _pack_uint_le(value: int, size: int) -> bytes:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("header value must be int")
    if value < 0 or value >= 1 << (8 * size):
        raise ValueError(f"value does not fit into {size} bytes")
    return value.to_bytes(size, byteorder="little", signed=False)


def _read_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("connection closed before the full message was received")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def encode_request(operation: int, body: Any) -> bytes:
    raw = _json_bytes(body)
    # Table 30: operation 2 bytes + body size 3 bytes + JSON.
    return _pack_uint_le(operation, 2) + _pack_uint_le(len(raw), 3) + raw


def decode_request(sock: socket.socket) -> tuple[int, Any]:
    operation = int.from_bytes(_read_exact(sock, 2), "little")
    body_size = int.from_bytes(_read_exact(sock, 3), "little")
    body = json.loads(_read_exact(sock, body_size).decode("utf-8"))
    return operation, body


def encode_response(operation: int, body: Any) -> bytes:
    raw = _json_bytes(body)
    # Table 30: version 1 byte + operation 2 bytes + body size 5 bytes + JSON.
    return (
        bytes([PROTOCOL_VERSION])
        + _pack_uint_le(operation, 2)
        + _pack_uint_le(len(raw), 5)
        + raw
    )


def decode_response(sock: socket.socket) -> tuple[int, int, Any]:
    version = _read_exact(sock, 1)[0]
    operation = int.from_bytes(_read_exact(sock, 2), "little")
    body_size = int.from_bytes(_read_exact(sock, 5), "little")
    body = json.loads(_read_exact(sock, body_size).decode("utf-8"))
    return version, operation, body
