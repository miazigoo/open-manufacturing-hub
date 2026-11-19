from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

SECRET_MARKER = "***REDACTED***"
SECRET_KEYS = ("password", "secret", "token", "api_key", "apikey", "authorization", "private_key")
MAX_VALUE_LENGTH = 1000


def is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in SECRET_KEYS)


def normalize_json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return normalize_json(value.model_dump(mode="json"))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): normalize_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [normalize_json(item) for item in value]
    return value


def redact_secrets(value: Any, parent_key: str = "") -> Any:
    value = normalize_json(value)
    if parent_key and is_secret_key(parent_key):
        return SECRET_MARKER
    if isinstance(value, dict):
        return {str(key): redact_secrets(item, str(key)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_secrets(item, parent_key) for item in value]
    if isinstance(value, str) and len(value) > MAX_VALUE_LENGTH:
        return f"{value[:MAX_VALUE_LENGTH]}...<truncated {len(value) - MAX_VALUE_LENGTH} chars>"
    return value


def json_diff(before: Any, after: Any) -> dict[str, list[dict[str, Any]]]:
    norm_before = normalize_json(before or {})
    norm_after = normalize_json(after or {})
    result: dict[str, list[dict[str, Any]]] = {"added": [], "removed": [], "changed": []}
    _diff_values(norm_before, norm_after, "", result)

    for category in ("added", "removed", "changed"):
        for entry in result[category]:
            last_key = entry["path"].split(".")[-1]
            if is_secret_key(last_key):
                if "before" in entry:
                    entry["before"] = SECRET_MARKER
                if "after" in entry:
                    entry["after"] = SECRET_MARKER
            else:
                if "before" in entry:
                    entry["before"] = redact_secrets(entry["before"])
                if "after" in entry:
                    entry["after"] = redact_secrets(entry["after"])
    return result


def _diff_values(before: Any, after: Any, path: str, result: dict[str, list[dict[str, Any]]]) -> None:
    if isinstance(before, dict) and isinstance(after, dict):
        before_keys = set(before)
        after_keys = set(after)
        for key in sorted(after_keys - before_keys):
            result["added"].append({"path": _join_path(path, key), "after": after[key]})
        for key in sorted(before_keys - after_keys):
            result["removed"].append({"path": _join_path(path, key), "before": before[key]})
        for key in sorted(before_keys & after_keys):
            _diff_values(before[key], after[key], _join_path(path, key), result)
        return
    if before != after:
        result["changed"].append({"path": path or "$", "before": before, "after": after})


def _join_path(parent: str, key: str) -> str:
    return f"{parent}.{key}" if parent else str(key)
