from __future__ import annotations

from typing import Any


def pagination_params(config: dict[str, Any], query: dict[str, Any] | None, page: int) -> dict[str, Any]:
    odata = config.get("odata") or {}
    page_size = int((query or {}).get("$top") or odata.get("default_page_size") or 100)
    params = dict(query or {})
    params["$top"] = page_size
    skip = int(params.get("$skip") or 0) + page * page_size
    if skip:
        params["$skip"] = skip
    else:
        params.pop("$skip", None)
    return params


def max_pages(config: dict[str, Any]) -> int:
    return int((config.get("odata") or {}).get("max_pages") or 10)
