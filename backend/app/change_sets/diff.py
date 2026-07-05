from __future__ import annotations

from typing import Any

SECRET_MARKERS = ("password", "token", "secret", "authorization", "api_key", "apikey", "private_key")


def redact_export(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value.keys()) == {"$secret"}:
            return {"$secret": str(value["$secret"])}
        if set(value.keys()) == {"$env"}:
            return {"$env": str(value["$env"])}
        result: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in SECRET_MARKERS) and not _is_reference(item):
                result[str(key)] = "***REFERENCE_ONLY***"
            else:
                result[str(key)] = redact_export(item)
        return result
    if isinstance(value, list):
        return [redact_export(item) for item in value]
    return value


def collect_secret_refs(value: Any, path: str = "") -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    if isinstance(value, dict):
        if set(value.keys()) == {"$secret"}:
            refs.append({"name": str(value["$secret"]), "path": path or "$"})
        for key, item in value.items():
            refs.extend(collect_secret_refs(item, f"{path}.{key}" if path else str(key)))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            refs.extend(collect_secret_refs(item, f"{path}[{index}]"))
    return refs


def collect_env_refs(value: Any, path: str = "") -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    if isinstance(value, dict):
        if set(value.keys()) == {"$env"}:
            refs.append({"key": str(value["$env"]), "path": path or "$"})
        for key, item in value.items():
            refs.extend(collect_env_refs(item, f"{path}.{key}" if path else str(key)))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            refs.extend(collect_env_refs(item, f"{path}[{index}]"))
    return refs


def _is_reference(value: Any) -> bool:
    return isinstance(value, dict) and (set(value.keys()) == {"$secret"} or set(value.keys()) == {"$env"})
