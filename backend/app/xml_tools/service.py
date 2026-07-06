from __future__ import annotations
import difflib
import hashlib
from typing import Any
from xml.dom import minidom
from app.xml_bridge.parser import parse_xml_safe
from app.xml_toolkit import service as toolkit_service


def parse(xml: str) -> dict[str, Any]:
    sha = _sha(xml)
    toolkit = toolkit_service.parse(xml)
    if toolkit.success:
        try:
            parsed = parse_xml_safe(xml)
        except Exception:
            parsed = toolkit.preview_tree or {}
        return {
            "valid": True,
            "sha256": sha,
            "size_bytes": len(xml.encode("utf-8")),
            "parsed": parsed,
            "preview": xml[:4000],
            "pretty_xml": toolkit.pretty_xml or _pretty(xml),
            "paths": [item.path for item in toolkit.paths],
            "error": None,
            "toolkit": toolkit.model_dump(mode="json"),
        }
    return {"valid": False, "sha256": sha, "size_bytes": len(xml.encode("utf-8")), "parsed": None, "preview": xml[:4000], "pretty_xml": None, "paths": [], "error": "; ".join(toolkit.errors), "toolkit": toolkit.model_dump(mode="json")}


def diff(left_xml: str, right_xml: str) -> dict[str, Any]:
    left_sha = _sha(left_xml)
    right_sha = _sha(right_xml)
    lines = difflib.unified_diff(_pretty(left_xml).splitlines(), _pretty(right_xml).splitlines(), fromfile="left.xml", tofile="right.xml", lineterm="")
    return {"same_hash": left_sha == right_sha, "left_sha256": left_sha, "right_sha256": right_sha, "forwarded_unchanged": left_sha == right_sha, "diff_text": "\n".join(lines)}


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pretty(value: str) -> str:
    try:
        return minidom.parseString(value.encode("utf-8")).toprettyxml(indent="  ")
    except Exception:
        return value


def _paths(value: Any, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            paths.append(next_prefix)
            paths.extend(_paths(item, next_prefix))
    elif isinstance(value, list):
        for index, item in enumerate(value[:3]):
            paths.extend(_paths(item, f"{prefix}[{index}]"))
    return paths[:200]
