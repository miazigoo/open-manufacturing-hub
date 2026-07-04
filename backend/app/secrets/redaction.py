from __future__ import annotations

from typing import Any

SECRET_FIELD_MARKERS = ("password", "token", "secret", "authorization", "api_key", "apikey", "private_key", "credential")
REDACTED = "***REDACTED***"
MASKED = "***"


def is_secret_ref(value: Any) -> bool:
    return isinstance(value, dict) and set(value.keys()) == {"$secret"} and isinstance(value.get("$secret"), str) and bool(value.get("$secret"))


def is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in SECRET_FIELD_MARKERS)


def safe_preview(value: str) -> str:
    if len(value) <= 8:
        return f"length: {len(value)}"
    return f"{value[:3]}****{value[-3:]}"


def mask_config(value: Any) -> Any:
    if is_secret_ref(value):
        return {"$secret": value["$secret"]}
    if isinstance(value, dict):
        masked: dict[str, Any] = {}
        for key, item in value.items():
            if key == "$secret":
                masked[key] = str(item)
            elif is_secret_key(str(key)) and not str(key).endswith("_secret"):
                masked[key] = mask_config(item) if is_secret_ref(item) else MASKED
            else:
                masked[key] = mask_config(item)
        return masked
    if isinstance(value, list):
        return [mask_config(item) for item in value]
    return value


def redact_value(value: Any) -> Any:
    if is_secret_ref(value):
        return {"$secret": value["$secret"]}
    if isinstance(value, dict):
        return {str(key): (REDACTED if is_secret_key(str(key)) and not is_secret_ref(item) else redact_value(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value


def collect_secret_references(value: Any, path: str = "") -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    if is_secret_ref(value):
        refs.append((value["$secret"], path or "$"))
    elif isinstance(value, dict):
        for key, item in value.items():
            next_path = f"{path}.{key}" if path else str(key)
            if str(key).endswith("_secret") and isinstance(item, str) and item:
                refs.append((item, next_path))
            else:
                refs.extend(collect_secret_references(item, next_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            refs.extend(collect_secret_references(item, f"{path}[{index}]" if path else f"[{index}]"))
    return refs


def raw_secret_warnings(value: Any, path: str = "") -> list[str]:
    warnings: list[str] = []
    if isinstance(value, dict):
        if is_secret_ref(value):
            return warnings
        for key, item in value.items():
            key_str = str(key)
            next_path = f"{path}.{key_str}" if path else key_str
            if key_str.endswith("_secret"):
                continue
            if is_secret_key(key_str) and isinstance(item, str) and item and item not in {MASKED, REDACTED, "***MASKED***", "***REFERENCE_ONLY***"}:
                warnings.append(f"{next_path} appears to contain raw secret")
            warnings.extend(raw_secret_warnings(item, next_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            warnings.extend(raw_secret_warnings(item, f"{path}[{index}]" if path else f"[{index}]"))
    return warnings
