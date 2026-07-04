from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
import json

from app.main import app
from app.packages import service as package_service
from app.production.release import route_inventory_gate


async def main() -> int:
    routes = package_service.route_inventory(list(app.routes))
    result = await route_inventory_gate(routes)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
