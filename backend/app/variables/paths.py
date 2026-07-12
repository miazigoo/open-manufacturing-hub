from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_TOKEN_RE = re.compile(r"([^.[\]]+)|\[(\d+)\]")


@dataclass(slots=True)
class PathResolutionError(Exception):
    path: str
    segment: str
    message: str

    def __str__(self) -> str:
        return f"{self.message} at '{self.segment}' while resolving '{self.path}'"


def resolve_path(data: Any, path: str) -> Any:
    if path is None or str(path).strip() == "":
        raise PathResolutionError(str(path), "", "Path is empty")
    current = data
    for token in _tokens(str(path)):
        current = _read_token(current, token, str(path))
    return current


def try_resolve_path(data: Any, path: str, default: Any = None) -> Any:
    try:
        return resolve_path(data, path)
    except PathResolutionError:
        return default


def _tokens(path: str) -> list[str | int]:
    tokens: list[str | int] = []
    position = 0
    for match in _TOKEN_RE.finditer(path):
        if match.start() != position and path[position:match.start()] not in {".", ""}:
            raise PathResolutionError(path, path[position:match.start()], "Invalid path syntax")
        if match.group(1) is not None:
            tokens.append(match.group(1))
        else:
            tokens.append(int(match.group(2)))
        position = match.end()
        if position < len(path) and path[position] == ".":
            position += 1
    if position != len(path):
        raise PathResolutionError(path, path[position:], "Invalid path syntax")
    return tokens


def _read_token(current: Any, token: str | int, path: str) -> Any:
    if isinstance(token, int):
        if not isinstance(current, list):
            raise PathResolutionError(path, f"[{token}]", "Expected list")
        if token < 0 or token >= len(current):
            raise PathResolutionError(path, f"[{token}]", "List index is out of range")
        return current[token]
    if token == "length" and not (isinstance(current, dict) and token in current):
        if isinstance(current, (list, dict, str)):
            return len(current)
        raise PathResolutionError(path, token, "Expected list, object or string")
    if isinstance(current, dict):
        if token not in current:
            raise PathResolutionError(path, token, "Key not found")
        return current[token]
    raise PathResolutionError(path, token, "Expected object")
