from __future__ import annotations

import hashlib
import re
from io import StringIO
from typing import Any
from xml.dom import minidom
from xml.etree import ElementTree

from app.xml_bridge.parser import XMLBridgeError, validate_xml_size
from app.xml_toolkit.schemas import XmlParseResponse, XmlPathItem

MAX_PATHS = 500
MAX_TREE_DEPTH = 8
MAX_TREE_CHILDREN = 80


def parse_xml(raw_xml: str) -> XmlParseResponse:
    sha = _sha(raw_xml)
    size = len(raw_xml.encode("utf-8"))
    namespaces: dict[str, str] = {}
    try:
        validate_xml_size(raw_xml)
        _reject_unsafe_xml(raw_xml)
        namespaces = _collect_namespaces(raw_xml)
        root = ElementTree.fromstring(raw_xml)
    except (XMLBridgeError, ElementTree.ParseError) as exc:
        return XmlParseResponse(success=False, valid=False, errors=[str(exc)], sha256=sha, size_bytes=size, namespaces=namespaces, encoding_detected=_encoding(raw_xml))

    uri_to_prefix = {uri: prefix for prefix, uri in namespaces.items()}
    root_name = _display_tag(root.tag, uri_to_prefix)
    paths: list[XmlPathItem] = []
    preview_tree = _tree_preview(root, f"/{root_name}", uri_to_prefix, paths, depth=0)
    return XmlParseResponse(
        success=True,
        valid=True,
        root=root_name,
        root_name=root_name,
        encoding_detected=_encoding(raw_xml),
        namespaces=namespaces,
        paths=paths[:MAX_PATHS],
        preview_tree=preview_tree,
        errors=[],
        sha256=sha,
        size_bytes=size,
        pretty_xml=_pretty(raw_xml),
    )


def _collect_namespaces(raw_xml: str) -> dict[str, str]:
    namespaces: dict[str, str] = {}
    try:
        for _event, item in ElementTree.iterparse(StringIO(raw_xml), events=("start-ns",)):
            prefix, uri = item
            namespaces[prefix or "default"] = uri
    except ElementTree.ParseError:
        return namespaces
    return namespaces


def _tree_preview(element: ElementTree.Element, path: str, uri_to_prefix: dict[str, str], paths: list[XmlPathItem], *, depth: int) -> dict[str, Any]:
    text = (element.text or "").strip()
    display_name = _display_tag(element.tag, uri_to_prefix)
    attributes = {_display_tag(key, uri_to_prefix): value for key, value in element.attrib.items()}
    for attr_name, attr_value in attributes.items():
        paths.append(XmlPathItem(path=f"{path}/@{attr_name}", value_preview=_preview(attr_value), type="attribute"))
    children = list(element)
    if text:
        paths.append(XmlPathItem(path=path, value_preview=_preview(text), type="text", repeated=_is_repeated_path(path)))
    elif not children:
        paths.append(XmlPathItem(path=path, value_preview="", type="text", repeated=_is_repeated_path(path)))

    child_counts: dict[str, int] = {}
    for child in children:
        child_name = _display_tag(child.tag, uri_to_prefix)
        child_counts[child_name] = child_counts.get(child_name, 0) + 1
    child_seen: dict[str, int] = {}
    preview_children = []
    if depth < MAX_TREE_DEPTH:
        for child in children[:MAX_TREE_CHILDREN]:
            child_name = _display_tag(child.tag, uri_to_prefix)
            index = child_seen.get(child_name, 0)
            child_seen[child_name] = index + 1
            child_path = f"{path}/{child_name}[{index}]" if child_counts[child_name] > 1 else f"{path}/{child_name}"
            preview_children.append(_tree_preview(child, child_path, uri_to_prefix, paths, depth=depth + 1))
    return {"name": display_name, "path": path, "text": _preview(text) if text else None, "attributes": attributes, "children": preview_children}


def _display_tag(tag: str, uri_to_prefix: dict[str, str]) -> str:
    if tag.startswith("{") and "}" in tag:
        uri, local = tag[1:].split("}", 1)
        prefix = uri_to_prefix.get(uri)
        return f"{prefix}:{local}" if prefix and prefix != "default" else local
    return tag


def _encoding(raw_xml: str) -> str | None:
    match = re.search(r"<\?xml[^>]*encoding=[\"']([^\"']+)[\"']", raw_xml[:256], re.IGNORECASE)
    return match.group(1) if match else None


def _reject_unsafe_xml(raw_xml: str) -> None:
    lowered = raw_xml.lower()
    if "<!doctype" in lowered or "<!entity" in lowered:
        raise XMLBridgeError("XML_UNSAFE", "DOCTYPE and ENTITY declarations are not allowed")


def _pretty(raw_xml: str) -> str:
    try:
        return minidom.parseString(raw_xml.encode("utf-8")).toprettyxml(indent="  ")
    except Exception:
        return raw_xml


def _preview(value: Any, limit: int = 240) -> str:
    text = str(value)
    return text if len(text) <= limit else f"{text[:limit]}..."


def _is_repeated_path(path: str) -> bool:
    return bool(re.search(r"\[\d+\](?:/|$)", path))


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

