from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree

from app.xml_toolkit.parser import _collect_namespaces, _display_tag, _reject_unsafe_xml


class XmlPathError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ExtractedXmlField:
    name: str
    path: str
    value: Any
    required: bool
    mode: str


def extract_path(raw_xml: str, path: str, *, mode: str = "first") -> Any:
    _reject_unsafe_xml(raw_xml)
    root = ElementTree.fromstring(raw_xml)
    uri_to_prefix = {uri: prefix for prefix, uri in _collect_namespaces(raw_xml).items()}
    segments = [segment for segment in path.strip().split("/") if segment]
    if not segments:
        raise XmlPathError("XML path is empty")
    root_name, root_index = _parse_segment(segments[0])
    if root_index not in (None, 0):
        raise XmlPathError("Root segment index must be 0 or omitted")
    if root_name != _display_tag(root.tag, uri_to_prefix):
        raise XmlPathError(f"Root {root_name} does not match XML root {_display_tag(root.tag, uri_to_prefix)}")
    matches: list[ElementTree.Element | str] = [root]
    for raw_segment in segments[1:]:
        if raw_segment.startswith("@"):
            attr_name = raw_segment[1:]
            values = []
            for match in matches:
                if isinstance(match, ElementTree.Element) and attr_name in {_display_tag(key, uri_to_prefix): key for key in match.attrib.keys()}:
                    real_key = next(key for key in match.attrib.keys() if _display_tag(key, uri_to_prefix) == attr_name)
                    values.append(match.attrib[real_key])
            matches = values
            continue
        name, index = _parse_segment(raw_segment)
        next_matches: list[ElementTree.Element] = []
        for match in matches:
            if not isinstance(match, ElementTree.Element):
                continue
            candidates = [child for child in list(match) if _display_tag(child.tag, uri_to_prefix) == name]
            if index is None:
                next_matches.extend(candidates)
            elif 0 <= index < len(candidates):
                next_matches.append(candidates[index])
        matches = next_matches
    values = [_element_value(item) for item in matches]
    if mode == "all":
        return values
    if not values:
        raise XmlPathError(f"XML path not found: {path}")
    return values[0]


def extract_fields(raw_xml: str, fields: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    values: dict[str, Any] = {}
    errors: list[dict[str, Any]] = []
    for field in fields:
        name = str(field.get("name") or "").strip()
        path = str(field.get("path") or "").strip()
        mode = str(field.get("mode") or "first")
        required = bool(field.get("required"))
        if not name or not path:
            errors.append({"name": name, "path": path, "code": "XML_FIELD_INVALID", "message": "XML extraction field needs name and path"})
            continue
        try:
            values[name] = extract_path(raw_xml, path, mode=mode)
        except (ElementTree.ParseError, XmlPathError) as exc:
            if required:
                errors.append({"name": name, "path": path, "code": "XML_REQUIRED_FIELD_MISSING", "message": str(exc)})
            else:
                values[name] = [] if mode == "all" else None
    return values, errors


def _parse_segment(segment: str) -> tuple[str, int | None]:
    match = re.match(r"^(.+?)\[(\d+)\]$", segment)
    if match:
        return match.group(1), int(match.group(2))
    return segment, None


def _element_value(value: ElementTree.Element | str) -> Any:
    if isinstance(value, str):
        return value
    text = (value.text or "").strip()
    if len(list(value)) == 0:
        return text
    return ElementTree.tostring(value, encoding="unicode")

