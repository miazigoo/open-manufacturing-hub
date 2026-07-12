#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"
FORBIDDEN = ["builder_json", "workflow", "operation template", "execution step", "route condition", "raw config"]

# Existing developer/advanced/docs surfaces are intentionally allowed. The check focuses on simple-mode entry points and pattern wizards.
CHECK_PATHS = [
    FRONTEND_SRC / "pages" / "DashboardPage.tsx",
    FRONTEND_SRC / "pages" / "IntegrationStartPage.tsx",
    FRONTEND_SRC / "pages" / "IntegrationPatternDetailPage.tsx",
    FRONTEND_SRC / "features" / "integration-master",
    FRONTEND_SRC / "features" / "pattern-wizards",
    FRONTEND_SRC / "components" / "Layout.tsx",
]

# Current legacy debt outside migrated wizards. Keep explicit so new leaks are visible in review.
WARN_ONLY_PATH_PARTS = {
    "DashboardPage.tsx",
    "Layout.tsx",
    "integration-master/",
    "pattern-wizards/poll-odata-send-target/",
    "pattern-wizards/request-print/",
    "pattern-wizards/source-web-api-writeback-onec/",
    "pattern-wizards/wms-fact-to-onec/",
    "pattern-wizards/xml-odata-xml-response/",
    "pattern-wizards/xml-raw-bridge/",
}
ALLOW_LINE_PATTERNS = [
    re.compile(r"Advanced details", re.IGNORECASE),
    re.compile(r"advanced pages", re.IGNORECASE),
    re.compile(r"<details", re.IGNORECASE),
    re.compile(r"/docs/", re.IGNORECASE),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check simple-mode UI copy for low-level implementation labels")
    parser.add_argument("--strict", action="store_true", help="fail on every non-whitelisted finding")
    args = parser.parse_args()

    findings = []
    for path in iter_files():
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            lower = line.lower()
            if not any(term in lower for term in FORBIDDEN):
                continue
            if any(pattern.search(line) for pattern in ALLOW_LINE_PATTERNS):
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            level = "warning" if is_warn_only(rel) else "error"
            findings.append((level, rel, line_no, line.strip()))

    print("Simple Mode UX check")
    print(f"checked_paths={len(list(iter_files()))} findings={len(findings)}")
    for level, rel, line_no, line in findings:
        print(f"{level.upper()}: {rel}:{line_no}: {line[:180]}")

    if args.strict:
        return 1 if findings else 0
    return 1 if any(level == "error" for level, *_ in findings) else 0


def iter_files():
    files: list[Path] = []
    for path in CHECK_PATHS:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.tsx")))
            files.extend(sorted(path.rglob("*.ts")))
    return sorted(set(files))


def is_warn_only(rel: str) -> bool:
    return any(part in rel for part in WARN_ONLY_PATH_PARTS)


if __name__ == "__main__":
    raise SystemExit(main())
