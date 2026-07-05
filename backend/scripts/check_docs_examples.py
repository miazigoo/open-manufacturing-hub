from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_PATH = ROOT / "frontend" / "src" / "docs" / "examples" / "index.json"
ASSETS_PATH = ROOT / "frontend" / "src" / "docs" / "assets" / "index.json"
ONEC_CONTENT_PATH = ROOT / "frontend" / "src" / "features" / "docs" / "onecContent.ts"
CONTENT_PATH = ROOT / "frontend" / "src" / "features" / "docs" / "content.ts"


def fail(message: str) -> None:
    raise SystemExit(f"[docs-examples-check] {message}")


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is invalid JSON: {exc}")
    if not isinstance(data, dict):
        fail(f"{path} must contain a JSON object")
    return data


def main() -> None:
    examples = load_json(EXAMPLES_PATH)
    assets = load_json(ASSETS_PATH)
    docs_text = ONEC_CONTENT_PATH.read_text(encoding="utf-8") + "\n" + CONTENT_PATH.read_text(encoding="utf-8")

    if len(examples) != len(set(examples)):
        fail("duplicate example ids detected")

    used_examples = {item for item in re.findall(r"::example\{exampleId=\"([^\"]+)\"\}", docs_text) if "$" not in item}
    used_examples.update(re.findall(r"exampleId:\s*'([^']+)'", docs_text))
    missing_examples = sorted(used_examples - set(examples))
    if missing_examples:
        fail(f"docs reference missing examples: {missing_examples}")

    used_assets = {item for item in re.findall(r"::screenshot\{assetId=\"([^\"]+)\"", docs_text) if "$" not in item}
    missing_assets = sorted(used_assets - set(assets))
    if missing_assets:
        fail(f"docs reference missing screenshot assets: {missing_assets}")

    for example_id, example in examples.items():
        for field in ("title", "description"):
            value = example.get(field)
            if not isinstance(value, dict) or not all(value.get(lang) for lang in ("ru", "en", "zh")):
                fail(f"{example_id}.{field} must contain ru/en/zh")
        if not example.get("endpoint_slug"):
            fail(f"{example_id} must declare endpoint_slug")
        if example.get("method") != "POST":
            fail(f"{example_id} must use POST for Test Console examples")
        mode = example.get("input_mode")
        if mode == "json":
            if not isinstance(example.get("body"), dict):
                fail(f"{example_id} JSON example must use object body")
            json.dumps(example["body"], ensure_ascii=False)
        elif mode == "xml":
            body_text = example.get("body_text") or ""
            try:
                ET.fromstring(body_text)
            except ET.ParseError as exc:
                fail(f"{example_id} XML body is invalid: {exc}")
        elif mode != "raw_text":
            fail(f"{example_id} has unsupported input_mode {mode!r}")
        if example.get("runnable") and not (example.get("requires_setup") or example.get("endpoint_slug")):
            fail(f"{example_id} runnable example must have endpoint or be marked requires_setup")

    required = {"onec.two_odata_to_json_endpoint", "onec.xml_raw_forward", "onec.print_label", "onec.marking_pool_to_api"}
    missing_required = sorted(required - set(examples))
    if missing_required:
        fail(f"required examples are missing: {missing_required}")

    print(f"[docs-examples-check] {len(examples)} examples, {len(used_examples)} docs references and {len(used_assets)} screenshot references verified")


if __name__ == "__main__":
    main()
