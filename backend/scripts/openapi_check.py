from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

TARGET = Path(__file__).resolve().parents[2] / "frontend" / "src" / "api" / "generated" / "openapi.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or export OpenAPI schema")
    parser.add_argument("--write", "--export", action="store_true", help="Write/export current schema to target file")
    parser.add_argument("--check", action="store_true", help="Verify target file matches current schema")
    args = parser.parse_args()

    schema = app.openapi()
    if not isinstance(schema.get("paths"), dict) or not schema["paths"]:
        raise RuntimeError("OpenAPI schema has no paths")

    new_content = json.dumps(schema, indent=2, sort_keys=True) + "\n"

    # Default to write if TARGET doesn't exist yet, or if explicitly requested
    if args.write or not TARGET.exists():
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_text(new_content, encoding="utf-8")
        print(f"OpenAPI exported: {len(schema['paths'])} paths -> {TARGET}")
        return 0

    # Otherwise verification mode
    existing_content = TARGET.read_text(encoding="utf-8")
    if existing_content.strip() != new_content.strip():
        print(
            f"ERROR: OpenAPI schema in {TARGET} does not match FastAPI app.openapi()!\n"
            f"Run `make openapi-export` (or `python scripts/openapi_check.py --write`) to synchronize.",
            file=sys.stderr,
        )
        return 1

    loaded = json.loads(existing_content)
    required = ["/api/health", "/api/packages/route-inventory", "/api/production/doctor"]
    missing = [path for path in required if path not in loaded.get("paths", {})]
    if missing:
        raise RuntimeError(f"OpenAPI missing required paths: {missing}")

    print(f"OpenAPI OK (matches schema): {len(loaded['paths'])} paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
