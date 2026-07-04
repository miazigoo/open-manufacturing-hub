from __future__ import annotations

import importlib.util
import sys

REQUIRED = ["pytest", "pytest_asyncio", "aiosqlite", "httpx"]


def main() -> int:
    missing = [name for name in REQUIRED if importlib.util.find_spec(name) is None]
    if missing:
        print("Missing backend test dependencies: " + ", ".join(missing), file=sys.stderr)
        print('Run: cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[test]"', file=sys.stderr)
        return 1
    print("Backend test environment OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
