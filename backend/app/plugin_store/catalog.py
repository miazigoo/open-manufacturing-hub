from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).with_name("catalog.json")


@lru_cache(maxsize=1)
def load_catalog() -> list[dict[str, Any]]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def catalog_by_package_id() -> dict[str, dict[str, Any]]:
    return {str(item["package_id"]): item for item in load_catalog()}
