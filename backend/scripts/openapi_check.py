from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

TARGET = Path(__file__).resolve().parents[2] / "frontend" / "src" / "api" / "generated" / "openapi.json"


def main() -> int:
    schema = app.openapi()
    if not isinstance(schema.get("paths"), dict) or not schema["paths"]:
        raise RuntimeError("OpenAPI schema has no paths")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(schema, indent=2, sort_keys=True), encoding="utf-8")
    loaded = json.loads(TARGET.read_text(encoding="utf-8"))
    required = ["/api/health", "/api/packages/route-inventory", "/api/production/doctor"]
    missing = [path for path in required if path not in loaded.get("paths", {})]
    if missing:
        raise RuntimeError(f"OpenAPI missing required paths: {missing}")
    print(f"OpenAPI OK: {len(loaded['paths'])} paths -> {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
