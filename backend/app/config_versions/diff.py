from __future__ import annotations

from typing import Any

from app.audit.diff import json_diff, redact_secrets


def diff_config(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return json_diff(redact_secrets(before), redact_secrets(after))
